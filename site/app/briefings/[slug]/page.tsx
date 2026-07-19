import type { Metadata } from "next";
import { notFound } from "next/navigation";
import SponsorCard from "@/components/SponsorCard";
import { getAllBriefings, getBriefing, SITE_NAME, siteUrl } from "@/lib/content";
import { isSponsorRelevant } from "@/lib/sponsor";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return getAllBriefings().map((b) => ({ slug: b.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const b = getBriefing(slug);
  if (!b) return {};
  return {
    title: b.title,
    description: b.description,
    alternates: { canonical: `/briefings/${b.slug}` },
    openGraph: {
      title: b.title,
      description: b.description,
      type: "article",
      publishedTime: b.publishedAt,
      modifiedTime: b.updatedAt,
    },
  };
}

export default async function BriefingPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const b = getBriefing(slug);
  if (!b) notFound();

  const articleLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: b.title,
    description: b.description,
    datePublished: b.publishedAt,
    dateModified: b.updatedAt,
    inLanguage: "en",
    mainEntityOfPage: `${siteUrl()}/briefings/${b.slug}`,
    author: {
      "@type": "Organization",
      name: SITE_NAME,
      url: siteUrl(),
    },
    publisher: {
      "@type": "Organization",
      name: SITE_NAME,
    },
    citation: b.sources.map((s) => s.url),
  };
  const faqLd =
    b.faq.length > 0
      ? {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: b.faq.map((f) => ({
            "@type": "Question",
            name: f.q,
            acceptedAnswer: { "@type": "Answer", text: f.a },
          })),
        }
      : null;

  return (
    <article className="article container">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleLd) }}
      />
      {faqLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(faqLd) }}
        />
      )}
      <span className="badge cat">{b.category}</span>
      <h1>{b.title}</h1>
      <div className="dateline">
        Published {new Date(b.publishedAt).toUTCString()} · Last updated{" "}
        {new Date(b.updatedAt).toUTCString()}
      </div>

      <div className="stats">
        <div className="stat">
          <strong>{b.keyword}</strong>trending search term
        </div>
        <div className="stat">
          <strong>{b.trafficLowerBound?.toLocaleString() ?? "n/a"}+</strong>searches
          (Google-reported lower bound)
        </div>
        <div className="stat">
          <strong>{b.geo}</strong>region of this snapshot
        </div>
      </div>

      {b.sections.map((s, i) => (
        <section key={i}>
          <h2>{s.heading}</h2>
          {s.paragraphs.map((p, j) => (
            <p key={j}>{p}</p>
          ))}
          {s.list && (
            <ul>
              {s.list.map((item, j) => (
                <li key={j}>{item}</li>
              ))}
            </ul>
          )}
        </section>
      ))}

      {b.faq.length > 0 && (
        <section className="faq">
          <h2>Frequently asked questions</h2>
          {b.faq.map((f, i) => (
            <details key={i}>
              <summary>{f.q}</summary>
              <p>{f.a}</p>
            </details>
          ))}
        </section>
      )}

      <div className="sources">
        <h2>Named sources</h2>
        <ol>
          {b.sources.map((s, i) => (
            <li key={i}>
              <a href={s.url} rel="nofollow noopener" target="_blank">
                {s.title}
              </a>{" "}
              — {s.source}
            </li>
          ))}
        </ol>
      </div>

      {isSponsorRelevant(b.category) && <SponsorCard />}

      <div className="disclosure" data-testid="ai-disclosure">
        <strong>Transparency note:</strong> this briefing was assembled automatically
        from the cited sources and Google Trends data
        {b.mode === "llm"
          ? ", drafted with AI assistance and approved by an independent automated review gate before publication"
          : " using a deterministic fact-briefing template (no generative text)"}
        . Review score: {b.review.score.toFixed(2)} ({b.review.mode}). Read our{" "}
        <a href="/about">editorial &amp; AI policy</a>. Found an error?{" "}
        <a href="/about#corrections">Request a correction</a>.
      </div>
    </article>
  );
}
