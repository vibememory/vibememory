import type { Metadata } from "next";
import { ChatGuidePage, findChatGuide } from "@/components/ChatGuidePage";
import { SeoJsonLd } from "@/components/SeoJsonLd";
import guides from "@/data/chat-guides.json";

const guide = findChatGuide("chatgpt")!;
const description = "ChatGPT Chat과 Work에 Vibe Memory Plugin을 설치하고 원격 MCP 기억 검색과 저장을 사용하는 일반 채팅 가이드입니다.";

export const metadata: Metadata = {title:"ChatGPT 일반 채팅 연결 가이드",description,alternates:{canonical:"/guide/chatgpt"},openGraph:{type:"article",url:"/guide/chatgpt",title:"ChatGPT × Vibe Memory 일반 채팅 가이드",description,images:[{url:"/assets/og-vibe-memory-v2.png",width:1200,height:630,alt:"ChatGPT Vibe Memory guide"}]}};

export default function ChatGptGuide() {
  const jsonLd = {"@context":"https://schema.org","@type":"TechArticle",headline:"ChatGPT Vibe Memory 일반 채팅 연결 가이드",description,url:"https://vibememory.io/guide/chatgpt",dateModified:guides.verified_at.slice(0,10),inLanguage:["ko","en","zh","ja","es","vi","th"],about:[{"@type":"SoftwareApplication",name:"ChatGPT"},{"@type":"SoftwareApplication",name:"Vibe Memory"}],author:{"@type":"Organization",name:"Vibe Memory contributors",url:"https://github.com/vibememory"}};
  return <><SeoJsonLd data={jsonLd} /><ChatGuidePage guide={guide} /></>;
}
