import fs from "fs";
import path from "path";

export interface Source {
  title: string;
  url: string;
  source: string;
}

export interface Section {
  heading: string;
  paragraphs: string[];
  list?: string[];
}

export interface FaqItem {
  q: string;
  a: string;
}

export interface Review {
  approved: boolean;
  score: number;
  mode: "rules" | "llm";
  notes: string;
  reviewedAt: string;
}

export interface Briefing {
  slug: string;
  title: string;
  description: string;
  keyword: string;
  geo: string;
  trafficLowerBound: number | null;
  category: string;
  mode: "briefing" | "llm";
  publishedAt: string;
  updatedAt: string;
  sources: Source[];
  sections: Section[];
  faq: FaqItem[];
  review: Review;
}

const CONTENT_DIR = path.join(process.cwd(), "content", "briefings");

export function getAllBriefings(): Briefing[] {
  if (!fs.existsSync(CONTENT_DIR)) return [];
  const files = fs.readdirSync(CONTENT_DIR).filter((f) => f.endsWith(".json"));
  const briefings: Briefing[] = [];
  for (const file of files) {
    try {
      const raw = fs.readFileSync(path.join(CONTENT_DIR, file), "utf-8");
      const b = JSON.parse(raw) as Briefing;
      // 合规护栏：只发布通过审核关口的内容
      if (b.review && b.review.approved) briefings.push(b);
    } catch {
      // 跳过损坏文件；审计入口在 /admin 可见
    }
  }
  briefings.sort((a, b) => (a.publishedAt < b.publishedAt ? 1 : -1));
  return briefings;
}

export function getBriefing(slug: string): Briefing | null {
  const all = getAllBriefings();
  return all.find((b) => b.slug === slug) ?? null;
}

export function getAllContentFilesForAudit(): {
  file: string;
  briefing: Briefing | null;
  parseError: string | null;
}[] {
  if (!fs.existsSync(CONTENT_DIR)) return [];
  const files = fs.readdirSync(CONTENT_DIR).filter((f) => f.endsWith(".json"));
  return files.map((file) => {
    try {
      const raw = fs.readFileSync(path.join(CONTENT_DIR, file), "utf-8");
      return { file, briefing: JSON.parse(raw) as Briefing, parseError: null };
    } catch (e) {
      return { file, briefing: null, parseError: String(e) };
    }
  });
}

export const SITE_NAME = "TrendFlow Briefings";
export const SITE_TAGLINE =
  "Fact-checked briefings on what the world is searching for — tech, products, and the events behind the spikes.";

export function siteUrl(): string {
  return (
    process.env.NEXT_PUBLIC_SITE_URL ||
    (process.env.VERCEL_PROJECT_PRODUCTION_URL
      ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
      : "http://localhost:3000")
  );
}
