import type { ReactNode } from "react";

type Props = {
  body: string;
  bodyClass?: string;
  pageStylesheet?: string;
  pageStylesheets?: string[];
  scripts?: string[];
  slot?: { marker: string; node: ReactNode };
};

const assetVersion = "20261030-v026-0";
const versioned = (path: string) => `${path}?v=${assetVersion}`;

export function LegacyPage({ body, bodyClass = "", pageStylesheet, pageStylesheets = [], scripts = [], slot }: Props) {
  const stylesheets = [...pageStylesheets, ...(pageStylesheet ? [pageStylesheet] : [])];
  const parts = slot ? body.split(slot.marker) : [body];
  if (slot && parts.length !== 2) throw new Error(`Legacy page slot marker must appear exactly once: ${slot.marker}`);
  return (
    <>
      {stylesheets.map((href) => <link key={href} rel="stylesheet" href={versioned(href)} />)}
      {stylesheets.length > 0 ? <link rel="stylesheet" href={versioned("/assets/theme.css")} /> : null}
      {stylesheets.length > 0 ? <link rel="stylesheet" href={versioned("/assets/product-ui.css")} /> : null}
      {slot ? (
        <div className={bodyClass || undefined}>
          <div dangerouslySetInnerHTML={{ __html: parts[0] }} />
          {slot.node}
          <div dangerouslySetInnerHTML={{ __html: parts[1] }} />
        </div>
      ) : <div className={bodyClass || undefined} dangerouslySetInnerHTML={{ __html: body }} />}
      {scripts.map((src) => (
        <script key={src} src={versioned(src)} defer />
      ))}
    </>
  );
}
