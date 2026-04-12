from typing import Dict


CHAIN_REGION_MAP = {
    "ethereum": "us",
    "arbitrum": "us",
    "optimism": "us",
    "polygon": "eu",
    "bsc": "global",
    "multi-chain": "global",
}


REGION_RULE_PRIORITY = {
    "us": ["SEC_Press", "CFTC_News", "ESMA_News"],
    "eu": ["ESMA_News", "SEC_Press", "CFTC_News"],
    "global": ["SEC_Press", "ESMA_News", "CFTC_News"],
}


class JurisdictionMapper:
    """Maps protocol context to the jurisdiction Sentinel should emphasize."""

    def fingerprint(self, target: Dict) -> Dict:
        chain = (target.get("chain") or "global").strip().lower()
        region = CHAIN_REGION_MAP.get(chain, "global")
        category = (target.get("category") or "").strip().lower()

        if "stablecoin" in category or "bridge" in category:
            region = "us"

        priorities = REGION_RULE_PRIORITY.get(region, REGION_RULE_PRIORITY["global"])
        return {
            "region": region,
            "priority_feeds": priorities,
            "chain": chain,
            "category": category or "unknown",
        }
