import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = {
  title: "Login",
  alternates: { canonical: null },
  openGraph: null,
  twitter: null,
  robots: { index: false, follow: false, noarchive: true },
};

export default function Login() {
  const page = legacyDocument("login");
  return <LegacyPage {...page} pageStylesheet="/assets/console.css" scripts={["/assets/login.js"]} />;
}
