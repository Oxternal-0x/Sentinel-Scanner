# 🛡️ Sentinel-Scanner: Autonomous DeFi Compliance AI

**Sentinel-Scanner** is the world’s first autonomous smart contract auditor designed to bridge the gap between rapidly evolving global regulations and on-chain reality.

## ⚡ Core Capabilities
* **📰 Autonomous Regulatory Intake:** Monitors SEC, CFTC, and ESMA RSS feeds for new regulations and automatically updates compliance rules.
* **📱 Real-time Notifications:** Telegram alerts when new regulations are detected or audit cycles complete.
* **⚖️ Self-Evolving Logic:** Automatically parses new regulatory filings (RSS/PDF) into Solidity-specific compliance rules using configurable OpenAI-compatible models (OpenAI or Ollama).
* **🎯 Adaptive Targeting:** Dynamically targets the top 10% of DeFi protocols by TVL, scaling automatically with market growth.
* **🔍 Multichain Forensics:** Automated source code extraction from Ethereum, Polygon, Arbitrum, BSC, and Optimism.
* **🤖 Semantic Auditing:** Moves beyond regex to understand the "Intent" of the code relative to jurisdictional law.
* **🔄 Proxy Detection:** Automatically resolves proxy contracts to audit implementation logic.
* **💾 Audit Trail:** JSON persistence of all compliance verdicts for regulatory reporting and historical analysis.

## 🛠️ Architecture
- `compliance_engine.py`: The LLM-driven "Brain" that interprets law.
- `indexer.py`: The "Radar" that identifies systemic risk targets using percentile-based selection.
- `etherscan.py`: The "MultichainFetcher" that retrieves live contract data across 5+ blockchains.
- `law_fetcher.py`: The "Regulatory Listener" that monitors global regulatory feeds.
- `telegram_notifier.py`: The "Alert System" for real-time notifications.
- `main.py`: The "Orchestrator" managing the end-to-end autonomous pipeline.

## 🎯 Product Moat
Unlike static auditors (CertiK, Hacken) that provide a "point-in-time" PDF, Sentinel is a living security layer. It uses LLMs to translate real-time regulatory shifts (SEC/MiCA) into executable scans, ensuring compliance 24/7, not just at launch. The adaptive percentile targeting ensures it always audits the "economic core" regardless of market size.

## 💡 Compliance Value Proposition
We reduce "Regulatory Lag." When a new law drops, Sentinel identifies non-compliant protocols across a $100B+ ecosystem in minutes, not months.

## 🚀 Go-To-Market Strategy
Target:
- DeFi Risk teams
- Institutional LPs
- Regulated asset managers

Sell a subscription for **continuous compliance insurance**, not a one-time audit engagement.

## 🚀 Quick Start (Mac mini / Unix)
1. Clone & install:
```bash
git clone https://github.com/Oxternal-0x/Sentinel-Scanner.git
cd Sentinel-Scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure env:
```bash
cat > .env <<'EOF'
OPENAI_API_KEY=<your_key>
OPENAI_MODEL=gpt-4o
ETHERSCAN_API_KEY=<your_key>
POLYGONSCAN_API_KEY=<your_key>
ARBISCAN_API_KEY=<your_key>
OPTIMISM_API_KEY=<your_key>
BSCSCAN_API_KEY=<your_key>

# Optional: Telegram notifications
TELEGRAM_BOT_TOKEN=<your_bot_token>
TELEGRAM_CHAT_ID=<your_chat_id>
EOF
```

### Optional: Use Local Ollama Instead of Hosted OpenAI
For local reasoning models (for example `deepseek-r1:7b` or `llama3.2:3b`), run Ollama with CORS origins:

```bash
OLLAMA_ORIGINS="https://yourdomain.com,app://farcaster" ollama serve
```

Then set:

```bash
DEEPSEEK_BASE_URL=http://127.0.0.1:11434/v1
DEEPSEEK_API_KEY=ollama
DEEPSEEK_MODEL=deepseek-r1:7b
COMPLIANCE_MODEL=deepseek-r1:7b
```

If you need remote access from Warpcast/public clients, tunnel Ollama:

```bash
ngrok http 11434
```

And point `DEEPSEEK_BASE_URL` to your generated `https://<id>.ngrok-free.app/v1`.

3. Test manually:
```bash
python3 main.py
```

4. Test autonomous features:
```bash
python3 test_autonomous.py
```

5. Set up autonomous mode (runs daily at 9 AM):
```bash
# Run the setup script
./setup_autonomous.sh

# Or manually edit crontab:
crontab -e
# Add: 0 9 * * * /usr/bin/python3 /Users/yourname/Sentinel-Scanner/main.py
```

6. Set up Telegram notifications (optional):
   - Create bot: Message [@BotFather](https://t.me/botfather) on Telegram
   - Get chat ID: Message your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Add tokens to `.env` above

## Event-Driven Mode (Webhooks + Watchers)
Sentinel can run in webhook-driven mode so audits only trigger when events happen.

1. Start server:
```bash
python3 dashboard.py
```

2. Configure watcher scope in `.env`:
- `WATCHLIST_PERCENTILE=0.10`
- `WATCHLIST_MAX_TARGETS=25`
- `WEBHOOK_MIN_REAUDIT_SECONDS=300`

3. Protect endpoints (recommended):
- Set `WEBHOOK_SHARED_SECRET=...`
- Send it as `X-Sentinel-Webhook-Token` from webhook providers

4. Webhook endpoints:
- `POST /webhook/onchain-change` (Alchemy/QuickNode contract activity)
- `POST /webhook/farcaster-news` (Neynar/Farcaster casts)
- `POST /webhook/cryptopanic-news` (news triggers)
- `GET /api/watchlist` (current watched protocols + addresses)
- `GET /api/webhook-config` (provider mapping + security readiness)

5. Example test calls:
```bash
curl -X POST http://127.0.0.1:8080/webhook/onchain-change \
  -H "Content-Type: application/json" \
  -d '{"event":{"address":"0x0000000000000000000000000000000000000000"}}'
```

```bash
curl -X POST http://127.0.0.1:8080/webhook/farcaster-news \
  -H "Content-Type: application/json" \
  -d '{"cast":{"text":"Potential exploit discussion around Aave and Lido"}}'
```

6. Handshake checklist for tunnel deployment:
- Set `PUBLIC_WEBHOOK_BASE_URL=https://your-tunnel.com`
- Check config:
```bash
curl https://your-tunnel.com/api/webhook-config
```
- Register providers:
  - Alchemy -> `https://your-tunnel.com/webhook/onchain-change`
  - Neynar -> `https://your-tunnel.com/webhook/farcaster-news`
  - CryptoPanic -> `https://your-tunnel.com/webhook/cryptopanic-news`
- Use keyword triggers on Neynar: `exploit`, `rug`, `audit`
- If using auth, include `X-Sentinel-Webhook-Token: <WEBHOOK_SHARED_SECRET>` in provider webhook headers

## 📌 Built by Oxternal.0x
A life-long learner, builder, and explorer.

## Mini App (Farcaster) Setup
Sentinel's dashboard now supports Farcaster Mini App primitives directly from `dashboard.py`.

1. Run the dashboard server:
```bash
python3 dashboard.py
```

2. Expose it on your public domain and set `.env` values:
- `FARCASTER_HOME_URL`
- `FARCASTER_ICON_URL`
- `FARCASTER_FRAME_IMAGE_URL`

3. Confirm manifest endpoint:
- `https://yourdomain.com/.well-known/farcaster.json`

4. Claim domain ownership in Warpcast:
- Warpcast mobile -> `Settings` -> `Developer` -> `Domains`
- Then fill:
  - `FARCASTER_ACCOUNT_ASSOCIATION_HEADER`
  - `FARCASTER_ACCOUNT_ASSOCIATION_PAYLOAD`
  - `FARCASTER_ACCOUNT_ASSOCIATION_SIGNATURE`

5. Shareability:
- The dashboard HTML includes `fc:frame` metadata with `launch_frame` so casts can launch the app.

6. Identity:
- The page calls `sdk.actions.ready()` after load and supports `sdk.actions.signIn()` for Farcaster-authenticated identity.

### React / Next.js Alternative
If you move to React/Next, install the same SDK in that app:
```bash
npm install @farcaster/miniapp-sdk
```
And call:
```ts
import { sdk } from "@farcaster/miniapp-sdk";
await sdk.actions.ready();
```

### Included Next.js Mini App
This repo now includes a starter frontend in `miniapp/` with:
- `sdk.actions.ready()` + `sdk.actions.signIn()` wiring
- `fc:frame` metadata in `app/head.tsx`
- `/.well-known/farcaster.json` route
- Proxy endpoint at `/api/heatmap` for Sentinel backend data

Run it with:
```bash
cd miniapp
npm install
cp .env.example .env.local
npm run dev
```

---

## 📈 Optional Next Step: Mermaid Architecture Diagram
Would you like me to write a `diagram.mermaid` file that you can paste into your README to show investors a beautiful flowchart of the AI pipeline?
