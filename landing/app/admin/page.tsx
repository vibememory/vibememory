import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = {
  title: "Admin",
  robots: { index: false, follow: false },
};

export default function Admin() {
  const page = legacyDocument("admin");
  return <LegacyPage {...page} pageStylesheets={["/assets/admin.css", "/assets/ui-kit.css"]} scripts={["/assets/ui-kit.js", "/assets/admin.js"]} />;
}
