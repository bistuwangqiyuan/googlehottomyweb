# 谷歌热词自动导流：商业机会报告与商业计划书

本项目产出两份正式对外文档，以及支撑它们的全部可复现数据与代码：

1. **商业机会挖掘与分析报告**（`opportunity-report/`）——先行确认商业机会是否成立；
2. **商业计划书**（`business-plan/`）——在机会报告结论之上编制。

## 项目主题

利用谷歌热词（Google Trends）分析 + SEO（搜索引擎优化）+ GEO（生成式引擎优化），
基于全自动软件与 AI，将搜索需求快速导流到自有网站的两阶段商业模式：

- **阶段一（自营验证）**：全自动引擎驱动自营网站组合，跑通"热词发现 → 内容生成（含编辑监督）→ SEO/GEO 优化 → 流量变现"闭环；
- **阶段二（SaaS 产品化）**：将经过实盘验证的引擎产品化，对外订阅销售。

## 目录结构

| 路径 | 内容 |
|---|---|
| `opportunity-report/` | 商业机会挖掘与分析报告（分章 Markdown；`商业机会挖掘与分析报告-完整版.md` 为七章合一的单文件版本） |
| `business-plan/` | 商业计划书（分章 Markdown，00–15 共 16 个文件；深化版新增：12 法务合规、13 前 90 天周级计划、14 成功概率与赔率；`商业计划书-完整版.md` 为合一单文件版本） |
| `scripts/` | 全部可复现 Python 脚本（数据采集、机会评分、TAM 测算、财务模型） |
| `data/` | 原始与处理后数据（CSV/JSON），每份数据附来源或生成脚本 |
| `assets/` | 由脚本自动生成的图表（PNG） |
| `SOURCES.md` | 全部外部引用来源清单（URL、访问日期、关键数据点） |

## 复现方法

```powershell
# Windows（本项目开发环境：Python 3.14.4）
py -m pip install -r requirements.txt

# 按编号顺序运行脚本，所有输出写入 data/ 与 assets/
py scripts/01_fetch_trending_now.py      # 抓取 Google Trends 实时热词（一手数据）
py scripts/02_trend_lifecycle.py         # 热词生命周期分析（Wikimedia Pageviews 开放数据）
py scripts/03_market_sizing.py           # TAM/SAM/SOM 双口径测算
py scripts/04_opportunity_scoring.py     # 机会评分模型
py scripts/05_unit_economics.py          # 单站/单篇内容单位经济
py scripts/06_financial_model.py         # 三情景 36 个月财务模型
py scripts/08_niche_selection.py         # 阶段一领域组合评分
py scripts/09_monte_carlo.py             # 蒙特卡洛 10,000 次风险量化（固定种子）

# 文档导出（可选）
py scripts/07_export_docx.py                                            # 机会报告 docx
py scripts/07_export_docx.py "business-plan/商业计划书-完整版.md" 商业计划书  # 商业计划书 docx
```

每个脚本运行结束会打印其写出的文件清单；正文中所有计算类数字均可由上述脚本复现，
所有引用类数字均可在 `SOURCES.md` 中查到出处。

## 数据诚信声明

- 有出处的数据：在正文标注来源编号，详情见 `SOURCES.md`；
- 计算得出的数据：标注生成脚本文件名，任何第三方可复现；
- 无法核实的内容：明确标注为"推测/假设"，并给出假设依据；
- 绝不编造数据。
