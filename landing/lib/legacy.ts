import { readFileSync } from "node:fs";
import { join } from "node:path";

export type LegacyDocument = { body: string; bodyClass: string };

export function legacyDocument(name: string): LegacyDocument {
  const source = readFileSync(join(process.cwd(), "templates", `${name}.html`), "utf8");
  const match = source.match(/<body(?:\s+class="([^"]*)")?>([\s\S]*?)<\/body>/i);
  if (!match) throw new Error(`Template ${name} has no body`);
  return { bodyClass: match[1] || "", body: match[2] };
}
