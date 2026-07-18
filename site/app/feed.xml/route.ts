import { getAllBriefings, SITE_NAME, SITE_TAGLINE, siteUrl } from "@/lib/content";

export const dynamic = "force-static";

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export async function GET() {
  const base = siteUrl();
  const items = getAllBriefings()
    .slice(0, 50)
    .map(
      (b) => `    <item>
      <title>${esc(b.title)}</title>
      <link>${base}/briefings/${b.slug}</link>
      <guid isPermaLink="true">${base}/briefings/${b.slug}</guid>
      <pubDate>${new Date(b.publishedAt).toUTCString()}</pubDate>
      <description>${esc(b.description)}</description>
    </item>`
    )
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>${esc(SITE_NAME)}</title>
    <link>${base}</link>
    <description>${esc(SITE_TAGLINE)}</description>
    <language>en</language>
${items}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: { "Content-Type": "application/rss+xml; charset=utf-8" },
  });
}
