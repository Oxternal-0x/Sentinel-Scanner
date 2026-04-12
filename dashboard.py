import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List
from urllib.parse import urlparse

from database import SentinelDB
from event_router import EventDrivenSentinel

APP_NAME = os.getenv("FARCASTER_APP_NAME", "Sentinel Compliance AI")
APP_VERSION = os.getenv("FARCASTER_APP_VERSION", "1.0.0")
APP_DESCRIPTION = os.getenv(
    "FARCASTER_APP_DESCRIPTION",
    "Compliance heatmap and risk intelligence for DeFi protocols.",
)
HOME_URL = os.getenv("FARCASTER_HOME_URL", "https://yourdomain.com")
ICON_URL = os.getenv("FARCASTER_ICON_URL", f"{HOME_URL.rstrip('/')}/icon.svg")
SPLASH_IMAGE_URL = os.getenv("FARCASTER_SPLASH_IMAGE_URL", ICON_URL)
FRAME_IMAGE_URL = os.getenv("FARCASTER_FRAME_IMAGE_URL", ICON_URL)
PUBLIC_WEBHOOK_BASE_URL = os.getenv("PUBLIC_WEBHOOK_BASE_URL", "").rstrip("/")


SVG_ICON = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"512\" height=\"512\" viewBox=\"0 0 512 512\" fill=\"none\">
<defs>
  <linearGradient id=\"g\" x1=\"64\" y1=\"64\" x2=\"448\" y2=\"448\" gradientUnits=\"userSpaceOnUse\">
    <stop stop-color=\"#102542\"/>
    <stop offset=\"1\" stop-color=\"#2A9D8F\"/>
  </linearGradient>
</defs>
<rect x=\"36\" y=\"36\" width=\"440\" height=\"440\" rx=\"120\" fill=\"url(#g)\"/>
<path d=\"M256 112L352 152V228C352 303 313 368 256 400C199 368 160 303 160 228V152L256 112Z\" fill=\"#fffaf2\"/>
<path d=\"M222 248L246 272L292 226\" stroke=\"#2A9D8F\" stroke-width=\"22\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>
</svg>\n"""


def build_farcaster_manifest() -> Dict:
    return {
        "accountAssociation": {
            "header": os.getenv("FARCASTER_ACCOUNT_ASSOCIATION_HEADER", ""),
            "payload": os.getenv("FARCASTER_ACCOUNT_ASSOCIATION_PAYLOAD", ""),
            "signature": os.getenv("FARCASTER_ACCOUNT_ASSOCIATION_SIGNATURE", ""),
        },
        "miniapp": {
            "version": APP_VERSION,
            "name": APP_NAME,
            "homeUrl": HOME_URL,
            "iconUrl": ICON_URL,
            "splashImageUrl": SPLASH_IMAGE_URL,
            "splashBackgroundColor": "#f5efe5",
            "subtitle": "Autonomous DeFi Compliance",
            "description": APP_DESCRIPTION,
            "primaryCategory": "finance",
            "tags": ["compliance", "defi", "security", "audit"],
            "heroImageUrl": FRAME_IMAGE_URL,
        },
    }


def build_frame_meta() -> str:
    frame_payload = {
        "version": "next",
        "imageUrl": FRAME_IMAGE_URL,
        "button": {
            "title": "Launch Compliance AI",
            "action": {
                "type": "launch_frame",
                "name": APP_NAME,
                "url": HOME_URL,
            },
        },
    }
    return json.dumps(frame_payload, separators=(",", ":"))


def build_heatmap_html(entries: List[dict]) -> str:
    safe_data = json.dumps(entries)
    fc_frame_content = build_frame_meta()
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{APP_NAME}</title>
  <meta name=\"fc:frame\" content='{fc_frame_content}' />
  <style>
    :root {{
      --bg: #f5efe5;
      --ink: #102542;
      --low: #2a9d8f;
      --medium: #f4a261;
      --high: #d1495b;
      --card: #fffaf2;
      --btn: #102542;
      --btn-ink: #fffaf2;
    }}
    body {{ font-family: Georgia, serif; background: radial-gradient(circle at top, #fffaf2, var(--bg)); color: var(--ink); margin: 0; }}
    header {{ padding: 24px; }}
    h1 {{ margin: 0 0 8px; }}
    .wrap {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; padding: 0 24px 24px; }}
    .panel {{ background: var(--card); border-radius: 18px; padding: 18px; box-shadow: 0 12px 40px rgba(16,37,66,0.08); }}
    .bubbles {{ display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-end; min-height: 480px; }}
    .bubble {{
      border-radius: 999px; display: grid; place-items: center; color: white; text-align: center;
      padding: 12px; font-size: 12px; line-height: 1.2; box-shadow: inset 0 -10px 30px rgba(0,0,0,0.08);
    }}
    .low {{ background: var(--low); }}
    .medium {{ background: var(--medium); }}
    .high {{ background: var(--high); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    td, th {{ padding: 8px 0; border-bottom: 1px solid rgba(16,37,66,0.08); text-align: left; }}
    .actions {{ display: flex; align-items: center; gap: 10px; margin-top: 14px; }}
    button {{
      border: 0; border-radius: 999px; padding: 10px 16px; cursor: pointer;
      background: var(--btn); color: var(--btn-ink); font-weight: 600;
    }}
    #status {{ font-size: 13px; opacity: 0.8; }}
    @media (max-width: 900px) {{ .wrap {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Sentinel Ecosystem Heatmap</h1>
    <p>Investor-grade overview of the latest compliance posture across audited protocols.</p>
    <div class=\"actions\">
      <button id=\"signin\" type=\"button\">Sign In with Farcaster</button>
      <span id=\"status\">Waiting for Mini App SDK...</span>
    </div>
  </header>
  <div class=\"wrap\">
    <section class=\"panel\">
      <div class=\"bubbles\" id=\"bubbles\"></div>
    </section>
    <aside class=\"panel\">
      <table>
        <thead><tr><th>Protocol</th><th>Score</th><th>Risk</th></tr></thead>
        <tbody id=\"rows\"></tbody>
      </table>
    </aside>
  </div>

  <script type=\"module\">
    import {{ sdk }} from "https://esm.sh/@farcaster/miniapp-sdk";

    const entries = {safe_data};
    const bubbles = document.getElementById("bubbles");
    const rows = document.getElementById("rows");
    const status = document.getElementById("status");
    const signInButton = document.getElementById("signin");

    entries.forEach((entry) => {{
      const score = Number(entry.score || 0);
      const size = Math.max(72, Math.min(180, 70 + Math.sqrt(Number(entry.tvl || 0)) / 5000));
      const bubble = document.createElement("div");
      bubble.className = `bubble ${{(entry.risk_level || "low").toLowerCase()}}`;
      bubble.style.width = `${{size}}px`;
      bubble.style.height = `${{size}}px`;
      bubble.innerHTML = `<strong>${{entry.protocol}}</strong><br>Score ${{score}}`;
      bubbles.appendChild(bubble);

      const row = document.createElement("tr");
      row.innerHTML = `<td>${{entry.protocol}}</td><td>${{score}}</td><td>${{entry.risk_level}}</td>`;
      rows.appendChild(row);
    }});

    try {{
      await sdk.actions.ready();
      status.textContent = "Mini App ready in Farcaster client.";
    }} catch (error) {{
      status.textContent = "Running outside Farcaster client.";
      console.debug("Mini App ready() skipped", error);
    }}

    signInButton.addEventListener("click", async () => {{
      try {{
        const result = await sdk.actions.signIn();
        status.textContent = `Signed in as FID ${{result?.fid || "unknown"}}`;
      }} catch (error) {{
        status.textContent = "Farcaster sign-in unavailable in this context.";
        console.debug("Mini App signIn() failed", error);
      }}
    }});
  </script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    db = SentinelDB()
    events = EventDrivenSentinel()

    def _send_json(self, payload: Dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, payload: str, content_type: str = "text/plain; charset=utf-8", status: int = 200):
        body = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _is_authorized(headers) -> bool:
        shared_secret = os.getenv("WEBHOOK_SHARED_SECRET", "").strip()
        if not shared_secret:
            return True
        provided = headers.get("X-Sentinel-Webhook-Token", "").strip()
        return provided == shared_secret

    def _read_json_body(self) -> Dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _webhook_endpoints(base_url: str) -> Dict:
        if not base_url:
            return {
                "onchain": "/webhook/onchain-change",
                "farcaster": "/webhook/farcaster-news",
                "cryptopanic": "/webhook/cryptopanic-news",
                "watchlist": "/api/watchlist",
            }
        return {
            "onchain": f"{base_url}/webhook/onchain-change",
            "farcaster": f"{base_url}/webhook/farcaster-news",
            "cryptopanic": f"{base_url}/webhook/cryptopanic-news",
            "watchlist": f"{base_url}/api/watchlist",
        }

    @staticmethod
    def _security_status() -> Dict:
        secret = os.getenv("WEBHOOK_SHARED_SECRET", "").strip()
        has_secret = bool(secret)
        return {
            "header_name": "X-Sentinel-Webhook-Token",
            "has_shared_secret": has_secret,
            "shared_secret_length": len(secret) if has_secret else 0,
            "secret_strength": "strong" if len(secret) >= 24 else ("weak" if has_secret else "missing"),
        }

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ["/", "/index.html"]:
            body = build_heatmap_html(self.db.get_heatmap_data())
            self._send_text(body, "text/html; charset=utf-8")
            return

        if path == "/api/heatmap":
            self._send_json(self.db.get_heatmap_data())
            return

        if path == "/api/watchlist":
            targets = self.events.get_watchlist()
            self._send_json(
                {
                    "count": len(targets),
                    "targets": targets,
                }
            )
            return

        if path == "/api/webhook-config":
            self._send_json(
                {
                    "public_base_url": PUBLIC_WEBHOOK_BASE_URL or "not_set",
                    "endpoints": self._webhook_endpoints(PUBLIC_WEBHOOK_BASE_URL),
                    "security": self._security_status(),
                    "provider_mapping": {
                        "alchemy": "onchain",
                        "neynar": "farcaster",
                        "cryptopanic": "cryptopanic",
                    },
                    "recommended_keywords": ["exploit", "rug", "audit"],
                }
            )
            return

        if path == "/.well-known/farcaster.json":
            self._send_json(build_farcaster_manifest())
            return

        if path == "/icon.svg":
            self._send_text(SVG_ICON, "image/svg+xml; charset=utf-8")
            return

        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path

        if path not in {
            "/webhook/onchain-change",
            "/webhook/farcaster-news",
            "/webhook/cryptopanic-news",
        }:
            self.send_error(404)
            return

        if not self._is_authorized(self.headers):
            self._send_json({"error": "unauthorized"}, status=401)
            return

        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json({"error": "invalid_json"}, status=400)
            return

        if path == "/webhook/onchain-change":
            result = self.events.queue_onchain_event(payload)
            self._send_json(result, status=202 if result.get("status") == "queued" else 200)
            return

        if path == "/webhook/farcaster-news":
            result = self.events.queue_social_event(payload, source="farcaster")
            self._send_json(result, status=202 if result.get("status") == "queued" else 200)
            return

        if path == "/webhook/cryptopanic-news":
            result = self.events.queue_social_event(payload, source="cryptopanic")
            self._send_json(result, status=202 if result.get("status") == "queued" else 200)
            return


if __name__ == "__main__":
    host = os.getenv("SENTINEL_HOST", "127.0.0.1")
    port = int(os.getenv("SENTINEL_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Sentinel heatmap available at http://{host}:{port}")
    print(f"Farcaster manifest at http://{host}:{port}/.well-known/farcaster.json")
    print(f"Webhook endpoint (on-chain): http://{host}:{port}/webhook/onchain-change")
    print(f"Webhook endpoint (social): http://{host}:{port}/webhook/farcaster-news")
    server.serve_forever()
