import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Optional, Set

from audit_service import AuditService
from compliance_engine import LegalInterpreter
from database import SentinelDB
from etherscan import MultichainFetcher
from indexer import DeFiLlamaIndexer
from main import autonomous_update

logger = logging.getLogger(__name__)

ADDRESS_RE = re.compile(r"0x[a-fA-F0-9]{40}")

DEFAULT_PERCENTILE = 0.10
DEFAULT_MAX_TARGETS = 25
DEFAULT_CACHE_TTL_SECONDS = 300
DEFAULT_MIN_REAUDIT_SECONDS = 300
DEFAULT_WORKERS = 2


def save_audit_report(protocol_name: str, report_data: Dict) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"reports/{protocol_name}_{timestamp}.json".replace(" ", "_")

    os.makedirs("reports", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as handle:
        json.dump(report_data, handle, indent=4)

    return filename


def _iter_strings(payload: object):
    if isinstance(payload, str):
        yield payload
        return
    if isinstance(payload, list):
        for item in payload:
            yield from _iter_strings(item)
        return
    if isinstance(payload, dict):
        for value in payload.values():
            yield from _iter_strings(value)


class EventDrivenSentinel:
    """
    Event router for webhook-driven auditing.
    Converts incoming on-chain/off-chain events into targeted audit runs.
    """

    def __init__(self):
        self.db = SentinelDB()
        self.interpreter = LegalInterpreter()
        self.fetcher = MultichainFetcher()
        self.audit_service = AuditService(
            db=self.db,
            interpreter=self.interpreter,
            fetcher=self.fetcher,
        )
        self.indexer = DeFiLlamaIndexer()

        self.percentile = float(os.getenv("WATCHLIST_PERCENTILE", str(DEFAULT_PERCENTILE)))
        self.max_targets = int(os.getenv("WATCHLIST_MAX_TARGETS", str(DEFAULT_MAX_TARGETS)))
        self.cache_ttl_seconds = int(
            os.getenv("WATCHLIST_CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL_SECONDS))
        )
        self.min_reaudit_seconds = int(
            os.getenv("WEBHOOK_MIN_REAUDIT_SECONDS", str(DEFAULT_MIN_REAUDIT_SECONDS))
        )
        self.executor = ThreadPoolExecutor(
            max_workers=int(os.getenv("WEBHOOK_MAX_WORKERS", str(DEFAULT_WORKERS)))
        )

        self._watch_targets: List[Dict] = []
        self._watch_targets_by_address: Dict[str, Dict] = {}
        self._watch_targets_updated_at = 0.0
        self._last_audit_at: Dict[str, float] = {}
        self._lock = threading.Lock()

    def get_watchlist(self, force_refresh: bool = False) -> List[Dict]:
        now = time.time()
        with self._lock:
            should_refresh = force_refresh or not self._watch_targets
            should_refresh = should_refresh or (now - self._watch_targets_updated_at > self.cache_ttl_seconds)
            if should_refresh:
                candidates = self.indexer.get_top_percentile_targets(
                    self.percentile,
                    require_address=True,
                )
                self._watch_targets = candidates[: self.max_targets]
                self._watch_targets_by_address = {
                    target["address"].lower(): target
                    for target in self._watch_targets
                    if target.get("address")
                }
                self._watch_targets_updated_at = now
                logger.info(
                    "Updated watchlist: %s targets (top %.2f%%, cap=%s)",
                    len(self._watch_targets),
                    self.percentile * 100,
                    self.max_targets,
                )
            return list(self._watch_targets)

    def get_watched_addresses(self) -> List[str]:
        targets = self.get_watchlist()
        return [t["address"] for t in targets if t.get("address")]

    def _get_manifest_bundle(self) -> Dict:
        latest = self.db.get_latest_manifest()
        if latest and latest.get("manifest"):
            return {
                "version": latest.get("version"),
                "manifest": latest.get("manifest", {}),
                "diff": latest.get("diff", {}),
                "source_title": latest.get("source_title", "latest_manifest"),
                "jurisdiction": latest.get("jurisdiction", "global"),
            }
        logger.info("No manifest found in DB; generating one from latest regulatory context")
        return autonomous_update(self.audit_service)

    def _can_reaudit(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            previous = self._last_audit_at.get(key, 0)
            if now - previous < self.min_reaudit_seconds:
                return False
            self._last_audit_at[key] = now
            return True

    @staticmethod
    def _extract_candidate_addresses(payload: Dict) -> List[str]:
        found: Set[str] = set()
        for value in _iter_strings(payload):
            for address in ADDRESS_RE.findall(value):
                found.add(address.lower())
        return list(found)

    def _find_target_by_address(self, payload: Dict) -> Optional[Dict]:
        self.get_watchlist()
        for address in self._extract_candidate_addresses(payload):
            target = self._watch_targets_by_address.get(address)
            if target:
                return target
        return None

    def _find_targets_by_text(self, text: str) -> List[Dict]:
        if not text:
            return []
        lowered = text.lower()
        matches = []
        for target in self.get_watchlist():
            name = (target.get("name") or "").lower()
            slug = (target.get("slug") or "").lower()
            if not name:
                continue
            if name in lowered or (slug and slug in lowered):
                matches.append(target)
        return matches

    def _run_audit_task(self, target: Dict, trigger_type: str, trigger_payload: Dict):
        protocol = target.get("name", "Unknown")
        try:
            manifest_bundle = self._get_manifest_bundle()
            report = self.audit_service.audit_target(
                target,
                manifest_bundle,
            )
            if not report:
                logger.warning("Audit skipped for %s: no report generated", protocol)
                return
            report["trigger"] = {
                "type": trigger_type,
                "timestamp": datetime.utcnow().isoformat(),
                "payload_sample": str(trigger_payload)[:1200],
            }
            report_path = save_audit_report(protocol, report)
            logger.info("Event-driven audit completed for %s -> %s", protocol, report_path)
        except Exception as exc:
            logger.error("Event-driven audit failed for %s: %s", protocol, exc, exc_info=True)

    def queue_onchain_event(self, payload: Dict) -> Dict:
        target = self._find_target_by_address(payload)
        if not target:
            return {
                "status": "ignored",
                "reason": "address_not_watched",
                "watched_addresses": len(self._watch_targets_by_address),
            }

        address = (target.get("address") or "").lower()
        if address and not self._can_reaudit(f"address:{address}"):
            return {
                "status": "ignored",
                "reason": "rate_limited",
                "address": target.get("address"),
                "protocol": target.get("name"),
            }

        self.executor.submit(self._run_audit_task, target, "onchain_change", payload)
        return {
            "status": "queued",
            "protocol": target.get("name"),
            "address": target.get("address"),
            "chain": target.get("chain"),
            "trigger": "onchain_change",
        }

    def queue_social_event(self, payload: Dict, source: str = "social") -> Dict:
        text = ""
        for key in ("text", "content", "title", "body"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                text = value
                break
        if not text and isinstance(payload.get("cast"), dict):
            cast_text = payload["cast"].get("text")
            if isinstance(cast_text, str):
                text = cast_text

        targets = self._find_targets_by_text(text)
        if not targets:
            return {
                "status": "ignored",
                "reason": "no_watched_protocol_in_text",
            }

        queued_protocols = []
        for target in targets[:3]:
            audit_key = f"social:{(target.get('address') or target.get('name', '')).lower()}"
            if not self._can_reaudit(audit_key):
                continue
            queued_protocols.append(target.get("name"))
            enriched_payload = dict(payload)
            enriched_payload["source"] = source
            self.executor.submit(self._run_audit_task, target, "social_news", enriched_payload)

        if not queued_protocols:
            return {
                "status": "ignored",
                "reason": "rate_limited",
            }

        return {
            "status": "queued",
            "trigger": "social_news",
            "protocols": queued_protocols,
        }
