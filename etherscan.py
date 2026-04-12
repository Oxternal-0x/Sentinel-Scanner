import requests
import time
import os
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration constants
REQUEST_TIMEOUT = 10  # API request timeout in seconds
RATE_LIMIT_DELAY = 1  # Delay in seconds when rate limited
PROXY_FETCH_DELAY = 0.2  # Delay before fetching proxy implementation

class MultichainFetcher:
    """
    Multi-chain source code fetcher with proxy detection and rate limiting.
    Smart router that automatically switches API endpoints and keys based on chain.
    """

    def __init__(self):
        # Etherscan V2 uses a unified base URL with per-chain IDs.
        self.configs = {
            "ethereum": {"chainid": "1", "key": os.getenv("ETHERSCAN_API_KEY")},
            "polygon": {"chainid": "137", "key": os.getenv("POLYGONSCAN_API_KEY") or os.getenv("ETHERSCAN_API_KEY")},
            "arbitrum": {"chainid": "42161", "key": os.getenv("ARBISCAN_API_KEY") or os.getenv("ETHERSCAN_API_KEY")},
            "bsc": {"chainid": "56", "key": os.getenv("BSCSCAN_API_KEY") or os.getenv("ETHERSCAN_API_KEY")},
            "optimism": {"chainid": "10", "key": os.getenv("OPTIMISM_API_KEY") or os.getenv("ETHERSCAN_API_KEY")}
        }

    def _normalize_chain(self, chain: str) -> str:
        """Accept common chain-name variants from upstream sources."""
        normalized = (chain or "").strip().lower()
        aliases = {
            "binance smart chain": "bsc",
            "eth": "ethereum",
        }
        return aliases.get(normalized, normalized)

    def _call_api(self, params: Dict[str, str]) -> Dict:
        response = requests.get("https://api.etherscan.io/v2/api", params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def fetch_source(self, address: str, chain: str) -> str:
        """
        Smart router that detects chain and switches API endpoint/key automatically.
        """
        chain = self._normalize_chain(chain)
        config = self.configs.get(chain)
        if not config or not config['key']:
            return f"⚠️ Skip: Chain '{chain}' not configured or key missing."

        params = {
            "chainid": config["chainid"],
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": config['key']
        }

        try:
            data = self._call_api(params)

            if data.get("status") == "1":
                result = data["result"][0]
                source = result.get("SourceCode", "")
                
                # Proxy Logic: If it's a proxy, we need the actual implementation
                if result.get("Proxy") == "1" and result.get("Implementation"):
                    impl = result["Implementation"]
                    logger.debug(f"  ↳ Proxy found. Routing to Implementation: {impl}")
                    time.sleep(PROXY_FETCH_DELAY)  # Free-tier breathing room
                    return self.fetch_source(impl, chain)
                
                return source
            return f"❌ API Error: {data.get('result', 'Unknown')}"
        except Exception as e:
            return f"❌ Fetcher crashed: {str(e)}"

    def get_source_code(self, address: str, chain: str = "ethereum") -> Optional[dict]:
        """
        Enhanced version returning full contract data dictionary.
        Makes direct API call to get complete contract information.
        """
        chain = self._normalize_chain(chain)
        config = self.configs.get(chain)
        if not config or not config['key']:
            return None

        params = {
            "chainid": config["chainid"],
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": config['key']
        }

        try:
            data = self._call_api(params)

            if data.get("status") == "1" and data.get("result"):
                result = data["result"][0]

                # Handle proxy contracts
                if result.get("Proxy") == "1" and result.get("Implementation"):
                    impl = result["Implementation"]
                    logger.debug(f"  ↳ Proxy found. Routing to Implementation: {impl}")
                    time.sleep(PROXY_FETCH_DELAY)  # Free-tier breathing room
                    # Recursively get implementation contract data
                    return self.get_source_code(impl, chain)

                return {
                    "address": address,
                    "chain": chain,
                    "source_code": result.get("SourceCode", ""),
                    "contract_name": result.get("ContractName", "Unknown"),
                    "compiler_version": result.get("CompilerVersion", "Unknown"),
                    "optimization_used": result.get("OptimizationUsed", "Unknown"),
                    "runs": result.get("Runs", "Unknown"),
                    "abi": result.get("ABI", ""),
                    "constructor_args": result.get("ConstructorArguments", ""),
                    "is_proxy": result.get("Proxy") == "1",
                    "implementation_address": result.get("Implementation"),
                }
            else:
                logger.warning(f"API returned error: {data.get('result', 'Unknown error')}")
                return None

        except Exception as e:
            logger.error(f"Error fetching contract data: {e}")
            return None

    def get_bytecode(self, address: str, chain: str = "ethereum") -> Optional[dict]:
        """Fetches deployed runtime bytecode for contracts without verified source."""
        chain = self._normalize_chain(chain)
        config = self.configs.get(chain)
        if not config or not config["key"]:
            return None

        params = {
            "chainid": config["chainid"],
            "module": "proxy",
            "action": "eth_getCode",
            "address": address,
            "tag": "latest",
            "apikey": config["key"],
        }

        try:
            data = self._call_api(params)
            bytecode = data.get("result")
            if not bytecode or bytecode == "0x":
                return None

            return {
                "address": address,
                "chain": chain,
                "bytecode": bytecode,
                "bytecode_size": max((len(bytecode) - 2) // 2, 0),
                "source_code": "",
                "contract_name": "UnverifiedContract",
                "compiler_version": "Unknown",
                "is_proxy": False,
                "verification_status": "unverified_bytecode",
            }
        except Exception as e:
            logger.error(f"Error fetching bytecode: {e}")
            return None

    def get_contract_artifact(self, address: str, chain: str = "ethereum") -> Optional[dict]:
        """Returns either verified source or a bytecode fallback artifact."""
        source_artifact = self.get_source_code(address, chain)
        if source_artifact:
            source_artifact["verification_status"] = (
                "verified_source" if source_artifact.get("source_code") else "unverified_source"
            )
            return source_artifact

        return self.get_bytecode(address, chain)

# --- Quick Test ---
if __name__ == "__main__":
    try:
        fetcher = MultichainFetcher()
        # Testing with WETH on Ethereum (often more reliable than USDT for a first test)
        result = fetcher.fetch_source("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "Ethereum")
        print("✅ API Test Result:")
        print(result[:500] + "..." if len(result) > 500 else result)
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Make sure ETHERSCAN_API_KEY is set in your .env file")
