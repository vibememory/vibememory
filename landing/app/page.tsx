import type { Metadata } from "next";
import { AgentSupportMatrix } from "@/components/AgentSupportMatrix";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = {
  title: "에이전트가 바뀌어도, 기억은 이어지도록",
  alternates: { canonical: "/" },
  openGraph: { title: "Vibe Memory — One memory, every agent", url: "/" },
};

export default function Home() {
  const page = legacyDocument("index");
  return <LegacyPage {...page} scripts={["/assets/app.js"]} slot={{ marker: "<!-- AGENT_SUPPORT_MATRIX -->", node: <AgentSupportMatrix /> }} />;
}
