import type { Metadata } from "next";
import Link from "next/link";
import SponsorCard from "@/components/SponsorCard";
import { getAllBriefings, SITE_NAME, siteUrl } from "@/lib/content";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "AI Infrastructure Briefings — chips, models, data centers, storage",
  description:
    "All fact-checked briefings on AI infrastructure: GPUs and accelerators, " +
    "large language models, data centers, HPC, and AI storage — with named sources.",
  alternates: { canonical: "/ai-infrastructure" },
};

/**
 * AI 基础设施垂直枢纽页：聚合全部 ai-infra 类简报。
 * 作用：给垂直线一个稳定的收录入口（SEO）+ 集中内链，
 * 顶部保留与简报页相同的合规赞助卡（可见标注 + rel=sponsored + UTM）。
 */
export default function AiInfrastructureHub() {
  const briefings = getAllBriefings().filter((b) => b.category === "ai-infra");
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "AI Infrastructure Briefings",
    url: `${siteUrl()}/ai-infrastructure`,
    isPartOf: { "@type": "WebSite", name: SITE_NAME, url: siteUrl() },
    hasPart: briefings.map((b) => ({
      "@type": "Article",
      headline: b.title,
      url: `${siteUrl()}/briefings/${b.slug}`,
      datePublished: b.publishedAt,
    })),
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <section className="hero">
        <div className="container">
          <span className="badge cat">ai-infra</span>
          <h1>AI Infrastructure Briefings</h1>
          <p>
            Every fact-checked briefing we publish on chips and accelerators, large
            language models, data centers, HPC, and AI storage — assembled from named
            sources and approved by an automated review gate.
          </p>
        </div>
      </section>
      <section className="container">
        <SponsorCard />
        <div className="card-list">
          {briefings.length === 0 && (
            <div className="empty">
              No AI-infrastructure briefings live right now. The pipeline publishes
              only content that passes the review gate; new briefings appear here
              automatically.
            </div>
          )}
          {briefings.map((b) => (
            <Link key={b.slug} href={`/briefings/${b.slug}`} className="card">
              <span className="badge cat">{b.category}</span>
              <h2>{b.title}</h2>
              <p>{b.description}</p>
              <div className="meta">
                {b.geo} · search interest {b.trafficLowerBound?.toLocaleString() ?? "n/a"}+ ·{" "}
                {new Date(b.publishedAt).toISOString().slice(0, 10)} · {b.sources.length}{" "}
                cited source{b.sources.length === 1 ? "" : "s"}
              </div>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
