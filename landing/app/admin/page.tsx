import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = {
  title: "Admin",
  alternates: { canonical: null },
  openGraph: null,
  twitter: null,
  robots: { index: false, follow: false, noarchive: true },
};

export default function Admin() {
  const page = legacyDocument("admin");
  return <LegacyPage {...page} pageStylesheets={["/assets/admin.css", "/assets/ui-kit.css"]} scripts={["/assets/ui-kit.js", "/assets/admin.js"]} />;
}
