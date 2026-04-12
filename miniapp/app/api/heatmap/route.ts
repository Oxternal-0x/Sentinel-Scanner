import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const base = process.env.SENTINEL_API_BASE_URL || "http://127.0.0.1:8080";

  try {
    const response = await fetch(`${base.replace(/\/$/, "")}/api/heatmap`, {
      cache: "no-store"
    });

    if (!response.ok) {
      return NextResponse.json([], { status: 200 });
    }

    const data = await response.json();
    return NextResponse.json(Array.isArray(data) ? data : []);
  } catch {
    return NextResponse.json([], { status: 200 });
  }
}
