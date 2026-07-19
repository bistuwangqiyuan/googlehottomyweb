import type { Metadata } from "next";
import { SITE_NAME } from "@/lib/content";
import { SPONSOR } from "@/lib/sponsor";

export const metadata: Metadata = {
  title: "Editorial & AI policy",
  description: `How ${SITE_NAME} produces, reviews, and corrects its content, including our use of automation and AI.`,
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <div className="prose container">
      <h1>Editorial &amp; AI policy</h1>
      <p>
        <strong>{SITE_NAME}</strong> publishes short, factual briefings about search
        trends: what is trending, how large the interest is, and what verifiable
        events are behind it. This page explains exactly how that content is made —
        we believe readers deserve to know.
      </p>

      <h2>How briefings are produced</h2>
      <ul>
        <li>
          <strong>Discovery:</strong> trending search terms are collected from the
          official Google Trends RSS feeds across 8 regions.
        </li>
        <li>
          <strong>Filtering:</strong> an opportunity filter removes topics we will not
          cover: medical or financial advice, gossip about private individuals,
          gambling, adult content, and topics where coverage could cause harm. These
          rules are enforced in code, on every run.
        </li>
        <li>
          <strong>Drafting:</strong> briefings are assembled from the Google-reported
          numbers and the headlines of named news sources. When AI drafting is
          enabled, the model is instructed to only restate facts present in the cited
          sources; when it is not, a deterministic template is used with no generative
          text at all. Every briefing states which mode produced it.
        </li>
        <li>
          <strong>Review gate:</strong> nothing is published without passing a review
          gate — automated checks for source completeness, factual grounding, length,
          and policy compliance, plus an independent AI reviewer for AI-drafted
          content. Items that fail are rejected and logged, not published.
        </li>
        <li>
          <strong>Human oversight:</strong> a human editor spot-checks published
          content and the rejection log on a recurring schedule and can remove any
          item. Automation does the volume; humans own the standard.
        </li>
      </ul>

      <h2>Sourcing</h2>
      <p>
        Every briefing lists its named sources with links. Search-interest figures are
        the lower-bound estimates that Google publishes in its Trends feed — we report
        them as lower bounds, never as exact counts. We do not fabricate quotes,
        numbers, or events.
      </p>

      <h2 id="advertising">Advertising &amp; affiliation disclosure</h2>
      <p>
        This site carries one sponsored placement: <strong>{SPONSOR.name}</strong>{" "}
        (mingxinstorage.xyz). {SPONSOR.legalNote} Because of that relationship, we
        hold these placements to explicit rules, enforced in code:
      </p>
      <ul>
        <li>
          Every sponsored link is visibly labeled <em>Sponsored</em> and carries{" "}
          <code>rel=&quot;sponsored&quot;</code>, so both readers and search engines
          can tell it apart from editorial links.
        </li>
        <li>
          The contextual sponsor card appears only on briefings in the
          AI-infrastructure category, where the topic is genuinely related; it never
          appears inside editorial text or disguised as a source.
        </li>
        <li>
          Sponsor claims quote only figures the sponsor has published with
          downloadable, signed test reports on its own site. We do not invent or
          embellish numbers.
        </li>
        <li>
          Sponsorship never influences which topics we cover, the filtering rules, or
          the review gate. The editorial pipeline runs identically with or without
          the placement.
        </li>
      </ul>

      <h2 id="corrections">Corrections</h2>
      <p>
        If you find an error, open an issue on our public repository or contact the
        editor. Verified errors are corrected or the item is withdrawn, and the
        correction is noted on the page.
      </p>

      <h2>What this site is not</h2>
      <p>
        We do not provide medical, legal, investment, or safety advice. Briefings are
        news-style summaries of public information, not recommendations.
      </p>
    </div>
  );
}
