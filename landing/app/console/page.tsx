import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = {
  title: "Workspace",
  alternates: { canonical: null },
  openGraph: null,
  twitter: null,
  robots: { index: false, follow: false, noarchive: true },
};

export default function Console() {
  const page = legacyDocument("console");
  return <LegacyPage {...page} pageStylesheets={["/assets/console.css", "/assets/ui-kit.css"]} scripts={["/assets/vendor/cytoscape.min.js", "/assets/ui-kit.js", "/assets/console.js"]} />;
}
