import requests
import logging
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=False)
load_dotenv(dotenv_path=".evn", override=True)
logger = logging.getLogger(__name__)

class TelegramNotifier:
    """
    Sends automated notifications to Telegram when regulatory changes are detected
    or when audit cycles complete. Enables hands-off monitoring.
    """

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self._is_valid_chat_id(self.chat_id))

        if not self.enabled:
            logger.warning("⚠️ Telegram notifications disabled - missing or invalid TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID")
        else:
            logger.info("✅ Telegram notifications enabled")

    def _is_valid_chat_id(self, chat_id: Optional[str]) -> bool:
        if not chat_id:
            return False
        value = str(chat_id).strip()
        if value.startswith("-"):
            value = value[1:]
        return value.isdigit()

    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Sends a message to the configured Telegram chat.
        Returns True if successful, False otherwise.
        """
        if not self.enabled:
            logger.debug("Telegram notifications disabled, skipping message")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("📱 Telegram notification sent successfully")
                return True
            else:
                logger.error(f"Failed to send Telegram message: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def notify_regulatory_update(self, alert: dict) -> None:
        """
        Notifies about new regulatory changes detected.
        """
        message = f"""🔔 *Regulatory Alert Detected*

*Agency:* {alert['agency']}
*Title:* {alert['title']}
*Published:* {alert.get('published', 'Unknown')[:10]}

_Sentinel is now updating compliance rules and auditing top protocols..._

[View Full Article]({alert['link']})"""

        self.send_message(message)

    def notify_audit_complete(self, protocols_audited: int, new_regulations: bool = False) -> None:
        """
        Notifies when an audit cycle completes.
        """
        regulation_status = "🆕 New regulations detected" if new_regulations else "📋 Using existing rules"

        message = f"""✅ *Sentinel Audit Cycle Complete*

*Protocols Audited:* {protocols_audited}
*Status:* {regulation_status}
*Reports:* Check `/reports` directory

_Next cycle: Tomorrow at 9:00 AM_"""

        self.send_message(message)

    def notify_error(self, error_message: str) -> None:
        """
        Notifies about critical errors that require attention.
        """
        message = f"""🚨 *Sentinel Error Alert*

{error_message}

_Please check logs and resolve the issue._"""

        self.send_message(message)

    def notify_delta_report(self, delta_report: dict) -> None:
        """Notifies when regulatory rules materially change."""
        summary = delta_report.get("summary", "Manifest updated.")
        message = f"""⚖️ *Sentinel Legal Delta*

{summary}

_Use /delta in the Telegram bot for the full diff payload._"""
        self.send_message(message)

    def notify_pending_risk(self, finding: dict) -> None:
        """Notifies when a watched pending transaction appears risky."""
        message = f"""⏱️ *Shadow Mempool Alert*

*Tx:* `{finding.get('tx_hash', 'unknown')}`
*To:* `{finding.get('to', 'unknown')}`
*Risk:* {finding.get('risk', 'unknown')}
"""
        self.send_message(message)
