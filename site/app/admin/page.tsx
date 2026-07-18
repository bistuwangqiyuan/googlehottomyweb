import fs from "fs";
import path from "path";
import { getAllContentFilesForAudit } from "@/lib/content";

export const dynamic = "force-dynamic";

interface AuditEntry {
  runAt: string;
  keyword: string;
  geo: string;
  decision: string;
  reason: string;
  slug?: string;
}

function readAuditLog(): AuditEntry[] {
  const p = path.join(process.cwd(), "content", "audit", "pipeline_log.json");
  if (!fs.existsSync(p)) return [];
  try {
    const entries = JSON.parse(fs.readFileSync(p, "utf-8")) as AuditEntry[];
    return entries.slice(-200).reverse();
  } catch {
    return [];
  }
}

const REPO_URL =
  process.env.NEXT_PUBLIC_REPO_URL ||
  "https://github.com/bistuwangqiyuan/googlehottomyweb";
const BRANCH = process.env.NEXT_PUBLIC_REPO_BRANCH || "master";

export default function AdminPage() {
  const files = getAllContentFilesForAudit();
  const audit = readAuditLog();

  return (
    <div className="prose container">
      <h1>Spot-check console</h1>
      <p>
        人工抽检后台：下表为全部内容文件（含未通过解析的）与流水线审计日志。
        “Take down” 链接直达 GitHub 删除页——删除并提交后 Vercel 自动重新部署，
        内容即刻下架（完整审计留痕在 git 历史）。
      </p>

      <h2>Published / stored content ({files.length})</h2>
      <table className="admin">
        <thead>
          <tr>
            <th>File</th>
            <th>Title</th>
            <th>Mode</th>
            <th>Review</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map(({ file, briefing, parseError }) => (
            <tr key={file}>
              <td>{file}</td>
              <td>{briefing ? briefing.title : <span className="bad">解析失败: {parseError}</span>}</td>
              <td>{briefing?.mode ?? "-"}</td>
              <td>
                {briefing ? (
                  briefing.review?.approved ? (
                    <span className="ok">
                      approved {briefing.review.score.toFixed(2)} ({briefing.review.mode})
                    </span>
                  ) : (
                    <span className="bad">not approved（不会被站点发布）</span>
                  )
                ) : (
                  "-"
                )}
              </td>
              <td>
                {briefing && (
                  <a
                    href={`/briefings/${briefing.slug}`}
                    target="_blank"
                    rel="noopener"
                  >
                    View
                  </a>
                )}{" "}
                ·{" "}
                <a
                  href={`${REPO_URL}/delete/${BRANCH}/site/content/briefings/${file}`}
                  target="_blank"
                  rel="noopener"
                >
                  Take down
                </a>
              </td>
            </tr>
          ))}
          {files.length === 0 && (
            <tr>
              <td colSpan={5}>暂无内容文件。</td>
            </tr>
          )}
        </tbody>
      </table>

      <h2>Pipeline audit log (last {audit.length})</h2>
      <table className="admin">
        <thead>
          <tr>
            <th>Run at (UTC)</th>
            <th>Keyword</th>
            <th>Geo</th>
            <th>Decision</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {audit.map((e, i) => (
            <tr key={i}>
              <td>{e.runAt}</td>
              <td>{e.keyword}</td>
              <td>{e.geo}</td>
              <td className={e.decision === "published" ? "ok" : "bad"}>{e.decision}</td>
              <td>{e.reason}</td>
            </tr>
          ))}
          {audit.length === 0 && (
            <tr>
              <td colSpan={5}>暂无审计日志。</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
