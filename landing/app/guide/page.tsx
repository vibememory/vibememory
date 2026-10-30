import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { SeoJsonLd } from "@/components/SeoJsonLd";
import { legacyDocument } from "@/lib/legacy";

const description =
  "Vibe Memory를 Claude Code, Codex, Cursor, ChatGPT Work와 연결하는 방법을 확인하세요. MCP, Skill, Rust CLI, Hook, 키워드 검색과 바이트 스트림 업로드를 설명합니다.";

export const metadata: Metadata = {
  title: "AI 에이전트 연결 가이드",
  description,
  alternates: { canonical: "/guide" },
  openGraph: {
    type: "article",
    url: "/guide",
    siteName: "Vibe Memory",
    locale: "ko_KR",
    title: "Vibe Memory AI 에이전트 연결 가이드",
    description,
    images: [
      {
        url: "/assets/og-vibe-memory-v2.png",
        width: 1200,
        height: 630,
        alt: "Vibe Memory connection guide",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Vibe Memory AI 에이전트 연결 가이드",
    description,
    images: ["/assets/og-vibe-memory-v2.png"],
  },
};

export default function Guide() {
  const page = legacyDocument("guide");
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "@id": "https://vibememory.io/guide#article",
    headline: "Vibe Memory AI 에이전트 연결 가이드",
    description,
    url: "https://vibememory.io/guide",
    mainEntityOfPage: "https://vibememory.io/guide",
    dateModified: "2026-10-30",
    inLanguage: "ko-KR",
    image: "https://vibememory.io/assets/og-vibe-memory-v2.png",
    author: {
      "@type": "Organization",
      name: "Vibe Memory contributors",
      url: "https://github.com/vibememory",
    },
    publisher: {
      "@type": "Organization",
      name: "Vibe Memory",
      url: "https://vibememory.io/",
    },
  };
  return (
    <>
      <SeoJsonLd data={jsonLd} />
      <LegacyPage {...page} pageStylesheet="/assets/guide.css" />
    </>
  );
}
