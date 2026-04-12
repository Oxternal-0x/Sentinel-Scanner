import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from audit_service import AuditService
from compliance_engine import LegalInterpreter
from database import SentinelDB
from etherscan import MultichainFetcher
from indexer import DeFiLlamaIndexer
from jurisdiction import JurisdictionMapper
from law_fetcher import RegulatoryListener
from mempool_monitor import MempoolMonitor
from telegram_notifier import TelegramNotifier

DEFAULT_PERCENTILE = 0.10
MAX_AUDIT_TARGETS = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def save_audit_report(protocol_name: str, report_data: Dict) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"reports/{protocol_name}_{timestamp}.json".replace(" ", "_")

    os.makedirs("reports", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as handle:
        json.dump(report_data, handle, indent=4)

    logger.info("💾 Report saved: %s", filename)
    return filename


def select_regulatory_alert(listener: RegulatoryListener, jurisdiction: str = "global") -> Optional[Dict]:
    alerts = listener.get_latest_alerts(limit=5)
    if not alerts:
        logger.info("📡 No new regulations detected today.")
        return None

    ranked_alerts = listener.rank_alerts_for_compliance(alerts)
    if ranked_alerts and ranked_alerts[0].get("relevance_score", 0) <= 0:
        logger.warning("⚠️ No high-signal crypto/regulatory alert found; using most recent alert as fallback")

    priority_map = {
        "us": ["SEC_Press", "CFTC_News", "ESMA_News"],
        "eu": ["ESMA_News", "SEC_Press", "CFTC_News"],
        "global": ["SEC_Press", "ESMA_News", "CFTC_News"],
    }
    priority = priority_map.get(jurisdiction, priority_map["global"])
    for agency in priority:
        for alert in ranked_alerts:
            if alert.get("agency") == agency:
                return alert
    return ranked_alerts[0]


def autonomous_update(audit_service: AuditService) -> Dict:
    listener = RegulatoryListener()
    latest_law = select_regulatory_alert(listener)

    if latest_law:
        logger.info("🆕 New Regulation Detected from %s: %s", latest_law["agency"], latest_law["title"])
        context = f"Context: {latest_law['title']}. Details: {latest_law['description']}"
        manifest = audit_service.interpreter.translate_law_to_rules(context)
        manifest["regulatory_source"] = latest_law
        jurisdiction = "global"
        if latest_law["agency"] == "ESMA_News":
            jurisdiction = "eu"
        elif latest_law["agency"] in {"SEC_Press", "CFTC_News"}:
            jurisdiction = "us"

        return audit_service.build_manifest_snapshot(latest_law, manifest, jurisdiction)

    logger.info("🔄 Using default compliance rules (no new regulations detected)")
    default_law = (
        "New Rule: All cross-chain bridges must implement a 4-hour transaction delay "
        "for amounts over $1M and maintain emergency pause capability."
    )
    manifest = audit_service.interpreter.translate_law_to_rules(default_law)
    return audit_service.build_manifest_snapshot(None, manifest, "global")


def explain_protocol(protocol_name: str) -> str:
    return AuditService(db=SentinelDB()).explain_protocol(protocol_name)


def analyze_contract_compliance(source_code: str, manifest: dict) -> Dict:
    """Compatibility wrapper retained for existing test scripts."""
    return AuditService(db=SentinelDB()).analyze_contract_compliance(source_code, manifest)


def run_sentinel_cycle() -> None:
    try:
        logger.info("🚀 Starting Sentinel Scanner cycle...")

        db = SentinelDB()
        interpreter = LegalInterpreter()
        fetcher = MultichainFetcher()
        audit_service = AuditService(db=db, interpreter=interpreter, fetcher=fetcher)
        indexer = DeFiLlamaIndexer()
        notifier = TelegramNotifier()
        mempool = MempoolMonitor()

        logger.info("🧠 Sentinel is checking for new regulatory updates...")
        manifest_bundle = autonomous_update(audit_service)
        diff_payload = manifest_bundle.get("diff", {})
        if diff_payload.get("diff", {}).get("added_rules") or diff_payload.get("diff", {}).get("removed_rules"):
            notifier.notify_delta_report(manifest_bundle["diff"])

        logger.info("📡 Querying DeFiLlama for top 10% of protocols by TVL...")
        targets: List[Dict] = indexer.get_top_percentile_targets(DEFAULT_PERCENTILE, require_address=True)
        logger.info(
            "🎯 Found %s protocols in the top %s%% by TVL.",
            len(targets),
            int(DEFAULT_PERCENTILE * 100),
        )
        if not targets:
            logger.warning("⚠️ No protocols found matching TVL threshold")
            return

        logger.info("🔍 Beginning audit of top %s protocol(s)...", min(MAX_AUDIT_TARGETS, len(targets)))
        watched_addresses = [target.get("address") for target in targets[:MAX_AUDIT_TARGETS] if target.get("address")]
        pending_risks = mempool.scan_pending_risks(watched_addresses)
        if pending_risks:
            notifier.notify_pending_risk(pending_risks[0])

        completed_reports = []
        for target in targets[:MAX_AUDIT_TARGETS]:
            logger.info("🔍 Auditing Protocol: %s (%s)", target["name"], target["chain"])
            logger.info("💰 TVL: $%0.2f", target["tvl"])
            try:
                report = audit_service.audit_target(target, manifest_bundle)
            except Exception as exc:
                logger.error("Error auditing protocol %s: %s", target.get("name", "UNKNOWN"), exc, exc_info=True)
                continue

            if not report:
                logger.warning("⚠️ Could not fetch contract artifact for %s", target.get("address"))
                continue

            save_audit_report(target["name"], report)
            completed_reports.append(report)
            logger.info("🧾 Compliance verdict for %s: %s", target["name"], report["compliance_verdict"])

        logger.info("✨ Sentinel Scanner cycle completed successfully")
        notifier.notify_audit_complete(len(completed_reports), bool(manifest_bundle.get("manifest")))

    except Exception as exc:
        logger.critical("Fatal error in Sentinel Scanner cycle: %s", exc, exc_info=True)
        TelegramNotifier().notify_error(f"Sentinel cycle failed: {exc}")
        raise


if __name__ == "__main__":
    try:
        run_sentinel_cycle()
    except Exception as exc:
        logger.critical("Application failed: %s", exc, exc_info=True)
        raise SystemExit(1)
