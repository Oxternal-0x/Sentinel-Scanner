import requests
from typing import List, Dict, Optional
import logging

# Configuration constants
REQUEST_TIMEOUT = 15  # API request timeout in seconds

logger = logging.getLogger(__name__)

class DeFiLlamaIndexer:
    """
    Connects to DeFiLlama's open API to identify high-value 
    smart contract targets across all chains.
    
    Features:
    - Robust type checking for TVL values
    - Handles None/null values from API responses
    - Safe field access to prevent KeyError exceptions
    - Request timeout to recover from network hangs
    """
    def __init__(self):
        self.base_url = "https://api.llama.fi/protocols"

    def get_top_percentile_targets(self, percentile: float = 0.10, require_address: bool = False) -> List[Dict]:
        """
        Fetches all protocols and returns the top X% (default 10%) by TVL.
        Statistically adaptive targeting that scales with market conditions.
        
        Args:
            percentile: Fraction of top protocols to target (0.10 = top 10%)
            
        Returns:
            List of top percentile protocol dictionaries, sorted by TVL descending
        """
        logger.info("📡 Requesting global protocol list...")
        try:
            response = requests.get(self.base_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                logger.warning("⚠️ Unexpected API format: Expected a list of protocols.")
                return []

            # 1. Clean and Sort the data by TVL (Highest to Lowest)
            valid_protocols = []
            for p in data:
                try:
                    tvl = float(p.get("tvl", 0))
                    if tvl > 0:  # Filter out dead/empty contracts
                        if require_address and not p.get("address"):
                            continue
                        valid_protocols.append(p)
                except (ValueError, TypeError):
                    continue

            valid_protocols.sort(key=lambda x: x["tvl"], reverse=True)

            # 2. Calculate the "Top X%" Cutoff
            total_count = len(valid_protocols)
            cutoff_index = max(1, int(total_count * percentile))
            
            whales = valid_protocols[:cutoff_index]

            logger.info(f"📊 Market Stats:")
            logger.info(f"   - Total Protocols Found: {total_count}")
            logger.info(f"   - Sentinel Target Group (Top {int(percentile*100)}%): {len(whales)} protocols")
            if whales:
                logger.info(f"   - Lower Bound TVL in Group: ${whales[-1]['tvl']:,.2f}")

            return [
                {
                    "name": p.get("name", "Unknown"),
                    "tvl": p.get("tvl", 0),
                    "chain": p.get("chain", "ethereum"),  # Default to ethereum for multi-chain
                    "address": p.get("address"),
                    "category": p.get("category", "Unknown"),
                    "slug": p.get("slug", "")
                } for p in whales
            ]

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API Connectivity Error: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Indexer Error: {e}")
            return []


# --- Diagnostic Check for your Mac Terminal ---
if __name__ == "__main__":
    indexer = DeFiLlamaIndexer()
    # Test with top 10% targeting
    test_results = indexer.get_top_percentile_targets(0.10) 
    if test_results:
        print(f"\n🎯 Top Target: {test_results[0]['name']} with ${test_results[0]['tvl']:,.2f}")
        print(f"Chain: {test_results[0]['chain']}")
        print(f"Total targets in top 10%: {len(test_results)}")
    else:
        print("\n⚠️ No protocols found - check API connectivity")
