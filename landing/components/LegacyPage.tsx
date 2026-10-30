type Props = {
  body: string;
  bodyClass?: string;
  pageStylesheet?: string;
  pageStylesheets?: string[];
  scripts?: string[];
};

const assetVersion = "20261030-v019-2";
const versioned = (path: string) => `${path}?v=${assetVersion}`;

export function LegacyPage({ body, bodyClass = "", pageStylesheet, pageStylesheets = [], scripts = [] }: Props) {
  const stylesheets = [...pageStylesheets, ...(pageStylesheet ? [pageStylesheet] : [])];
  return (
    <>
      {stylesheets.map((href) => <link key={href} rel="stylesheet" href={versioned(href)} />)}
      <div className={bodyClass || undefined} dangerouslySetInnerHTML={{ __html: body }} />
      {scripts.map((src) => (
        <script key={src} src={versioned(src)} defer />
      ))}
    </>
  );
}
