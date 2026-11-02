import { LegacyPage } from "@/components/LegacyPage";
import { legacyDocument } from "@/lib/legacy";

export type AdminView = "overview" | "requests" | "operators" | "users";

export function AdminPage({ view }: { view: AdminView }) {
  const page = legacyDocument("admin");
  return (
    <LegacyPage
      {...page}
      bodyClass={`admin-page admin-view-${view}`}
      pageStylesheets={["/assets/admin.css", "/assets/ui-kit.css"]}
      scripts={["/assets/ui-kit.js", "/assets/admin.js"]}
    />
  );
}
