import type { Metadata } from "next";
import { AgentSupportMatrix } from "@/components/AgentSupportMatrix";
import { LegacyPage } from "@/components/LegacyPage";
import { SeoJsonLd } from "@/components/SeoJsonLd";
import { legacyDocument } from "@/lib/legacy";

const description =
  "Claude Code, Codex, Cursor 등 여러 AI 에이전트에 하나의 기억과 관계 그래프를 연결하세요. MCP, Skill, Rust CLI와 self-hosting을 지원하며 별도 LLM 호출 없이 동작합니다.";

export const metadata: Metadata = {
  title: { absolute: "Vibe Memory — AI 에이전트를 위한 공유 기억 레이어" },
  description,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "Vibe Memory",
    locale: "ko_KR",
    title: "Vibe Memory — One memory, every agent",
    description,
    images: [
      {
        url: "/assets/og-vibe-memory-v2.png",
        width: 1200,
        height: 630,
        alt: "Vibe Memory — One memory, every agent",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Vibe Memory — One memory, every agent",
    description,
    images: ["/assets/og-vibe-memory-v2.png"],
  },
};

export default function Home() {
  const page = legacyDocument("index");
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": "https://vibememory.io/#organization",
        name: "Vibe Memory",
        url: "https://vibememory.io/",
        logo: {
          "@type": "ImageObject",
          url: "https://vibememory.io/assets/favicon.svg",
        },
        sameAs: ["https://github.com/vibememory"],
      },
      {
        "@type": "WebSite",
        "@id": "https://vibememory.io/#website",
        name: "Vibe Memory",
        alternateName: "VibeMemory",
        url: "https://vibememory.io/",
        description,
        inLanguage: ["ko", "en", "zh", "ja", "es", "vi", "th"],
        publisher: { "@id": "https://vibememory.io/#organization" },
      },
      {
        "@type": "SoftwareApplication",
        "@id": "https://vibememory.io/#software",
        name: "Vibe Memory",
        url: "https://vibememory.io/",
        description,
        applicationCategory: "DeveloperApplication",
        operatingSystem: "Web, Linux, macOS, Windows",
        softwareVersion: "0.26.4",
        isAccessibleForFree: true,
        offers: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
        },
        image: "https://vibememory.io/assets/og-vibe-memory-v2.png",
        downloadUrl: "https://vibememory.io/downloads/vibe-memory-skill.zip",
        codeRepository: "https://github.com/vibememory/vibememory",
        featureList: [
          "Shared memory across AI agents",
          "MCP and agent Skill integrations",
          "Agent-authored entities and relationship graph",
          "Keyword-only local embeddings",
          "Byte-stream file storage",
          "Self-hosted deployment",
        ],
        publisher: { "@id": "https://vibememory.io/#organization" },
      },
    ],
  };
  return (
    <>
      <SeoJsonLd data={jsonLd} />
      <LegacyPage
        {...page}
        scripts={["/assets/app.js"]}
        slot={{ marker: "<!-- AGENT_SUPPORT_MATRIX -->", node: <AgentSupportMatrix /> }}
      />
    </>
  );
}
