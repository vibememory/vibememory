import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export default function NotFound() {
  const page = legacyDocument("404");
  return <LegacyPage {...page} />;
}
