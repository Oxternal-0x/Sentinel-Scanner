#!/usr/bin/env python
"""Debug compliance engine loading"""
import traceback

print("Attempting to import compliance_engine...")
try:
    import compliance_engine
    print("Module loaded")
    print(f"Module contents: {dir(compliance_engine)}")
except Exception as e:
    print(f"Failed to import: {e}")
    traceback.print_exc()

print("\nAttempting to exec compliance_engine.py...")
try:
    exec(open('/Users/oxternal/Documents/Sentinel-Scanner/Sentinel-Scanner/compliance_engine.py').read())
    print("File executed successfully")
except Exception as e:
    print(f"Failed to exec: {e}")
    traceback.print_exc()
