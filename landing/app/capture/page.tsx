import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = {
  title: "Secure Vault Capture",
  robots: { index: false, follow: false },
};

export default function Capture() {
  const page = legacyDocument("capture");
  return <LegacyPage {...page} pageStylesheet="/assets/console.css" scripts={["/assets/capture.js"]} />;
}
