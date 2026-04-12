#!/usr/bin/env python3
"""
Test script for Sentinel-Scanner autonomous features.
Tests the regulatory listener and telegram notifier without running full audit.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from law_fetcher import RegulatoryListener
from telegram_notifier import TelegramNotifier
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_regulatory_listener():
    """Test the regulatory listener functionality."""
    print("📰 Testing Regulatory Listener...")

    listener = RegulatoryListener()
    alerts = listener.get_latest_alerts(limit=2)

    if alerts:
        print(f"✅ Found {len(alerts)} regulatory alerts:")
        for i, alert in enumerate(alerts, 1):
            print(f"   {i}. {alert['agency']}: {alert['title'][:60]}...")
    else:
        print("⚠️ No regulatory alerts found (this could be normal)")

    return bool(alerts)

def test_telegram_notifier():
    """Test the telegram notifier (won't send if not configured)."""
    print("\n📱 Testing Telegram Notifier...")

    notifier = TelegramNotifier()

    if notifier.enabled:
        print("✅ Telegram notifications are configured")
        # Don't actually send a test message to avoid spam
        print("   (Skipping actual message send to avoid spam)")
    else:
        print("⚠️ Telegram notifications not configured (add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env)")

    return notifier.enabled

def main():
    print("🛡️ Sentinel-Scanner Autonomous Features Test")
    print("=" * 50)

    regulatory_working = test_regulatory_listener()
    telegram_configured = test_telegram_notifier()

    print("\n" + "=" * 50)
    print("📊 Test Results:")

    if regulatory_working:
        print("✅ Regulatory monitoring: WORKING")
    else:
        print("⚠️ Regulatory monitoring: No alerts found (may be normal)")

    if telegram_configured:
        print("✅ Telegram notifications: CONFIGURED")
    else:
        print("⚠️ Telegram notifications: NOT CONFIGURED")

    print("\n🚀 Ready for autonomous mode!")
    print("   Run './setup_autonomous.sh' to set up daily cron job")

if __name__ == "__main__":
    main()