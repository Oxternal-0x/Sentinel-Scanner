from typing import Dict, List


class LegalDiffEngine:
    """Computes changes between the previously active and new compliance manifests."""

    def diff_manifests(self, previous_manifest: Dict, current_manifest: Dict) -> Dict:
        previous_rules = self._as_rule_list(previous_manifest)
        current_rules = self._as_rule_list(current_manifest)

        previous_set = set(previous_rules)
        current_set = set(current_rules)

        return {
            "added_rules": sorted(current_set - previous_set),
            "removed_rules": sorted(previous_set - current_set),
            "unchanged_count": len(previous_set & current_set),
            "previous_rule_count": len(previous_rules),
            "current_rule_count": len(current_rules),
        }

    def build_delta_report(self, diff: Dict, newly_at_risk: List[Dict]) -> Dict:
        return {
            "summary": (
                f"Added {len(diff.get('added_rules', []))} rule(s), "
                f"removed {len(diff.get('removed_rules', []))} rule(s), "
                f"and {len(newly_at_risk)} protocol(s) are currently flagged HIGH/MEDIUM."
            ),
            "diff": diff,
            "newly_at_risk": newly_at_risk,
        }

    def _as_rule_list(self, manifest: Dict) -> List[str]:
        if not manifest:
            return []

        rules = manifest.get("extracted_rules")
        if isinstance(rules, list):
            return [str(rule).strip() for rule in rules if str(rule).strip()]

        if isinstance(rules, dict):
            flattened = []
            for key, value in rules.items():
                flattened.append(f"{key}: {value}")
            return flattened

        return []
