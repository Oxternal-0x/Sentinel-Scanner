"use client";

import { sdk } from "@farcaster/miniapp-sdk";
import { useEffect, useMemo, useState } from "react";
import { keccak256, parseAbi, toHex } from "viem";
import {
  useAccount,
  useConnect,
  useDisconnect,
  useWaitForTransactionReceipt,
  useWriteContract
} from "wagmi";

import type { HeatmapEntry } from "@/lib/types";

type Props = {
  initialEntries: HeatmapEntry[];
};

const wrapperAbi = parseAbi(["function submitRegulatoryHash(bytes32 policyHash) external"]);
const wrapperAddress = process.env.NEXT_PUBLIC_REG_WRAPPER_ADDRESS;

function normalizeRiskClass(riskLevel: string): string {
  const normalized = (riskLevel || "low").toLowerCase();
  if (normalized === "high") return "bg-high";
  if (normalized === "medium") return "bg-medium";
  return "bg-low";
}

export default function MiniAppDashboard({ initialEntries }: Props) {
  const [entries, setEntries] = useState<HeatmapEntry[]>(initialEntries);
  const [status, setStatus] = useState("Loading Farcaster context...");
  const [policyText, setPolicyText] = useState("");
  const [lastPolicyHash, setLastPolicyHash] = useState("");
  const { address, chainId, isConnected } = useAccount();
  const { connect, connectors, isPending: isConnectPending } = useConnect();
  const { disconnect } = useDisconnect();
  const { data: txHash, isPending: isWritePending, writeContract } = useWriteContract();
  const { isLoading: isConfirming, isSuccess: isConfirmed } = useWaitForTransactionReceipt({
    hash: txHash
  });
  const isWrapperAddressValid = /^0x[a-fA-F0-9]{40}$/.test(wrapperAddress || "");

  useEffect(() => {
    async function bootstrapMiniApp() {
      try {
        await sdk.actions.ready();
        setStatus("Mini App ready in Farcaster client.");
      } catch {
        setStatus("Running in browser mode (outside Farcaster client).");
      }
    }

    bootstrapMiniApp();
  }, []);

  useEffect(() => {
    async function refreshEntries() {
      try {
        const response = await fetch("/api/heatmap", { cache: "no-store" });
        if (!response.ok) return;

        const data = (await response.json()) as HeatmapEntry[];
        if (Array.isArray(data)) {
          setEntries(data);
        }
      } catch {
        // Intentionally noop so the app still works with server-side data.
      }
    }

    refreshEntries();

    const refreshMs = Math.max(5000, Number(process.env.NEXT_PUBLIC_HEATMAP_REFRESH_MS || 30000));
    const timer = setInterval(refreshEntries, refreshMs);
    return () => clearInterval(timer);
  }, []);

  const sortedEntries = useMemo(
    () => [...entries].sort((a, b) => Number(b.score || 0) - Number(a.score || 0)),
    [entries]
  );

  async function signIn() {
    try {
      const result = await sdk.actions.signIn();
      const fid = (result as { fid?: number } | null)?.fid;
      setStatus(fid ? `Signed in as FID ${fid}.` : "Signed in with Farcaster.");
    } catch {
      setStatus("Farcaster sign-in is unavailable in this context.");
    }
  }

  function connectWallet() {
    const connector = connectors[0];
    if (!connector) {
      setStatus("No wallet connector available in this client.");
      return;
    }
    connect({ connector });
  }

  function submitPolicyHash() {
    const normalized = policyText.trim();
    if (!normalized) {
      setStatus("Add policy text before submitting on-chain.");
      return;
    }
    if (!isWrapperAddressValid) {
      setStatus("Set NEXT_PUBLIC_REG_WRAPPER_ADDRESS to your deployed wrapper contract.");
      return;
    }
    const policyHash = keccak256(toHex(normalized));
    setLastPolicyHash(policyHash);
    writeContract({
      address: wrapperAddress as `0x${string}`,
      abi: wrapperAbi,
      functionName: "submitRegulatoryHash",
      args: [policyHash]
    });
  }

  return (
    <main className="mx-auto max-w-6xl px-5 pb-8 pt-7 md:px-8">
      <header className="mb-5 rounded-3xl bg-paper p-5 shadow-[0_12px_40px_rgba(16,37,66,0.08)]">
        <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">Sentinel Ecosystem Heatmap</h1>
        <p className="mt-2 text-sm opacity-80 md:text-base">
          Investor-grade overview of the latest compliance posture across audited protocols.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:opacity-90"
            onClick={signIn}
            type="button"
          >
            Sign In with Farcaster
          </button>
          <span className="text-sm opacity-80">{status}</span>
        </div>
      </header>

      <section className="mb-5 rounded-3xl bg-paper p-5 shadow-[0_12px_40px_rgba(16,37,66,0.08)]">
        <h2 className="text-lg font-semibold">Wallet + Regulatory Wrapper</h2>
        <p className="mt-2 text-sm opacity-80">
          Connect Warpcast wallet and submit a policy hash on-chain via
          <code className="ml-1 rounded bg-ink/5 px-1 py-0.5">submitRegulatoryHash(bytes32)</code>.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          {!isConnected ? (
            <button
              className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:opacity-90 disabled:opacity-60"
              disabled={isConnectPending}
              onClick={connectWallet}
              type="button"
            >
              {isConnectPending ? "Connecting..." : "Connect Wallet"}
            </button>
          ) : (
            <button
              className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:opacity-90"
              onClick={() => disconnect()}
              type="button"
            >
              Disconnect Wallet
            </button>
          )}
          <span className="text-sm opacity-80">
            {isConnected ? `Connected: ${address || "unknown"} (chain ${chainId || "n/a"})` : "Wallet not connected"}
          </span>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
          <textarea
            className="min-h-28 rounded-2xl border border-ink/15 bg-white p-3 text-sm outline-none ring-0 focus:border-ink/40"
            onChange={(event) => setPolicyText(event.target.value)}
            placeholder="Paste policy text to hash and register on-chain..."
            value={policyText}
          />
          <button
            className="h-fit rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:opacity-90 disabled:opacity-60"
            disabled={!isConnected || !isWrapperAddressValid || isWritePending || isConfirming}
            onClick={submitPolicyHash}
            type="button"
          >
            {isWritePending || isConfirming ? "Submitting..." : "Submit Policy Hash"}
          </button>
        </div>
        <div className="mt-3 text-sm opacity-80">
          <p>
            Wrapper:
            <code className="ml-1 rounded bg-ink/5 px-1 py-0.5">
              {isWrapperAddressValid ? wrapperAddress : "Set NEXT_PUBLIC_REG_WRAPPER_ADDRESS"}
            </code>
          </p>
          {lastPolicyHash ? (
            <p>
              Last hash:
              <code className="ml-1 break-all rounded bg-ink/5 px-1 py-0.5">{lastPolicyHash}</code>
            </p>
          ) : null}
          {txHash ? (
            <p>
              Tx:
              <a
                className="ml-1 underline"
                href={`https://basescan.org/tx/${txHash}`}
                rel="noreferrer"
                target="_blank"
              >
                {txHash}
              </a>
            </p>
          ) : null}
          {isConfirmed ? <p>Transaction confirmed.</p> : null}
        </div>
      </section>

      <section className="grid gap-5 md:grid-cols-[2fr_1fr]">
        <div className="rounded-3xl bg-paper p-5 shadow-[0_12px_40px_rgba(16,37,66,0.08)]">
          <div className="flex min-h-[380px] flex-wrap items-end gap-3">
            {sortedEntries.map((entry) => {
              const score = Number(entry.score || 0);
              const size = Math.max(72, Math.min(180, 70 + Math.sqrt(Number(entry.tvl || 0)) / 5000));
              return (
                <article
                  className={`grid place-items-center rounded-full p-3 text-center text-xs leading-5 text-white shadow-[inset_0_-10px_30px_rgba(0,0,0,0.08)] ${normalizeRiskClass(
                    entry.risk_level
                  )}`}
                  key={entry.protocol}
                  style={{ height: `${size}px`, width: `${size}px` }}
                >
                  <strong>{entry.protocol}</strong>
                  <span>Score {score}</span>
                </article>
              );
            })}
          </div>
        </div>

        <aside className="rounded-3xl bg-paper p-5 shadow-[0_12px_40px_rgba(16,37,66,0.08)]">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="border-b border-ink/10 py-2 text-left">Protocol</th>
                <th className="border-b border-ink/10 py-2 text-left">Score</th>
                <th className="border-b border-ink/10 py-2 text-left">Risk</th>
              </tr>
            </thead>
            <tbody>
              {sortedEntries.map((entry) => (
                <tr key={`${entry.protocol}-row`}>
                  <td className="border-b border-ink/10 py-2">{entry.protocol}</td>
                  <td className="border-b border-ink/10 py-2">{Number(entry.score || 0)}</td>
                  <td className="border-b border-ink/10 py-2">{entry.risk_level}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </aside>
      </section>
    </main>
  );
}
