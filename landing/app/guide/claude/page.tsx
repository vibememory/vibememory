import type { Metadata } from "next";
import { ChatGuidePage, findChatGuide } from "@/components/ChatGuidePage";
import { SeoJsonLd } from "@/components/SeoJsonLd";
import guides from "@/data/chat-guides.json";

const guide = findChatGuide("claude")!;
const description = "Claude 일반 채팅에 Vibe Memory 원격 Connector를 추가하고 기억 검색과 저장을 사용하는 연결 가이드입니다.";

export const metadata: Metadata = {title:"Claude 일반 채팅 연결 가이드",description,alternates:{canonical:"/guide/claude"},openGraph:{type:"article",url:"/guide/claude",title:"Claude × Vibe Memory 일반 채팅 가이드",description,images:[{url:"/assets/og-vibe-memory-v2.png",width:1200,height:630,alt:"Claude Vibe Memory guide"}]}};

export default function ClaudeGuide() {
  const jsonLd = {"@context":"https://schema.org","@type":"TechArticle",headline:"Claude Vibe Memory 일반 채팅 연결 가이드",description,url:"https://vibememory.io/guide/claude",dateModified:guides.verified_at.slice(0,10),inLanguage:["ko","en","zh","ja","es","vi","th"],about:[{"@type":"SoftwareApplication",name:"Claude"},{"@type":"SoftwareApplication",name:"Vibe Memory"}],author:{"@type":"Organization",name:"Vibe Memory contributors",url:"https://github.com/vibememory"}};
  return <><SeoJsonLd data={jsonLd} /><ChatGuidePage guide={guide} /></>;
}
