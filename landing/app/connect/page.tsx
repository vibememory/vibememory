import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = { title: "Connect agent", robots: { index: false, follow: false } };

export default function Connect() {
  const page = legacyDocument("connect");
  return <LegacyPage {...page} pageStylesheets={["/assets/console.css", "/assets/ui-kit.css"]} scripts={["/assets/connect.js"]} />;
}
