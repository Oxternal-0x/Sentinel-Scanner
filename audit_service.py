import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from badge_service import BadgeService
from bytecode_analyzer import BytecodeAnalyzer
from compliance_engine import LegalInterpreter
from database import SentinelDB
from etherscan import MultichainFetcher
from fuzzing_engine import FuzzingEngine
from governance_report import GovernanceReporter
from jurisdiction import JurisdictionMapper
from legal_diff import LegalDiffEngine
from sentiment_monitor import SocialSentimentMonitor

logger = logging.getLogger(__name__)

SOURCE_CODE_LIMIT = 4000


class AuditService:
    """Shared audit pipeline used by the scheduler, Telegram bot, and dashboard."""

    def __init__(
        self,
        db: Optional[SentinelDB] = None,
        interpreter: Optional[LegalInterpreter] = None,
        fetcher: Optional[MultichainFetcher] = None,
    ):
        self.db = db or SentinelDB()
        self.interpreter = interpreter or LegalInterpreter()
        self.fetcher = fetcher or MultichainFetcher()
        self.bytecode_analyzer = BytecodeAnalyzer()
        self.fuzzing = FuzzingEngine()
        self.jurisdiction_mapper = JurisdictionMapper()
        self.legal_diff = LegalDiffEngine()
        self.sentiment = SocialSentimentMonitor()
        self.badges = BadgeService()
        self.governance = GovernanceReporter()

    def analyze_contract_compliance(
        self,
        source_material: str,
        manifest: Dict,
        context: Optional[Dict] = None,
    ) -> Dict:
        context = context or {}
        manifest_text = (
            "No specific compliance rules available. Perform a conservative risk review."
            if not manifest or "error" in manifest
            else json.dumps(manifest, indent=2)
        )

        prompt = f"""
AUDIT MISSION: Compare the following smart-contract artifact against these regulatory rules.

REGULATORY RULES:
{manifest_text}

AUDIT CONTEXT:
{json.dumps(context, indent=2)}

CONTRACT OR DECOMPILED MATERIAL:
{source_material[:SOURCE_CODE_LIMIT]}

Return JSON with:
{{
  "compliance_score": 0-100,
  "violations": ["specific issues"],
  "remediation": "fix guidance",
  "confidence": 0-1
}}
"""
        try:
            result = self.interpreter.generate_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            if not all(key in result for key in ["compliance_score", "violations", "remediation"]):
                raise ValueError("Invalid AI audit response structure")
            return result
        except Exception as exc:
            logger.error("Error during compliance analysis: %s", exc, exc_info=True)
            return {
                "compliance_score": 0,
                "violations": ["AI analysis failed"],
                "remediation": str(exc),
                "confidence": 0.0,
            }

    def build_manifest_snapshot(
        self,
        latest_law: Optional[Dict],
        manifest: Dict,
        jurisdiction: str,
    ) -> Dict:
        version = self.db.new_manifest_version()
        previous = self.db.get_latest_manifest()
        previous_manifest = previous["manifest"] if previous else {}
        diff = self.legal_diff.diff_manifests(previous_manifest, manifest)
        delta_report = self.legal_diff.build_delta_report(diff, self.db.get_protocols_newly_at_risk())
        source_title = latest_law["title"] if latest_law else "Default compliance rule"
        self.db.save_manifest_snapshot(version, source_title, jurisdiction, manifest, delta_report)
        return {
            "version": version,
            "manifest": manifest,
            "diff": delta_report,
            "source_title": source_title,
            "jurisdiction": jurisdiction,
        }

    def audit_target(self, target: Dict, manifest_bundle: Dict) -> Optional[Dict]:
        chain = (target.get("chain") or "ethereum").lower()
        if chain == "multi-chain":
            chain = "ethereum"

        if not target.get("address"):
            return None

        jurisdiction = self.jurisdiction_mapper.fingerprint(target)
        signals = self.sentiment.collect_signals(target["name"])
        for signal in signals:
            self.db.save_social_signal(
                protocol=signal["protocol"],
                source=signal["source"],
                signal_type=signal["signal_type"],
                summary=signal["summary"],
                confidence=signal["confidence"],
                raw_payload=signal,
            )

        artifact = self.fetcher.get_contract_artifact(target["address"], chain)
        if not artifact:
            return None

        source_quality = artifact.get("verification_status", "unknown")
        source_material = artifact.get("source_code") or artifact.get("bytecode", "")
        bytecode_analysis = {}
        if source_quality != "verified_source":
            bytecode_analysis = self.bytecode_analyzer.analyze(artifact)
            self.bytecode_analyzer.persist_analysis(target["name"], bytecode_analysis)
            source_material = bytecode_analysis.get("decompiled_text") or artifact.get("bytecode", "")

        fuzz_result = self.fuzzing.run(artifact)
        verdict = self.analyze_contract_compliance(
            source_material,
            manifest_bundle["manifest"],
            context={
                "jurisdiction": jurisdiction,
                "source_quality": source_quality,
                "bytecode_analysis": bytecode_analysis,
                "fuzzing": fuzz_result,
                "social_signals": signals,
            },
        )

        if source_quality != "verified_source":
            verdict["violations"] = verdict.get("violations", []) + [
                "Contract source is not verified; audit is based on bytecode/decompilation fallback.",
            ]
            verdict["compliance_score"] = min(verdict.get("compliance_score", 0), 45)

        if signals:
            verdict["violations"] = verdict.get("violations", []) + [
                f"External signal detected: {signal['summary']}" for signal in signals[:2]
            ]
            verdict["compliance_score"] = max(verdict.get("compliance_score", 0) - 10, 0)

        report = {
            "protocol_name": target["name"],
            "chain": chain,
            "address": target["address"],
            "tvl": target.get("tvl", 0),
            "scan_timestamp": datetime.now().isoformat(),
            "source_quality": source_quality,
            "jurisdiction": jurisdiction["region"],
            "manifest_version": manifest_bundle["version"],
            "compliance_verdict": verdict,
            "contract_info": {
                "contract_name": artifact.get("contract_name", "Unknown"),
                "compiler_version": artifact.get("compiler_version", "Unknown"),
                "is_proxy": artifact.get("is_proxy", False),
            },
            "bytecode_analysis": bytecode_analysis,
            "fuzzing": fuzz_result,
            "social_signals": signals,
            "legal_delta": manifest_bundle.get("diff", {}),
        }
        report["risk_level"] = self._risk_from_score(verdict.get("compliance_score", 0))
        report["governance_report"] = self.governance.build_snapshot_report(report)

        badge = self.badges.issue_eligibility(
            protocol_name=target["name"],
            chain=chain,
            address=target["address"],
            score=verdict.get("compliance_score", 0),
        )
        report["badge"] = badge
        self.db.save_badge_eligibility(
            protocol=target["name"],
            chain=chain,
            address=target["address"],
            score=verdict.get("compliance_score", 0),
            status=badge["status"],
            metadata_path=badge["metadata_path"],
        )

        self.db.save_audit(
            protocol=target["name"],
            chain=chain,
            address=target["address"],
            tvl=target.get("tvl", 0),
            score=verdict.get("compliance_score", 0),
            result=report,
            source_quality=source_quality,
            jurisdiction=jurisdiction["region"],
            manifest_version=manifest_bundle["version"],
        )
        return report

    def explain_protocol(self, protocol_name: str) -> str:
        latest = self.db.get_latest_audit(protocol_name)
        if not latest:
            return f"No audit history found for {protocol_name}."

        result = latest["result"]
        verdict = result.get("compliance_verdict", {})
        violations = verdict.get("violations", [])
        joined = "\n".join(f"- {violation}" for violation in violations[:5]) if violations else "- No violations recorded."
        return (
            f"{protocol_name} scored {latest['score']} ({latest['risk_level']}) on {latest['run_at']}.\n"
            f"Source quality: {latest.get('source_quality', 'unknown')}\n"
            f"Jurisdiction focus: {latest.get('jurisdiction', 'global')}\n"
            f"Top findings:\n{joined}\n"
            f"Remediation: {verdict.get('remediation', 'N/A')}"
        )

    def run_single_audit(self, address: str, chain: str = "ethereum", protocol_name: Optional[str] = None) -> Dict:
        manifest_bundle = self.db.get_latest_manifest()
        if not manifest_bundle:
            default_manifest = self.interpreter.translate_law_to_rules(
                "Default Rule: Flag missing pause controls, blacklist gaps, and unverified bytecode as elevated risk."
            )
            manifest_bundle = self.build_manifest_snapshot(None, default_manifest, "global")

        target = {
            "name": protocol_name or address,
            "chain": chain,
            "address": address,
            "tvl": 0,
            "category": "manual",
        }
        report = self.audit_target(target, manifest_bundle)
        if not report:
            return {
                "name": protocol_name or address,
                "score": 0,
                "verdict": "Unable to fetch contract source or bytecode.",
                "report": None,
            }

        verdict = report["compliance_verdict"]
        return {
            "name": report["protocol_name"],
            "score": verdict.get("compliance_score", 0),
            "verdict": report["risk_level"],
            "report": report,
        }

    def _risk_from_score(self, score: int) -> str:
        if score < 50:
            return "HIGH"
        if score < 80:
            return "MEDIUM"
        return "LOW"
