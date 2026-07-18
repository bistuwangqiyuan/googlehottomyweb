import type { MetadataRoute } from "next";
import { getAllBriefings, siteUrl } from "@/lib/content";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteUrl();
  const briefings = getAllBriefings().map((b) => ({
    url: `${base}/briefings/${b.slug}`,
    lastModified: new Date(b.updatedAt),
    changeFrequency: "daily" as const,
    priority: 0.8,
  }));
  return [
    { url: base, lastModified: new Date(), changeFrequency: "hourly", priority: 1 },
    { url: `${base}/about`, changeFrequency: "monthly", priority: 0.4 },
    { url: `${base}/privacy`, changeFrequency: "yearly", priority: 0.2 },
    ...briefings,
  ];
}
