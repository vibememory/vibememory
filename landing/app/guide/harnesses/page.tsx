import type { Metadata } from "next";
import { HarnessGuideDirectory } from "@/components/HarnessGuideDirectory";
import { PublicHeaderControls } from "@/components/PublicHeaderControls";
import { SeoJsonLd } from "@/components/SeoJsonLd";
import guides from "@/data/harness-guides.json";

const description = "Claude Code, Codex, Cursor, Muse Code, Hermes Agent, OpenClaw에 Vibe Memory를 연결하는 제품별 설치 가이드입니다.";

export const metadata: Metadata = {
  title: "에이전트 하네스별 연결 가이드",
  description,
  alternates: { canonical: "/guide/harnesses" },
  openGraph: { type: "website", url: "/guide/harnesses", title: "Vibe Memory 제품별 연결 가이드", description },
};

export default function HarnessesGuideIndex() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Vibe Memory 에이전트 하네스별 연결 가이드",
    description,
    url: "https://vibememory.io/guide/harnesses",
    dateModified: guides.verified_at.slice(0, 10),
    hasPart: guides.guides.map((guide) => ({
      "@type": "TechArticle",
      name: `${guide.name} Vibe Memory 연결 가이드`,
      url: `https://vibememory.io/guide/${guide.slug}`,
    })),
  };
  return (
    <>
      <SeoJsonLd data={jsonLd} />
      <link rel="stylesheet" href="/assets/guide.css?v=20261109-v039-3" />
      <link rel="stylesheet" href="/assets/harness-guide.css?v=20261109-v039-3" />
      <a className="skip" href="#main">본문으로 바로가기</a>
      <header className="header wrap">
        <a href="/" className="brand" aria-label="Vibe Memory home">
          <svg viewBox="0 0 32 32" aria-hidden="true"><path d="m7 9 9-4 9 8-6 13-13-6L7 9Zm0 0 12 17M16 5 6 20l19-7"/><circle cx="7" cy="9" r="3"/><circle cx="16" cy="5" r="3"/><circle cx="25" cy="13" r="3"/><circle cx="19" cy="26" r="3"/><circle cx="6" cy="20" r="3"/></svg>
          <span>vibe<span className="brand-light">memory</span></span>
        </a>
        <div className="header-actions public-header-actions"><PublicHeaderControls /><a className="nav-cta" href="/guide">전체 연결 가이드</a></div>
      </header>
      <main className="harness-index wrap" id="main">
        <HarnessGuideDirectory />
        <div className="harness-index-note"><strong>공통 원칙</strong><p>Skill은 행동 지침, MCP는 서버 도구, Hook은 로컬 생명주기 자동화입니다. 세 기능을 따로 검토하고 현재 제품의 가이드만 적용하세요.</p></div>
      </main>
    </>
  );
}
