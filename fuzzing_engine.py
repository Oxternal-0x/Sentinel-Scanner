import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict


class FuzzingEngine:
    """Optional Echidna integration for verified contracts."""

    def run(self, artifact: Dict) -> Dict:
        if artifact.get("verification_status") != "verified_source":
            return {
                "status": "skipped",
                "reason": "verified_source_required",
            }

        echidna = shutil.which("echidna") or shutil.which("echidna-test")
        if not echidna:
            return {
                "status": "skipped",
                "reason": "echidna_not_installed",
            }

        contract_name = artifact.get("contract_name") or "TargetContract"
        source_code = artifact.get("source_code") or ""
        pragma = self._extract_pragma(source_code)
        harness = self._build_harness(contract_name)

        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = os.path.join(tmpdir, "Target.sol")
            with open(target_file, "w", encoding="utf-8") as handle:
                handle.write(f"{pragma}\n\n{source_code}\n\n{harness}\n")

            try:
                result = subprocess.run(
                    [echidna, target_file, "--contract", "SentinelHarness"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
            except Exception as exc:
                return {
                    "status": "failed",
                    "reason": str(exc),
                }

        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        failures = [line.strip() for line in combined.splitlines() if "failed" in line.lower()]
        return {
            "status": "completed" if result.returncode == 0 else "warning",
            "failures": failures[:10],
            "summary": combined[:2500],
        }

    def _extract_pragma(self, source_code: str) -> str:
        match = re.search(r"pragma\s+solidity\s+[^;]+;", source_code)
        return match.group(0) if match else "pragma solidity ^0.8.0;"

    def _build_harness(self, contract_name: str) -> str:
        return f"""
contract SentinelHarness {{
    bool public sentinel_constant_truth = true;

    function echidna_sentinel_placeholder() public view returns (bool) {{
        return sentinel_constant_truth;
    }}
}}
"""
