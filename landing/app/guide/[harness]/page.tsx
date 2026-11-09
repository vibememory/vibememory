import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { HarnessGuidePage, findHarnessGuide } from "@/components/HarnessGuidePage";
import { SeoJsonLd } from "@/components/SeoJsonLd";
import guides from "@/data/harness-guides.json";

type Props = { params: Promise<{ harness: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return guides.guides.map((guide) => ({ harness: guide.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { harness } = await params;
  const guide = findHarnessGuide(harness);
  if (!guide) return {};
  const description = `${guide.name}에서 Vibe Memory Skill, 원격 MCP, 자동 Hook을 설치하고 검증하는 제품별 가이드입니다.`;
  return {
    title: `${guide.name} 연결 가이드`,
    description,
    alternates: { canonical: `/guide/${guide.slug}` },
    openGraph: {
      type: "article",
      url: `/guide/${guide.slug}`,
      siteName: "Vibe Memory",
      title: `${guide.name} × Vibe Memory 연결 가이드`,
      description,
      images: [{ url: "/assets/og-vibe-memory-v2.png", width: 1200, height: 630, alt: `${guide.name} Vibe Memory guide` }],
    },
    twitter: { card: "summary_large_image", title: `${guide.name} × Vibe Memory`, description, images: ["/assets/og-vibe-memory-v2.png"] },
  };
}

export default async function HarnessGuide({ params }: Props) {
  const { harness } = await params;
  const guide = findHarnessGuide(harness);
  if (!guide) notFound();
  const canonical = `https://vibememory.io/guide/${guide.slug}`;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    headline: `${guide.name} Vibe Memory 연결 가이드`,
    description: guide.summary,
    url: canonical,
    mainEntityOfPage: canonical,
    dateModified: guides.verified_at.slice(0, 10),
    inLanguage: ["ko", "en", "zh", "ja", "es", "vi", "th"],
    about: [{ "@type": "SoftwareApplication", name: guide.name }, { "@type": "SoftwareApplication", name: "Vibe Memory" }],
    author: { "@type": "Organization", name: "Vibe Memory contributors", url: "https://github.com/vibememory" },
  };
  return <><SeoJsonLd data={jsonLd} /><HarnessGuidePage guide={guide} /></>;
}
