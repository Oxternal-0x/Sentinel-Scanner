import requests
from xml.etree import ElementTree
from typing import List, Dict
import logging
from datetime import datetime
import re
from html import unescape

logger = logging.getLogger(__name__)

REGULATORY_RELEVANCE_KEYWORDS = {
    "crypto": 5,
    "digital asset": 5,
    "digital assets": 5,
    "stablecoin": 5,
    "stablecoins": 5,
    "defi": 5,
    "blockchain": 4,
    "token": 4,
    "tokens": 4,
    "virtual asset": 4,
    "virtual assets": 4,
    "exchange": 3,
    "custody": 3,
    "broker": 2,
    "securities": 2,
    "commodity": 2,
}

class RegulatoryListener:
    """
    Monitors global regulatory bodies for new crypto/DeFi enforcement and guidance.
    Polls RSS feeds from SEC, CFTC, and ESMA to detect regulatory changes.
    """

    DEFAULT_FEEDS = {
        "SEC_Press": "https://www.sec.gov/news/pressreleases.rss",
        "CFTC_News": "https://www.cftc.gov/RSS/RSSGP/rssgp.xml",
        "ESMA_News": "https://www.esma.europa.eu/press-news/esma-news"
    }

    def __init__(self, feeds: Dict[str, str] = None):
        # High-signal feeds for Crypto Compliance
        self.feeds = feeds if feeds is not None else self.DEFAULT_FEEDS.copy()


    def _safe_text(self, element):
        if element is not None and element.text:
            return element.text.strip()
        return ""

    def _strip_html(self, raw_text: str) -> str:
        clean_text = re.sub(r"<[^>]+>", " ", raw_text or "")
        clean_text = unescape(clean_text)
        return re.sub(r"\s+", " ", clean_text).strip()

    def _parse_rss_items(self, agency: str, xml_content: bytes, limit: int) -> List[Dict]:
        alerts = []
        root = ElementTree.fromstring(xml_content)
        items = root.findall(".//item")

        for item in items[:limit]:
            title = self._safe_text(item.find("title"))
            if not title:
                continue

            alerts.append({
                "agency": agency,
                "title": title,
                "link": self._safe_text(item.find("link")),
                "description": self._safe_text(item.find("description")),
                "published": self._safe_text(item.find("pubDate")) or datetime.now().isoformat(),
                "detected_at": datetime.now().isoformat()
            })

        return alerts

    def _parse_esma_html_items(self, agency: str, html_content: str, limit: int) -> List[Dict]:
        alerts = []
        seen_links = set()
        pattern = re.compile(
            r'<a[^>]+href="(?P<link>/press-news/esma-news/[^"]+)"[^>]*>(?P<title>.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )

        for match in pattern.finditer(html_content):
            relative_link = match.group("link")
            if relative_link in seen_links:
                continue

            title = self._strip_html(match.group("title"))
            if not title or len(title) < 10:
                continue

            seen_links.add(relative_link)
            alerts.append({
                "agency": agency,
                "title": title,
                "link": f"https://www.esma.europa.eu{relative_link}",
                "description": "",
                "published": datetime.now().isoformat(),
                "detected_at": datetime.now().isoformat()
            })

            if len(alerts) >= limit:
                break

        return alerts

    def get_latest_alerts(self, limit: int = 3) -> List[Dict]:
        """
        Polls global regulatory bodies for new enforcement or guidance.
        Returns the most recent alerts from each feed.
        """
        alerts = []
        logger.info("📡 Scanning Global Regulatory Feeds...")

        headers = {'User-Agent': 'Sentinel-Scanner/1.0 (Compliance Research)'}
        for agency, url in self.feeds.items():
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                if agency == "ESMA_News":
                    parsed_alerts = self._parse_esma_html_items(agency, response.text, limit)
                else:
                    parsed_alerts = self._parse_rss_items(agency, response.content, limit)

                for alert in parsed_alerts:
                    if alert not in alerts:
                        alerts.append(alert)
                        logger.debug(f"📄 Found alert from {agency}: {alert['title'][:50]}...")

            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ Network issue while fetching {agency}: {e}")
            except ElementTree.ParseError as e:
                logger.warning(f"⚠️ XML parse failure for {agency}: {e}")
            except Exception as e:
                logger.warning(f"⚠️ Unexpected error for {agency}: {e}")

        # Sort alerts by publication date (most recent first)
        alert_sort_key = lambda x: x.get('published', '')
        alerts.sort(key=alert_sort_key, reverse=True)

        logger.info(f"✅ Retrieved {len(alerts)} regulatory alerts")
        return alerts

    def rank_alerts_for_compliance(self, alerts: List[Dict]) -> List[Dict]:
        """Ranks alerts by crypto/compliance relevance before recency."""
        ranked = []
        for alert in alerts:
            haystack = f"{alert.get('title', '')} {alert.get('description', '')}".lower()
            score = 0
            for keyword, weight in REGULATORY_RELEVANCE_KEYWORDS.items():
                if keyword in haystack:
                    score += weight

            ranked.append(
                {
                    **alert,
                    "relevance_score": score,
                }
            )

        ranked.sort(key=lambda item: (item.get("relevance_score", 0), item.get("published", "")), reverse=True)
        return ranked

    def has_new_regulations(self, last_check_timestamp: str = None) -> bool:
        """
        Checks if there are new regulations since the last check.
        Returns True if new alerts are found.
        """
        alerts = self.get_latest_alerts(limit=1)
        if not alerts:
            return False

        if not last_check_timestamp:
            return True

        # Check if the most recent alert is newer than our last check
        try:
            most_recent = datetime.fromisoformat(alerts[0]['detected_at'])
            last_check = datetime.fromisoformat(last_check_timestamp)
            return most_recent > last_check
        except (ValueError, KeyError):
            # If we can't parse timestamps, assume there are new regulations
            return True
