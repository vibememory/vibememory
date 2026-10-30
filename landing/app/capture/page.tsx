import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = {
  title: "Secure Vault Capture",
  alternates: { canonical: null },
  openGraph: null,
  twitter: null,
  robots: { index: false, follow: false, noarchive: true },
};

export default function Capture() {
  const page = legacyDocument("capture");
  return <LegacyPage {...page} pageStylesheet="/assets/console.css" scripts={["/assets/capture.js"]} />;
}
