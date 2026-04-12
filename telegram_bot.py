import logging
import os
from typing import Optional

import telebot
from dotenv import load_dotenv

from audit_service import AuditService
from database import SentinelDB

load_dotenv(dotenv_path=".env", override=False)
load_dotenv(dotenv_path=".evn", override=True)

logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

db = SentinelDB()
audit_service = AuditService(db=db)
bot = telebot.TeleBot(TOKEN) if TOKEN else None


def _normalized_chat_id(chat_id: Optional[str]) -> Optional[str]:
    if not chat_id:
        return None
    value = str(chat_id).strip()
    if value.startswith("-"):
        return value
    return value if value.isdigit() else None


def _authorized(message) -> bool:
    expected_chat_id = _normalized_chat_id(CHAT_ID)
    if not expected_chat_id:
        return True
    return str(message.chat.id) == expected_chat_id


def _guard(message) -> bool:
    if _authorized(message):
        return True
    bot.reply_to(message, "This bot is configured for a different chat.")
    return False


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    if not _guard(message):
        return
    bot.reply_to(
        message,
        "🛡️ *Sentinel Compliance Bot Active*\n"
        "Commands:\n"
        "/status - Current scan stats\n"
        "/audit [address] [chain] - Manual contract scan\n"
        "/latest - Last elevated-risk finding\n"
        "/explain [protocol] - Explain latest verdict",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["status"])
def show_status(message):
    if not _guard(message):
        return
    stats = db.get_stats()
    bot.reply_to(
        message,
        f"📊 *Current Ledger Status*\n"
        f"Total Audits: {stats['total']}\n"
        f"High Risk: {stats['high_risk']}\n"
        f"Medium Risk: {stats['medium_risk']}\n"
        f"Low Risk: {stats['low_risk']}",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["latest"])
def latest_finding(message):
    if not _guard(message):
        return
    latest = db.get_latest_high_risk()
    if not latest:
        bot.reply_to(message, "No elevated-risk findings have been recorded yet.")
        return

    bot.reply_to(
        message,
        f"🚨 *Latest Elevated Risk*\n"
        f"Protocol: {latest['protocol']}\n"
        f"Chain: {latest['chain']}\n"
        f"Score: {latest['score']}/100\n"
        f"Risk: {latest['risk_level']}\n"
        f"Run At: {latest['run_at']}",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["explain"])
def explain(message):
    if not _guard(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Please provide a protocol: `/explain Aave V3`", parse_mode="Markdown")
        return

    protocol = parts[1].strip()
    explanation = audit_service.explain_protocol(protocol)
    bot.reply_to(message, explanation)


@bot.message_handler(commands=["audit"])
def manual_audit(message):
    if not _guard(message):
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Please provide an address: `/audit 0x123... [chain]`", parse_mode="Markdown")
        return

    address = parts[1]
    chain = parts[2] if len(parts) > 2 else "ethereum"
    bot.reply_to(message, f"🔍 Initiating ad-hoc audit for: `{address}` on `{chain}`...", parse_mode="Markdown")

    try:
        result = audit_service.run_single_audit(address=address, chain=chain)
    except Exception as exc:
        logger.exception("Manual audit failed")
        bot.reply_to(message, f"Audit failed: {exc}")
        return

    report = result.get("report") or {}
    verdict = report.get("compliance_verdict", {})
    response = (
        f"✅ *Audit Complete*\n"
        f"Protocol: {result['name']}\n"
        f"Score: {result['score']}/100\n"
        f"Verdict: {result['verdict']}\n"
        f"Source Quality: {report.get('source_quality', 'unknown')}\n"
        f"Top Issue: {(verdict.get('violations') or ['No issues recorded'])[0]}"
    )
    bot.reply_to(message, response, parse_mode="Markdown")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is required to run telegram_bot.py")
    print("🚀 Sentinel Bot is listening...")
    bot.infinity_polling()
