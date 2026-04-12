const appName = process.env.NEXT_PUBLIC_FARCASTER_APP_NAME || "Sentinel Compliance AI";
const appUrl = process.env.NEXT_PUBLIC_FARCASTER_HOME_URL || "https://yourdomain.com";
const imageUrl = process.env.NEXT_PUBLIC_FARCASTER_FRAME_IMAGE_URL || `${appUrl.replace(/\/$/, "")}/icon.svg`;

const frameContent = JSON.stringify({
  version: "next",
  imageUrl,
  button: {
    title: "Launch Compliance AI",
    action: {
      type: "launch_frame",
      name: appName,
      url: appUrl
    }
  }
});

export default function Head() {
  return <meta name="fc:frame" content={frameContent} />;
}
