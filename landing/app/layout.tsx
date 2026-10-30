import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

const assetVersion = "20261030-v026-0";

const siteDescription =
  "Claude Code, Codex, Cursor 등 여러 AI 에이전트가 기억과 관계를 공유하도록 연결하는 오픈소스 메모리 레이어입니다. MCP, Skill, Rust CLI와 self-hosting을 지원합니다.";

export const metadata: Metadata = {
  metadataBase: new URL("https://vibememory.io"),
  title: {
    default: "Vibe Memory — AI 에이전트를 위한 공유 기억 레이어",
    template: "%s | Vibe Memory",
  },
  description: siteDescription,
  applicationName: "Vibe Memory",
  authors: [{ name: "Vibe Memory contributors", url: "https://github.com/vibememory" }],
  creator: "Vibe Memory contributors",
  publisher: "Vibe Memory",
  category: "technology",
  keywords: [
    "AI agent memory",
    "에이전트 메모리",
    "Claude Code memory",
    "Codex memory",
    "MCP server",
    "agent skills",
    "knowledge graph",
    "self-hosted AI",
    "Vibe Memory",
  ],
  referrer: "strict-origin-when-cross-origin",
  formatDetection: { email: false, address: false, telephone: false },
  alternates: { canonical: "/" },
  manifest: "/site.webmanifest",
  icons: {
    icon: [{ url: "/assets/favicon.svg", type: "image/svg+xml" }],
    shortcut: "/assets/favicon.svg",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      noimageindex: false,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "Vibe Memory",
    locale: "ko_KR",
    title: "Vibe Memory — One memory, every agent",
    description: siteDescription,
    images: [
      {
        url: "/assets/og-vibe-memory.png",
        width: 1200,
        height: 630,
        alt: "Vibe Memory — One memory, every agent",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Vibe Memory — One memory, every agent",
    description: siteDescription,
    images: ["/assets/og-vibe-memory.png"],
  },
  other: {
    "mobile-web-app-capable": "yes",
  },
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
