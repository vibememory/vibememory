import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

const assetVersion = "20261030-v019-2";

export const metadata: Metadata = {
  metadataBase: new URL("https://vibememory.io"),
  title: { default: "Vibe Memory", template: "%s — Vibe Memory" },
  description: "One shared memory layer for your AI agents.",
  icons: { icon: "/assets/favicon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#f8f9fc",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="ko">
      <head>
        <link rel="stylesheet" href={`/assets/style.css?v=${assetVersion}`} />
        <link rel="stylesheet" href={`/assets/i18n.css?v=${assetVersion}`} />
        <link rel="stylesheet" href={`/assets/console-fixes.css?v=${assetVersion}`} />
        <script src={`/assets/i18n.js?v=${assetVersion}`} defer />
        <script src={`/assets/install-prompt.js?v=${assetVersion}`} defer />
      </head>
      <body>{children}</body>
    </html>
  );
}
