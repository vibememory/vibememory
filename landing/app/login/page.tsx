import type { Metadata } from "next";
import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export const metadata: Metadata = { title: "Login", robots: { index: false, follow: false } };

export default function Login() {
  const page = legacyDocument("login");
  return <LegacyPage {...page} pageStylesheet="/assets/console.css" scripts={["/assets/login.js"]} />;
}
