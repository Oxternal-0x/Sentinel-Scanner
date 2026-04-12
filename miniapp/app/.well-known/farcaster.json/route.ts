import { NextResponse } from "next/server";

export function GET() {
  const homeUrl = process.env.NEXT_PUBLIC_FARCASTER_HOME_URL || "https://yourdomain.com";
  const appName = process.env.NEXT_PUBLIC_FARCASTER_APP_NAME || "Sentinel Compliance AI";
  const iconUrl = process.env.NEXT_PUBLIC_FARCASTER_ICON_URL || `${homeUrl.replace(/\/$/, "")}/icon.svg`;

  return NextResponse.json({
    accountAssociation: {
      header: process.env.FARCASTER_ACCOUNT_ASSOCIATION_HEADER || "",
      payload: process.env.FARCASTER_ACCOUNT_ASSOCIATION_PAYLOAD || "",
      signature: process.env.FARCASTER_ACCOUNT_ASSOCIATION_SIGNATURE || ""
    },
    miniapp: {
      version: process.env.NEXT_PUBLIC_FARCASTER_APP_VERSION || "1.0.0",
      name: appName,
      homeUrl,
      iconUrl,
      splashImageUrl: process.env.NEXT_PUBLIC_FARCASTER_SPLASH_IMAGE_URL || iconUrl,
      splashBackgroundColor: "#f5efe5",
      subtitle: "Autonomous DeFi Compliance",
      description:
        process.env.NEXT_PUBLIC_FARCASTER_APP_DESCRIPTION ||
        "Compliance heatmap and risk intelligence for DeFi protocols.",
      primaryCategory: "finance",
      tags: ["compliance", "defi", "security", "audit"],
      heroImageUrl: process.env.NEXT_PUBLIC_FARCASTER_FRAME_IMAGE_URL || iconUrl
    }
  });
}
