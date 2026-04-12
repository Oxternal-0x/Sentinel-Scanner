import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/providers";

const appName = process.env.NEXT_PUBLIC_FARCASTER_APP_NAME || "Sentinel Compliance AI";

export const metadata: Metadata = {
  title: appName,
  description: "Compliance heatmap and risk intelligence for DeFi protocols."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
