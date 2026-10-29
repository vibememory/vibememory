import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = {
  title: "Connection guide",
  description: "Connect Vibe Memory CLI Skills, keyword search, and byte-stream uploads.",
  alternates: { canonical: "/guide.html" },
};

export default function Guide() {
  const page = legacyDocument("guide");
  return <LegacyPage {...page} pageStylesheet="/assets/guide.css" />;
}
