# Sentinel Mini App (Farcaster)

This is a Next.js Farcaster Mini App frontend for Sentinel Scanner.

## Run locally

1. Install dependencies:
```bash
cd miniapp
npm install
```

2. Configure env:
```bash
cp .env.example .env.local
```

3. Start Sentinel backend in another terminal:
```bash
python3 dashboard.py
```

4. Start Mini App:
```bash
npm run dev
```

## Endpoints

- Mini App page: `http://localhost:3000`
- Mini App manifest: `http://localhost:3000/.well-known/farcaster.json`
- Backend heatmap API: `http://127.0.0.1:8080/api/heatmap`

## Notes

- `sdk.actions.ready()` runs on load to hide Farcaster splash screens.
- `sdk.actions.signIn()` is wired to the sign-in button.
- `fc:frame` metadata is emitted in `app/head.tsx`.
- Wagmi + Viem are wired with the Farcaster Mini App connector.
- Set `NEXT_PUBLIC_REG_WRAPPER_ADDRESS` to enable on-chain wrapper writes.
