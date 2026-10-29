import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = {
  title: "Admin",
  robots: { index: false, follow: false },
};

export default function Admin() {
  const page = legacyDocument("admin");
  return <LegacyPage {...page} pageStylesheet="/assets/admin.css" scripts={["/assets/admin.js"]} />;
}
