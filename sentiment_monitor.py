import os
from typing import Dict, List

import requests
from xml.etree import ElementTree


KEYWORDS = {
    "security-offering": ["security token", "offering", "yield-bearing", "dividend", "profit share"],
    "governance-change": ["proposal", "governance", "tokenomics", "migration", "strategic pivot"],
    "compliance-risk": ["investigation", "lawsuit", "enforcement", "sanction", "delist"],
}


class SocialSentimentMonitor:
    """Monitors configured RSS/Atom feeds for protocol-specific risk language."""

    def __init__(self):
        self.feed_urls = [
            url.strip()
            for url in os.getenv("SENTINEL_SOCIAL_FEEDS", "").split(",")
            if url.strip()
        ]

    def collect_signals(self, protocol_name: str, limit: int = 5) -> List[Dict]:
        if not self.feed_urls:
            return []

        protocol_terms = {
            protocol_name.lower(),
            protocol_name.lower().replace(" ", ""),
            protocol_name.lower().split()[0],
        }
        signals: List[Dict] = []

        for feed_url in self.feed_urls:
            try:
                response = requests.get(feed_url, timeout=10)
                response.raise_for_status()
                root = ElementTree.fromstring(response.content)
            except Exception:
                continue

            for item in root.findall(".//item")[:limit]:
                title = self._read(item.find("title"))
                description = self._read(item.find("description"))
                haystack = f"{title} {description}".lower()

                if not any(term in haystack for term in protocol_terms):
                    continue

                matched_labels = [label for label, terms in KEYWORDS.items() if any(term in haystack for term in terms)]
                if not matched_labels:
                    continue

                signals.append(
                    {
                        "protocol": protocol_name,
                        "source": feed_url,
                        "signal_type": matched_labels[0],
                        "summary": title or description[:140],
                        "confidence": min(1.0, 0.35 + 0.15 * len(matched_labels)),
                    }
                )

        return signals

    def _read(self, element) -> str:
        if element is not None and element.text:
            return element.text.strip()
        return ""
