import json
import logging
import os
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


class MempoolMonitor:
    """Optional shadow mempool monitor via JSON-RPC pending transaction filters."""

    def __init__(self):
        self.rpc_url = os.getenv("ETH_RPC_URL")

    def scan_pending_risks(self, watched_addresses: List[str]) -> List[Dict]:
        if not self.rpc_url or not watched_addresses:
            return []

        try:
            filter_id = self._rpc("eth_newPendingTransactionFilter", [])
            tx_hashes = self._rpc("eth_getFilterChanges", [filter_id]) or []
        except Exception as exc:
            logger.warning("Mempool monitor unavailable: %s", exc)
            return []

        findings = []
        watched = {address.lower() for address in watched_addresses if address}
        for tx_hash in tx_hashes[:25]:
            tx = self._rpc("eth_getTransactionByHash", [tx_hash])
            if not tx:
                continue
            destination = (tx.get("to") or "").lower()
            if destination not in watched:
                continue

            findings.append(
                {
                    "tx_hash": tx_hash,
                    "to": tx.get("to"),
                    "from": tx.get("from"),
                    "value": int(tx.get("value", "0x0"), 16),
                    "risk": "watched_contract_pending_call",
                }
            )
        return findings

    def _rpc(self, method: str, params: List[object]):
        response = requests.post(
            self.rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(json.dumps(payload["error"]))
        return payload.get("result")
