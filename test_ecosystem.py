#!/usr/bin/env python
"""Test script for Sentinel Scanner ecosystem"""

print("🔍 Testing Sentinel Scanner Ecosystem...\n")

# Test imports with detailed error handling
try:
    import compliance_engine
    print(f"⚠️ compliance_engine loaded but dir = {dir(compliance_engine)}")
except Exception as e:
    print(f"❌ Error importing compliance_engine: {e}")
    import traceback
    traceback.print_exc()

try:
    from indexer import DeFiLlamaIndexer
    print("✅ DeFiLlama Indexer: Ready")
except Exception as e:
    print(f"⚠️ Indexer Error: {e}")

try:
    from etherscan import MultichainFetcher
    print("✅ Multichain Fetcher: Ready")
except Exception as e:
    print(f"⚠️ Etherscan Error: {e}")

print("\n📊 Pipeline Architecture:")
print("  1. Compliance Engine → Interprets regulations")
print("  2. DeFiLlama Indexer → Finds whale protocols")
print("  3. Multichain Fetcher → Downloads source code")
print("\n🚀 Sentinel Scanner modules loaded!")
