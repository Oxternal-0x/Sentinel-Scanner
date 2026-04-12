from database import SentinelDB

if __name__ == "__main__":
    db = SentinelDB()
    print("\n🚩 TOP COMPLIANCE RISKS (Last 24h):")
    print("-" * 50)
    risks = db.get_history()
    for r in risks:
        print(f"[{r[3]}] {r[0]:<15} | Score: {r[1]} | Risk: {r[2]}")
