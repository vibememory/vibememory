import type { Metadata } from "next";
import { ChatGuideDirectory } from "@/components/ChatGuideDirectory";
import { PublicHeaderControls } from "@/components/PublicHeaderControls";
import { SeoJsonLd } from "@/components/SeoJsonLd";
import guides from "@/data/chat-guides.json";

const description = "ChatGPT와 Claude 일반 채팅에서 Vibe Memory 원격 MCP를 연결하고 기억 검색과 체크포인트 저장을 사용하는 가이드입니다.";

export const metadata: Metadata = {
  title: "ChatGPT·Claude 일반 채팅 연결 가이드",
  description,
  alternates: { canonical: "/guide/chat" },
  openGraph: { type: "website", url: "/guide/chat", title: "Vibe Memory 일반 채팅 가이드", description },
};

export default function ChatGuideIndex() {
  const jsonLd = {"@context":"https://schema.org","@type":"CollectionPage",name:"Vibe Memory 일반 채팅 연결 가이드",description,url:"https://vibememory.io/guide/chat",dateModified:guides.verified_at.slice(0,10),hasPart:guides.guides.map((guide)=>({"@type":"TechArticle",name:`${guide.name} 일반 채팅 연결 가이드`,url:`https://vibememory.io/guide/${guide.slug}`}))};
  return <><SeoJsonLd data={jsonLd} /><link rel="stylesheet" href="/assets/guide.css?v=20261109-v039-4" /><link rel="stylesheet" href="/assets/chat-guide.css?v=20261109-v039-4" /><a className="skip" href="#main">본문으로 바로가기</a><header className="header wrap chat-public-header"><a href="/" className="brand" aria-label="Vibe Memory home"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="m7 9 9-4 9 8-6 13-13-6L7 9Zm0 0 12 17M16 5 6 20l19-7"/><circle cx="7" cy="9" r="3"/><circle cx="16" cy="5" r="3"/><circle cx="25" cy="13" r="3"/><circle cx="19" cy="26" r="3"/><circle cx="6" cy="20" r="3"/></svg><span>vibe<span className="brand-light">memory</span></span></a><div className="header-actions public-header-actions"><PublicHeaderControls /><a className="nav-cta" href="/guide/harnesses">코딩 하네스 가이드</a></div></header><main className="chat-index wrap" id="main"><ChatGuideDirectory /></main></>;
}
