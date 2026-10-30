import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { SeoJsonLd } from "@/components/SeoJsonLd";
import { legacyDocument } from "@/lib/legacy";

const description =
  "Vibe Memory 설치, MCP 연결, 계정 보안과 self-hosting 문제를 해결할 수 있는 공식 지원 안내입니다.";

export const metadata: Metadata = {
  title: "지원",
  description,
  alternates: { canonical: "/support" },
  openGraph: {
    type: "website",
    url: "/support",
    siteName: "Vibe Memory",
    locale: "ko_KR",
    title: "Vibe Memory Support",
    description,
  },
};

export default function Support() {
  const page = legacyDocument("support");
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ContactPage",
    name: "Vibe Memory Support",
    description,
    url: "https://vibememory.io/support",
    inLanguage: ["ko-KR", "en"],
    isPartOf: { "@id": "https://vibememory.io/#website" },
  };
  return (
    <>
      <SeoJsonLd data={jsonLd} />
      <LegacyPage {...page} pageStylesheet="/assets/guide.css" />
    </>
  );
}
