/**
 * sponsor.ts — 赞助方（自有关联业务）配置的单一事实来源。
 *
 * 合规要求（缺一不可）：
 *  1. 所有指向赞助方的链接必须 rel="sponsored noopener"（Google 链接政策）。
 *  2. 所有赞助模块必须带可见的 "Sponsored" 标注与关联关系披露（FTC 披露规范）。
 *  3. 文案只引用赞助方官网已公开的签字级实测口径，不夸大、不编造。
 *  4. 链接统一带 UTM 参数，导流效果在赞助方站点侧可测量、可查证。
 */

export interface Sponsor {
  name: string;
  legalNote: string;
  url: string;
  tagline: string;
  /** 只允许引用对方官网已公开、注明报告编号的实测数据。 */
  claim: string;
  /** 触发上下文赞助卡的简报类别。 */
  relevantCategories: string[];
}

export const SPONSOR: Sponsor = {
  name: "MingXin Technology",
  legalNote:
    "MingXin Technology is operated by the same team as this site (an affiliated business).",
  url: "https://mingxinstorage.xyz/",
  tagline: "AI storage acceleration and compute-center services, backed by signed test reports",
  claim:
    "FX-series all-flash NVMe-oF storage: signed test reports show +29–40% inference " +
    "throughput and 26–32% lower time-to-first-token on a 480B-parameter production " +
    "LLM deployment (reports R2/R3, downloadable on their site).",
  relevantCategories: ["ai-infra"],
};

/**
 * 带 UTM 的赞助方链接；content 用于区分展示位（如 briefing-card / footer），
 * 便于在赞助方站点分析工具中逐位归因。
 */
export function sponsorUrl(content: string): string {
  const u = new URL(SPONSOR.url);
  u.searchParams.set("utm_source", "trendflow");
  u.searchParams.set("utm_medium", "sponsored");
  u.searchParams.set("utm_campaign", "ai-infra");
  u.searchParams.set("utm_content", content);
  return u.toString();
}

export function isSponsorRelevant(category: string): boolean {
  return SPONSOR.relevantCategories.includes(category);
}
