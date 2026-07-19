import { SPONSOR, sponsorUrl } from "@/lib/sponsor";

/**
 * 上下文赞助卡：只在 ai-infra 类简报页渲染（由调用方用 isSponsorRelevant 判断）。
 * 可见 "Sponsored" 标注 + 关联关系披露 + rel="sponsored"，缺一不可。
 */
export default function SponsorCard() {
  return (
    <aside className="sponsor-card" data-testid="sponsor-card">
      <span className="badge sponsor-badge">Sponsored · Affiliated</span>
      <h2>
        <a
          href={sponsorUrl("briefing-card")}
          rel="sponsored noopener"
          target="_blank"
        >
          {SPONSOR.name}
        </a>{" "}
        — {SPONSOR.tagline}
      </h2>
      <p>{SPONSOR.claim}</p>
      <p className="sponsor-disclosure">
        Disclosure: {SPONSOR.legalNote} This placement appears only on
        AI-infrastructure briefings and is always labeled. See our{" "}
        <a href="/about#advertising">advertising &amp; affiliation policy</a>.
      </p>
    </aside>
  );
}
