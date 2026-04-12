import MiniAppDashboard from "@/components/miniapp-dashboard";
import type { HeatmapEntry } from "@/lib/types";

async function getHeatmapData(): Promise<HeatmapEntry[]> {
  const base = process.env.SENTINEL_API_BASE_URL || "http://127.0.0.1:8080";
  try {
    const response = await fetch(`${base.replace(/\/$/, "")}/api/heatmap`, { cache: "no-store" });
    if (!response.ok) return [];
    const data = (await response.json()) as HeatmapEntry[];
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const entries = await getHeatmapData();
  return <MiniAppDashboard initialEntries={entries} />;
}
