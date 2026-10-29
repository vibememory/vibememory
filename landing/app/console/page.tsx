import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = { title: "Workspace", robots: { index: false, follow: false } };

export default function Console() {
  const page = legacyDocument("console");
  return <LegacyPage {...page} pageStylesheet="/assets/console.css" scripts={["/assets/vendor/cytoscape.min.js", "/assets/console.js"]} />;
}
