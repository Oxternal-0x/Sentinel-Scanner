import json
import os
from typing import Dict, Optional


class BadgeService:
    """Creates off-chain metadata for Sentinel Verified eligibility."""

    def issue_eligibility(self, protocol_name: str, chain: str, address: Optional[str], score: int) -> Dict:
        eligible = score >= 90
        os.makedirs("badges", exist_ok=True)
        filename = f"badges/{protocol_name.replace(' ', '_')}.json"

        metadata = {
            "name": f"Sentinel Verified: {protocol_name}",
            "description": "Off-chain eligibility record for Sentinel Verified compliance badge.",
            "protocol": protocol_name,
            "chain": chain,
            "address": address,
            "score": score,
            "eligible": eligible,
            "badge_type": "soulbound-eligibility",
        }

        with open(filename, "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)

        return {
            "status": "eligible" if eligible else "ineligible",
            "metadata_path": filename,
            "metadata": metadata,
        }
