type Props = {
  body: string;
  bodyClass?: string;
  pageStylesheet?: string;
  scripts?: string[];
};

const assetVersion = "20261029-admin-console-1";
const versioned = (path: string) => `${path}?v=${assetVersion}`;

export function LegacyPage({ body, bodyClass = "", pageStylesheet, scripts = [] }: Props) {
  return (
    <>
      {pageStylesheet ? <link rel="stylesheet" href={versioned(pageStylesheet)} /> : null}
      <div className={bodyClass || undefined} dangerouslySetInnerHTML={{ __html: body }} />
      {scripts.map((src) => (
        <script key={src} src={versioned(src)} defer />
      ))}
    </>
  );
}
