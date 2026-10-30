import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

const assetVersion = "20261030-v025-0";

export const metadata: Metadata = {
  metadataBase: new URL("https://vibememory.io"),
  title: { default: "Vibe Memory", template: "%s — Vibe Memory" },
  description: "One shared memory layer for your AI agents.",
  icons: { icon: "/assets/favicon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8f9fc" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1020" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        <script src={`/assets/theme-init.js?v=${assetVersion}`} />
        <link rel="stylesheet" href={`/assets/style.css?v=${assetVersion}`} />
        <link rel="stylesheet" href={`/assets/i18n.css?v=${assetVersion}`} />
        <link rel="stylesheet" href={`/assets/console-fixes.css?v=${assetVersion}`} />
        <link rel="stylesheet" href={`/assets/theme.css?v=${assetVersion}`} />
        <link rel="stylesheet" href={`/assets/product-ui.css?v=${assetVersion}`} />
        <script src={`/assets/theme.js?v=${assetVersion}`} defer />
        <script src={`/assets/i18n.js?v=${assetVersion}`} defer />
        <script src={`/assets/install-prompt.js?v=${assetVersion}`} defer />
      </head>
      <body>{children}</body>
    </html>
  );
}
