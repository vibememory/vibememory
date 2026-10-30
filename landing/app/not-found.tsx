import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = {
  title: "페이지를 찾을 수 없음",
  alternates: { canonical: null },
  openGraph: null,
  twitter: null,
  robots: { index: false, follow: false, noarchive: true },
};

export default function NotFound() {
  const page = legacyDocument("404");
  return <LegacyPage {...page} />;
}
