import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SentinelNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self._is_valid_chat_id(self.chat_id))

        if not self.enabled:
            print("⚠️ Telegram alerts disabled (missing TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID)")

    def _is_valid_chat_id(self, chat_id: str) -> bool:
        if not chat_id:
            return False
        value = str(chat_id).strip()
        if value.startswith("-"):
            value = value[1:]
        return value.isdigit()

    def send_alert(self, protocol: str, score: int, chain: str, tvl: float):
        """Sends a formatted alert to Telegram for high-risk findings."""
        if not self.enabled:
            return

        message = (
            f"🚨 *SENTINEL HIGH-RISK ALERT*\n\n"
            f"*Protocol:* {protocol}\n"
            f"*Chain:* {chain}\n"
            f"*TVL:* ${tvl:,.2f}\n"
            f"*Compliance Score:* {score}/100\n\n"
            f"⚠️ _Action Required: Immediate Regulatory Review._"
        )

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                print(f"⚠️ Notification failed HTTP {response.status_code}: {response.text}")
        except Exception as e:
            print(f"⚠️ Notification failed: {e}")
