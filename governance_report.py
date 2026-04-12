from typing import Dict


class GovernanceReporter:
    """Builds Snapshot-style governance reports from Sentinel audits."""

    def build_snapshot_report(self, audit_report: Dict) -> str:
        verdict = audit_report.get("compliance_verdict", {})
        violations = verdict.get("violations", [])
        risk_level = audit_report.get("risk_level", "UNKNOWN")

        lines = [
            f"# Sentinel Audit Report: {audit_report.get('protocol_name', 'Unknown Protocol')}",
            "",
            f"- Chain: {audit_report.get('chain', 'unknown')}",
            f"- Address: {audit_report.get('address', 'n/a')}",
            f"- TVL: ${audit_report.get('tvl', 0):,.2f}",
            f"- Compliance Score: {verdict.get('compliance_score', 0)}",
            f"- Risk Level: {risk_level}",
            f"- Source Quality: {audit_report.get('source_quality', 'unknown')}",
            "",
            "## Violations",
        ]

        if violations:
            lines.extend([f"- {item}" for item in violations])
        else:
            lines.append("- No explicit violations found.")

        lines.extend(
            [
                "",
                "## Remediation",
                verdict.get("remediation", "No remediation available."),
            ]
        )
        return "\n".join(lines)
