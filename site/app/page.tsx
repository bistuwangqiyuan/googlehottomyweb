import Link from "next/link";
import { getAllBriefings, SITE_NAME, SITE_TAGLINE, siteUrl } from "@/lib/content";

export const dynamic = "force-static";

export default function HomePage() {
  const briefings = getAllBriefings();
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: SITE_NAME,
    url: siteUrl(),
    description: SITE_TAGLINE,
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <section className="hero">
        <div className="container">
          <span className="badge">Updated automatically, reviewed before publish</span>
          <h1>What the world is searching for — with the facts behind it</h1>
          <p>{SITE_TAGLINE}</p>
        </div>
      </section>
      <section className="container">
        <div className="card-list">
          {briefings.length === 0 && (
            <div className="empty">
              No briefings published yet. The pipeline publishes only content that
              passes the review gate.
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
