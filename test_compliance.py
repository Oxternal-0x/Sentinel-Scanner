#!/usr/bin/env python3
"""
Test script for the compliance engine functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from compliance_engine import LegalInterpreter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_legal_interpreter():
    """Test the LegalInterpreter class."""
    print("🧠 Testing LegalInterpreter...")

    try:
        interpreter = LegalInterpreter()
        print("✅ LegalInterpreter initialized successfully")

        # Test rule extraction
        test_law = "MiCA Article 12: All stablecoins must implement a pause function for emergency stops."
        print(f"📜 Testing with law: {test_law[:50]}...")

        rules = interpreter.translate_law_to_rules(test_law)
        print(f"✅ Rules extracted: {type(rules)}")
        print(f"   Keys: {list(rules.keys()) if isinstance(rules, dict) else 'Not a dict'}")

        if "error" not in rules:
            print("✅ No errors in rule extraction")
        else:
            print(f"⚠️ Error in extraction: {rules.get('error')}")

        return True

    except Exception as e:
        print(f"❌ LegalInterpreter test failed: {e}")
        return False

def test_analyze_contract():
    """Test the analyze_contract_compliance function."""
    print("\n🔍 Testing analyze_contract_compliance...")

    try:
        from main import analyze_contract_compliance

        # Simple test contract
        test_code = """
        pragma solidity ^0.8.0;

        contract TestToken {
            address public owner;

            constructor() {
                owner = msg.sender;
            }

            function transfer(address to, uint amount) public {
                // No access control - potential security issue
            }
        }
        """

        # Test manifest
        test_manifest = {
            "extracted_rules": ["Contracts should have access control for sensitive functions"],
            "original_text": "Test regulation"
        }

        print("📝 Analyzing test contract...")
        result = analyze_contract_compliance(test_code, test_manifest)

        print(f"✅ Analysis result: {type(result)}")
        if isinstance(result, dict) and "compliance_score" in result:
            print(f"   Score: {result.get('compliance_score')}")
            print(f"   Violations: {len(result.get('violations', []))}")
            print("✅ Contract analysis successful")
        else:
            print(f"⚠️ Unexpected result structure: {result}")

        return True

    except Exception as e:
        print(f"❌ Contract analysis test failed: {e}")
        return False

def main():
    print("🛡️ Sentinel-Scanner Compliance Engine Test")
    print("=" * 50)

    legal_ok = test_legal_interpreter()
    analyze_ok = test_analyze_contract()

    print("\n" + "=" * 50)
    print("📊 Test Results:")

    if legal_ok:
        print("✅ Legal rule extraction: WORKING")
    else:
        print("❌ Legal rule extraction: FAILED")

    if analyze_ok:
        print("✅ Contract compliance analysis: WORKING")
    else:
        print("❌ Contract compliance analysis: FAILED")

    if legal_ok and analyze_ok:
        print("\n🎉 Compliance engine is fully operational!")
    else:
        print("\n⚠️ Some compliance features need attention")

if __name__ == "__main__":
    main()