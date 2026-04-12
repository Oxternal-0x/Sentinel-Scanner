import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from typing import Dict, List


KNOWN_SELECTORS = {
    "a9059cbb": "transfer(address,uint256)",
    "095ea7b3": "approve(address,uint256)",
    "23b872dd": "transferFrom(address,address,uint256)",
    "40c10f19": "mint(address,uint256)",
    "42966c68": "burn(uint256)",
    "8456cb59": "pause()",
    "3f4ba83a": "unpause()",
}


class BytecodeAnalyzer:
    """Falls back to bytecode-level heuristics and optional decompilation."""

    def analyze(self, artifact: Dict) -> Dict:
        bytecode = artifact.get("bytecode", "")
        if not bytecode:
            return {
                "status": "no_bytecode",
                "tool": "none",
                "summary": "No bytecode available for analysis.",
                "selectors": [],
                "risk_flags": ["missing_source_artifact"],
            }

        selectors = self._extract_selectors(bytecode)
        decompilation = self._run_panoramix(bytecode)
        risk_flags = ["unverified_contract", "bytecode_only_review"]
        if not selectors:
            risk_flags.append("opaque_bytecode_surface")

        return {
            "status": "analyzed",
            "tool": decompilation["tool"],
            "summary": decompilation["summary"],
            "selectors": selectors,
            "risk_flags": risk_flags,
            "fingerprint": hashlib.sha256(bytecode.encode("utf-8")).hexdigest()[:16],
            "decompiled_text": decompilation.get("decompiled_text", ""),
        }

    def _extract_selectors(self, bytecode: str) -> List[str]:
        body = (bytecode or "").lower().replace("0x", "")
        matches = [signature for selector, signature in KNOWN_SELECTORS.items() if selector in body]
        return sorted(set(matches))

    def _run_panoramix(self, bytecode: str) -> Dict:
        panoramix = shutil.which("panoramix")
        if not panoramix:
            return {
                "tool": "heuristic-fallback",
                "summary": "Panoramix not installed; using bytecode heuristics and selector analysis only.",
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            bytecode_path = os.path.join(tmpdir, "contract.evm")
            with open(bytecode_path, "w", encoding="utf-8") as handle:
                handle.write(bytecode)

            try:
                result = subprocess.run(
                    [panoramix, bytecode_path],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
            except Exception as exc:
                return {
                    "tool": "panoramix",
                    "summary": f"Panoramix invocation failed: {exc}",
                }

            output = (result.stdout or result.stderr).strip()
            return {
                "tool": "panoramix",
                "summary": "Panoramix decompilation completed." if output else "Panoramix returned no output.",
                "decompiled_text": output[:4000],
            }

    def persist_analysis(self, protocol_name: str, analysis: Dict) -> str:
        os.makedirs("artifacts/bytecode", exist_ok=True)
        filename = f"artifacts/bytecode/{protocol_name.replace(' ', '_')}.json"
        with open(filename, "w", encoding="utf-8") as handle:
            json.dump(analysis, handle, indent=2)
        return filename
