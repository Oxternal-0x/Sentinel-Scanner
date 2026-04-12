#!/usr/bin/env python3
"""
Minimal test to check if Sentinel-Scanner can initialize with current API keys.
"""

import os
import sys

def test_imports():
    """Test if all modules can be imported."""
    try:
        from compliance_engine import LegalInterpreter
        from indexer import DeFiLlamaIndexer
        from etherscan import MultichainFetcher
        from law_fetcher import RegulatoryListener
        from telegram_notifier import TelegramNotifier
        print("✅ All modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_initialization():
    """Test if core classes can be initialized."""
    try:
        from compliance_engine import LegalInterpreter
        from indexer import DeFiLlamaIndexer
        from etherscan import MultichainFetcher

        # Test LegalInterpreter (needs OpenAI key)
        interpreter = LegalInterpreter()
        if interpreter.client:
            print("✅ LegalInterpreter initialized (OpenAI connected)")
        else:
            print("⚠️ LegalInterpreter initialized but no OpenAI client")

        # Test DeFiLlamaIndexer (no API key needed)
        indexer = DeFiLlamaIndexer()
        print("✅ DeFiLlamaIndexer initialized")

        # Test MultichainFetcher (needs Etherscan key)
        fetcher = MultichainFetcher()
        print("✅ MultichainFetcher initialized")

        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

def main():
    print("🛡️ Sentinel-Scanner Initialization Test")
    print("=" * 40)

    imports_ok = test_imports()
    if not imports_ok:
        return

    init_ok = test_initialization()

    print("\n" + "=" * 40)
    if imports_ok and init_ok:
        print("🎉 Sentinel-Scanner is ready to run!")
        print("   Try: python3 main.py")
    else:
        print("⚠️ Some components failed - check API keys")

if __name__ == "__main__":
    main()