type JsonLdValue = Record<string, unknown> | Array<Record<string, unknown>>;

type Props = {
  data: JsonLdValue;
};

export function SeoJsonLd({ data }: Props) {
  const json = JSON.stringify(data).replace(/</g, "\\u003c");
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />;
}
