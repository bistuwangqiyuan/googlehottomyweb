# 谷歌热词自动导流：商业机会报告与商业计划书

本项目产出两份正式对外文档，以及支撑它们的全部可复现数据与代码：

1. **商业机会挖掘与分析报告**（`opportunity-report/`）——先行确认商业机会是否成立；
2. **商业计划书**（`business-plan/`）——在机会报告结论之上编制。

## 项目主题

利用谷歌热词（Google Trends）分析 + SEO（搜索引擎优化）+ GEO（生成式引擎优化），
基于全自动软件与 AI，将搜索需求快速导流到自有网站的两阶段商业模式：

- **阶段一（自营验证）**：全自动引擎驱动自营网站组合，跑通"热词发现 → 内容生成（含编辑监督）→ SEO/GEO 优化 → 流量变现"闭环；
- **阶段二（SaaS 产品化）**：将经过实盘验证的引擎产品化，对外订阅销售。

## 阶段一首站已上线（TrendFlow）

按计划书阶段一方案实现的首站 MVP 已部署到真实生产环境：**https://trendflow-site.vercel.app**
（151 项 E2E 断言在真实线上 URL 全部通过，详见 `VERIFICATION-REPORT.md` 第二部分）。

```powershell
python -m pip install -r pipeline/requirements.txt
python -m pipeline.run_pipeline        # 真实抓取 8 国热词→过滤→生成→审核→发布
python tests/test_pipeline_unit.py     # 流水线单元测试（18 项）
python tests/e2e_site.py               # 本地生产模式全套 E2E（需先 cd site && npm install）
python tests/e2e_site.py --base-url https://trendflow-site.vercel.app   # 对线上跑同一套
```

上线自动化与仅剩的人工步骤（域名付款、可选 LLM key）见 `GO-LIVE-CHECKLIST.md`。

## 目录结构

| 路径 | 内容 |
|---|---|
| `opportunity-report/` | 商业机会挖掘与分析报告（分章 Markdown；`商业机会挖掘与分析报告-完整版.md` 为七章合一的单文件版本） |
| `business-plan/` | 商业计划书（分章 Markdown，编号 00–14 共 15 章；深化版新增：11 法务合规、12 前 90 天周级计划、13 成功概率与赔率；`商业计划书-完整版.md` 为合一单文件版本，共 16 个 md 文件） |
| `scripts/` | 全部可复现 Python 脚本（数据采集、机会评分、TAM 测算、财务模型） |
| `data/` | 原始与处理后数据（CSV/JSON），每份数据附来源或生成脚本 |
| `assets/` | 由脚本自动生成的图表（PNG） |
| `SOURCES.md` | 全部外部引用来源清单（URL、访问日期、关键数据点） |
| `pipeline/` | TrendFlow 内容流水线（抓取→合规过滤→双模式生成→审核关口→发布），GitHub Actions 每 6 小时运行 |
| `site/` | TrendFlow 站点（Next.js 15，SEO/GEO 双轨优化 + 合规披露 + `/admin` 抽检后台） |
| `tests/` | 流水线单元测试 + E2E 套件（本地/线上同一套断言） |
| `deploy/` | 一键部署脚本（Vercel）与 <$2/年域名自动注册脚本（Porkbun，支持 dry-run） |

## 复现方法

```powershell
# Windows（要求 Python >= 3.10；本项目经 Python 3.12.10 实测验证）
python -m pip install -r requirements.txt

# 按编号顺序运行脚本，所有输出写入 data/ 与 assets/
python scripts/01_fetch_trending_now.py  # 抓取 Google Trends 实时热词（一手数据）
python scripts/02_trend_lifecycle.py     # 热词生命周期分析（Wikimedia Pageviews 开放数据）
python scripts/03_market_sizing.py       # TAM/SAM/SOM 双口径测算
python scripts/04_opportunity_scoring.py # 机会评分模型
python scripts/05_unit_economics.py      # 单站/单篇内容单位经济
python scripts/06_financial_model.py     # 三情景 36 个月财务模型（读取 05 的单位经济输出）
python scripts/08_niche_selection.py     # 阶段一领域组合评分
python scripts/09_monte_carlo.py         # 蒙特卡洛 10,000 次风险量化（固定种子，读取 05 输出）

# 文档导出（可选）
python scripts/07_export_docx.py                                            # 机会报告 docx
python scripts/07_export_docx.py "business-plan/商业计划书-完整版.md" 商业计划书  # 商业计划书 docx
```

每个脚本运行结束会打印其写出的文件清单；正文中所有计算类数字均可由上述脚本复现，
所有引用类数字均可在 `SOURCES.md` 中查到出处。

## 自动化验证（一条命令核验全部数字）

本仓库自带两个验证脚本，任何第三方可自动核验"可复现"承诺：

```powershell
# 1) 复现性验证：重跑全部计算脚本，断言输出与仓库数据逐数值一致
python scripts/10_verify_reproducibility.py              # 全量（含联网脚本，最慢）
python scripts/10_verify_reproducibility.py --offline    # 仅离线确定性脚本（<1 分钟）

# 2) 文档一致性核对：正文中 80+ 条关键数字逐条与 data/ 脚本输出比对
python scripts/11_verify_doc_consistency.py
```

两个脚本退出码为 0 即全部通过。验证分级如实声明：确定性脚本（03–06、08、09）
要求逐数值精确一致；01（实时热词）结果随时点变化，验证"方法可复现"并保留
2026-07-14 快照为审计基线；02（Wikimedia 历史数据）要求精确复现。

## 数据诚信声明

- 有出处的数据：在正文标注来源编号，详情见 `SOURCES.md`；
- 计算得出的数据：标注生成脚本文件名，任何第三方可复现；
- 无法核实的内容：明确标注为"推测/假设"，并给出假设依据；
- 绝不编造数据。
