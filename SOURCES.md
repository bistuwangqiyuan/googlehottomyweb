# 引用来源清单（SOURCES）

本清单收录报告与商业计划书中全部外部引用。格式：编号、来源、访问日期、关键数据点、链接。
计算类数字不在此列——它们由 `scripts/` 下对应脚本生成，可复现。

## A. AI 搜索对自然流量的影响（需求侧核心证据）

- **[S1]** Seer Interactive, "AIO Impact on Google CTR: 2026 Update"（2026-04 发布；访问 2026-07-14）
  - 样本：53 个品牌、547 万查询、24.3 亿次自然展现，2025-01 至 2026-02 共 14 个月
  - 出现 AI Overview 时自然 CTR：2025-01 为 3.19% → 2025-12 最低 1.31% → 2026-02 回升至 2.36%
  - 无 AI Overview 查询的自然 CTR：2026-02 为 3.82%
  - 被 AI Overview 引用的品牌 CTR ≈ 2.1%，未被引用 ≈ 0.9%（2.3 倍差距）
  - AI Overview 出现率按意图：信息类 ~36%、交易类 ~5%、对比类 ~95%、问句类 ~86%
  - https://www.seerinteractive.com/insights/aio-impact-on-google-ctr-2026-update
- **[S2]** Search Engine Land, "Google AI Overviews CTR shows early signs of recovery: Study"（2026；访问 2026-07-14）
  - 对 S1 的第三方转述与核对：无 AIO ≈ 3.3% CTR；有 AIO 且被引用 ≈ 2.1%；有 AIO 未被引用 ≈ 0.9%
  - https://searchengineland.com/google-ai-overviews-ctr-recovery-study-475566
- **[S3]** Ahrefs 研究（经 almcorp.com 2026 年综述转引；访问 2026-07-14）
  - 30 万关键词 + Search Console 聚合数据：AI Overview 出现与排名第一页面的平均 CTR 下降约 58% 相关（截至 2025-12）
  - https://almcorp.com/blog/google-ai-overviews-organic-ctr-2026/
- **[S4]** Pew Research Center（经 Contently 2026-04-27 综述转引；访问 2026-07-14）
  - 出现 AI 摘要时用户点击传统结果的比例为 8%，无摘要时为 15%；点击 AI 摘要内链接的比例仅 1%
  - 约 83% 带 AI Overview 的搜索以零点击结束；2026 年 Q1 约 25.11% 的 Google 搜索触发 AI Overview（2190 万搜索样本）
  - AI 渠道访客转化率约为其他渠道的 3 倍，单访客价值约为传统自然访客的 4.4 倍
  - https://contently.com/2026/04/27/ai-overview-traffic-impact/

## B. Google 反垃圾政策（合规硬约束）

- **[S5]** Google Search Central Blog, "What web creators should know about our March 2024 core update and new spam policies"（2024-03；访问 2026-07-14）
  - 定义 Scaled Content Abuse（规模化内容滥用）：不论由 AI、人工或混合方式产生，凡以操纵排名为主要目的、对用户无附加价值的批量内容均属违规
  - 同时推出 Site Reputation Abuse（站点声誉滥用）与 Expired Domain Abuse（过期域名滥用）政策
  - https://developers.google.com/search/blog/2024/03/core-update-spam-policies
- **[S6]** Google Search Central Blog, "Updating our site reputation abuse policy"（2024-11，2025-01 措辞更新；访问 2026-07-14）
  - 明确：无论是否有第一方参与监督，凡利用宿主站排名信号发布第三方内容以操纵排名均违规
  - https://developers.google.com/search/blog/2024/11/site-reputation-abuse
- **[S7]** Digital Applied, "Scaled Content Abuse: Google's AI Page Crackdown Guide"（2026；访问 2026-07-14）
  - 2026 年 3 月核心更新将规模化内容滥用列为首要打击目标；无编辑监督的批量 AI 页面站点流量下降 50–80%
  - 政策打击的是"无价值的薄内容"，而非 AI 工具本身
  - https://www.digitalapplied.com/blog/scaled-content-abuse-google-march-update-ai-pages-decimated
- **[S8]** Search Engine Land, "Google begins enforcement of site reputation abuse policy..."（2024-05；访问 2026-07-14）
  - CNN、USA Today、Fortune、LA Times 等大站的优惠券目录被人工处罚移出相关排名
  - https://searchengineland.com/google-begins-enforcement-of-site-reputation-abuse-policy-with-portions-of-sites-being-delisted-440294

## C. 市场规模（供给侧）

- **[S9]** Precedence Research, "SEO Software Market Size"（访问 2026-07-14）
  - 2025 年全球 SEO 软件市场 849.4 亿美元；2026 年 964.2 亿；预测 2035 年 2950.4 亿，CAGR 13.26%（2026–2035）
  - https://www.precedenceresearch.com/seo-software-market
- **[S10]** The Insight Partners, "SEO Software Market"（访问 2026-07-14）
  - 2025 年 863.4 亿美元；预测 2034 年 1584.7 亿，CAGR 7.89%（2026–2034）
  - https://www.theinsightpartners.com/reports/seo-software-market
- **[S11]** Fortune Business Insights, "SEO Software Market"（访问 2026-07-14）
  - 2025 年 859.7 亿美元；2026 年 977 亿；预测 2034 年 2719 亿，CAGR 13.65%
  - https://www.fortunebusinessinsights.com/seo-software-market-114540
- **[S12]** MarketIntelo, "Generative Engine Optimization (GEO) Market Research Report 2034"（访问 2026-07-14）
  - GEO 市场 2025 年 8.48 亿美元；预测 2034 年 198 亿，CAGR 50.5%；北美占 42.5%；SaaS 部署占 60%
  - 2026 年初生成式引擎月处理 AI 查询超 150 亿次，年同比翻倍
  - https://marketintelo.com/report/generative-engine-optimization-geo-market
- **[S13]** ResearchIntelo, "AI Generative Search Optimization (GEO/AEO) Platforms Market"（访问 2026-07-14）
  - GEO/AEO 平台市场 2025 年 8.50 亿美元；预测 2034 年 121 亿，CAGR 38.5%；头部厂商：Profound、BrightEdge、Semrush、Conductor
  - https://researchintelo.com/report/ai-generative-search-optimization-geoaeo-platforms-market

## D. 一手数据（本项目脚本直接采集）

- **[D1]** Google Trends "Trending Now" RSS（`scripts/01_fetch_trending_now.py` 采集，原始快照存 `data/`）
  - https://trends.google.com/trending/rss?geo=US
- **[D2]** Wikimedia Pageviews REST API（`scripts/02_trend_lifecycle.py` 采集，开放许可 CC0）
  - https://wikimedia.org/api/rest_v1/

## E. 变现基准（广告 / 联盟）

- **[S14]** EarnifyHub, "Blog Display Ad RPM by Niche 2026"（基于 450+ 博客 2025-01 至 2026-03 数据；访问 2026-07-14）
  - 各细分领域每千次会话广告收入（Session RPM）：个人理财 $15–40（前 10% 达 $55+）、科技/SaaS $12–35、健康 $10–28、美食 $8–20、旅行 $6–18、生活方式 $4–12、娱乐/名人 $3–7
  - AdSense $3–12（无流量门槛）；Ezoic $8–20（1 万会话门槛）；Mediavine $15–40+（5 万会话门槛）；Raptive $18–50+（10 万门槛）
  - 非美英加澳流量 RPM 低 50–80%
  - https://earnifyhub.com/blog/blogging/blog-display-ad-rpm-by-niche-2026
- **[S15]** Hakaru 博客广告收入计算器（2026；访问 2026-07-14）
  - AdSense 约 $5–15 RPM、Mediavine $15–30、Raptive $20–40（按千次页面浏览）
  - https://hakaru.io/tools/blog-ad-revenue-calculator
- **[S16]** MonetizationGuy, "Session RPM Explained"（2026；访问 2026-07-14）
  - 新闻/时事类 $3–8、娱乐/名人 $3–7、游戏 $2–6；Google 已于 2025-09 在 AdSense 中停用会话类指标
  - https://monetizationguy.com/minis/so-what-exactly-is-session-rpm
- **[S17]** AffiliateBooster, "2026 State of Affiliate Marketing Report"（数据源含 eMarketer/Statista/Rakuten/Awin；访问 2026-07-14）
  - 全球联盟营销支出 2025 年超 170 亿美元，2026 年预计 200.7 亿；美国 2026 年 132 亿（+10.1%）
  - Amazon Associates 占全球市场 46.6%；AI 搜索来源访客转化率约 14%（传统 Google 约 2.8%，近 5 倍溢价）
  - Google AI Overviews 与发布商引荐流量下降 25% 相关
  - https://www.affiliatebooster.com/state-of-affiliate-marketing-report/
- **[S18]** Track360, "Affiliate Marketing Industry Statistics 2026"（访问 2026-07-14）
  - 全行业平均佣金率 8.3%（Performance Marketing Association 2025 调查）；头部 10% 联盟客贡献 67% 收入（Forrester）
  - https://track360.io/blog/affiliate-marketing-industry-statistics-2026
- **[S19]** Digital Applied, "Affiliate Marketing Statistics 2026"（Forrester 2026 预测转引；访问 2026-07-14）
  - 全球联盟支出 2026 年 194 亿美元（2025 年 171 亿）；北美占 47%；Amazon Associates 标准佣金按类目 1–10%，Cookie 窗口 24 小时
  - https://www.digitalapplied.com/blog/affiliate-marketing-statistics-2026-data-points

## F. 竞品定价与融资

- **[S20]** Exploding Topics 定价（Semrush 官方知识库 + 官网 API 页；访问 2026-07-14）
  - Entrepreneur $39/月、Investor $99/月、Business $249/月；API 加购：1K 请求 $1,000/月、5K $2,000/月、25K $4,000/月（仅 Business 可加购）
  - https://www.semrush.com/kb/1490-exploding-topics ；https://explodingtopics.com/feature/et-api
- **[S21]** Glimpse（Google Trends 增强工具）：付费版约 $71/月起（年付）（maxaeo.ai 等第三方评测；访问 2026-07-14）
- **[S22]** Ahrefs 官网定价（访问 2026-07-14）
  - Starter $29/月、Lite $129/月、Standard $249/月、Advanced $449/月、Enterprise $1,499/月起；年付省约 17%
  - https://ahrefs.com/pricing
- **[S23]** Semrush 定价（allable.ai 汇总 + 官网；访问 2026-07-14）
  - Pro $139.95/月、Guru $249.95/月、Business $499.95/月；新 Semrush One AI 系列 $199–549/月
  - https://www.allable.ai/blog/semrush-pricing/
- **[S24]** GEO/AEO 工具定价与融资（aeoguide.io、nboundmarketing.com、surmado.com、thenextscoop.com 交叉；访问 2026-07-14）
  - Profound：Starter $99/月、Growth $399/月、Enterprise $2,000–5,000+/月；累计融资 1.55 亿美元，2026-02 以 10 亿美元估值完成 9,600 万美元 C 轮（Lightspeed 领投），成立 18 个月即成独角兽
  - Peec AI：€89/月起，Pro €199/月；融资 2,910 万美元，10 个月 ARR 超 400 万美元，2025-11 估值超 1 亿美元
  - Otterly AI：$29/月起（15 提示词）、$189/月（100）、$489/月（400）
  - 赛道 2025 夏至 2026 春合计融资超 3 亿美元（Surmado 统计）
  - https://aeoguide.io/peec-ai-vs-otterly-ai-vs-profound/
- **[S25]** Surfer SEO $49–299/月（文档量计费）；Jasper AI $49/月起（stackscored.com 2026-04-21 核价；访问 2026-07-14）
  - https://www.stackscored.com/pricing/seo-tools/

## G. 成本侧（LLM API 与基础设施）

- **[S26]** benchr.org / presenc.ai LLM API 价格汇总（2026-05 采集自官方文档；访问 2026-07-14）
  - 旗舰层：GPT-5.5 $5/$30（每百万输入/输出 token）、Claude Opus 4.8 $5/$25、Gemini 3.1 Pro $2/$12
  - 中间层：Claude Sonnet 4.6 $3/$15、GPT-5 $1.25/$10、Gemini 3.5 Flash $1.5/$9
  - 经济层：GPT-4.1 Nano $0.1/$0.4、Gemini 2.5 Flash-Lite $0.1/$0.4、DeepSeek V4-Flash $0.14/$0.28
  - 提示缓存折扣 75–90%；批处理 API 约 5 折
  - https://benchr.org/articles/ai-model-pricing-comparison ；https://presenc.ai/research/llm-api-pricing-comparison-2026

## H. 目标客户基数（自下而上 TAM）

- **[S27]** SBA / USAFacts（经 renowebdesigner.com 2026-02 研究汇编转引；访问 2026-07-14）
  - 美国小企业约 3,620 万家（SBA 2025-06）；其中雇主企业约 627 万家；78% 报告开展某种形式的 SEO；39% 以某种形式向机构付费购买 SEO 服务
  - https://renowebdesigner.com/wp-content/uploads/2026/02/SEO_vs_Paid_Ads_US_Small_Businesses_Research.pdf
- **[S28]** Content Master 市场测算（引 World Bank/IFC 口径；访问 2026-07-14）
  - 全球小企业约 3.5–4 亿家；全球广告与营销机构约 43.7 万家（2024）
  - https://contentmaster.ca/investor-resources/how-big-is-the-opportunity-market-sizing-breakdown/
- **[S29]** QuickSEO, "State of the SEO Agency Industry 2026"（IBISWorld/Backlinko/SE Ranking/Ahrefs 调查转引；访问 2026-07-14）
  - 美国 SEO/网络营销咨询公司约 36.3 万家；机构平均月度服务费 $3,209（Ahrefs 439 家调查）；美国 SMB 平均月度 SEO 支出 $497（Backlinko 1,200 家调查）；64% 机构收费低于 $1,000/月
  - 全球 SEO 服务（机构口径）2026 年约 878.2 亿美元（Research and Markets）
  - https://quickseo.ai/blog/the-state-of-the-seo-agency-industry-in-2026-50-stats
- **[S30]** BrightLocal, "SMB Marketing Report 2025"（778 家 SMB 调查；访问 2026-07-14）
  - 72% SMB 认为 SEO 影响中高；但仅 40% 拥有独立网站——存在巨大"想做而无能力做"缺口
  - https://www.brightlocal.com/research/smb-marketing-2025/

## I. GEO/AI Overview 引用因子（产品工艺依据）

- **[S31]** Link Building Journal, "How Google AI Overviews Choose Cited Pages: A Data-Backed 2026 Study"（抽样 1,000 个 AI Overview、30 个垂直领域；访问 2026-07-14）
  - 语义完整度（主题覆盖深度）与引用呈 r=0.87 相关；评分 8.5+/10 的页面被引用频率高 4.2 倍
  - Schema 标记（FAQPage/HowTo/Article/Product）页面被引用率为无标记页面的 2.3 倍
  - 多模态内容（文+图+视频）入选率高 156%；E-E-A-T 强的第 6–10 名页面被引用率为 E-E-A-T 弱的第 1 名的 2.3 倍
  - 直接答案结构（每节前 50 词即答案）与片段抽取强相关；域级主题簇覆盖是最强单一预测因子
  - https://linkbuildingjournal.co.uk/how-google-ai-overviews-choose-cited-pages/
- **[S32]** GenerateMore.ai 综述（汇总 Digital Applied 千例研究、grounding-chunks 逆向分析；访问 2026-07-14）
  - 引用单位是"句子"而非页面：高密度、自足、事实具体的句子最易被整句提取
  - 长文（2,500 词+）引用率 +1.6 倍；正文内具名来源 +2.1 倍；YMYL 领域需自然排名前 10 才有引用资格
  - https://generatemore.ai/blog/how-to-get-visibility-on-google-ai-overviews-and-ai-mode
- **[S33]** RankScope, "How to Rank in Google AI Overviews (2026)"（访问 2026-07-14）
  - 可执行规范：每个 H2/H3 首句直接作答（40–60 词自足答案）、对比内容表格化、主张附具体数字与来源、至少一项原创数据
  - https://rankscope.ai/blog/how-to-rank-in-ai-overviews
- **[S34]** SEOcrawl, "AI Overviews Ranking Factors (2026)"（访问 2026-07-14）
  - 96% 的 AI Overview 引用来自可验证的权威来源；2025-12 核心更新后 E-E-A-T 要求从 YMYL 扩展到全部内容类别
  - https://seocrawl.ai/blog/ai-overview-ranking-factors

## J. 内容站退出估值（止损残值依据）

- **[S35]** Empire Flippers（2025 年中数据披露；访问 2026-07-14）
  - 内容站平均成交倍数：2024 年约 27 倍月净利 → 2025 年约 24 倍（连续三年下行后的理性定价）
  - 2025 年上半年约 30 笔内容站交易，平均成交价约 $325K；买家对 Google 算法与 AI 侵蚀风险显著更谨慎
  - https://empireflippers.com/you-can-sell-your-business-for-life-changing-money-in-2025-heres-the-secret/
- **[S36]** Empire Flippers, "2026 State of the Industry Report"（访问 2026-07-14）
  - 全市场平均成交价 $272K；展示广告类占成交量 13.3%（第二大类）；结论：内容站作为独立资产的收购风险上升，买家更青睐可转型（电商/数字产品/服务）或有协同的标的
  - https://info.empireflippers.com/hubfs/2026%20Lead%20Magnets/2026%20State%20of%20the%20Industry%20Report.pdf
- **[S37]** Organic Arbitrage 汇总（访问 2026-07-14）
  - 展示广告站 28–38 倍月净利、联盟站 26–42 倍、下滑期站点仅 12–20 倍；估值基线为过去 12 个月平均净利
  - https://organicarbitrage.com/articles/revenue-multiple-valuation-seo-sites

## K. SMB SaaS 经营基准（H15/H16 校准）

- **[S38]** Optifai Pipeline Study（N=939 家 B2B SaaS，2025Q2–2026Q1；访问 2026-07-14）
  - SMB（ACV<$10K）月流失 3–5%；SMB CAC 回收期 8–12 个月为基准、<12 个月为优
  - https://optif.ai/learn/questions/b2b-saas-churn-rate-benchmark/
- **[S39]** NoNoise Metrics 汇编（Recurly/OpenView/Bessemer/SaaS Capital 2024 口径；访问 2026-07-14）
  - 低 ARPU（<€50）SMB SaaS 月流失 3–5%、年流失 30–50%；LTV:CAC 健康区间 3:1–5:1
  - https://blog.nonoisemetrics.com/saas-benchmarks-2026/
- **[S40]** 2026 SaaS Benchmarks Report（Ryan Allis 汇编；访问 2026-07-14）
  - SMB SaaS（月流失 3–7%）必须依赖低 CAC 渠道（自助/PLG/内容/SEO），CAC 须控制在 $600 以下；LTV:CAC 全体私营中位数 3.3
  - https://www.linkedin.com/pulse/2026-saas-benchmarks-report-ryan-allis-14kbf
  - **校准结论**：本项目 H15（月流失 4.5%）落在 SMB 基准带中位，H16（CAC $350，内容驱动）低于 $600 红线且与内容获客模式一致——两项假设经外部基准验证，维持不变

## L. 法务合规（美国联邦 + 数据隐私 + 版权）

- **[S41]** FTC Endorsement Guides（16 CFR Part 255，2023 年修订；访问 2026-07-14）
  - 联盟佣金属"重大关联"，必须在推荐内容与链接可同屏看到处清晰醒目披露（如 "I get commissions for purchases made through links in this post"）；页脚统一声明不合规
  - https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking
- **[S42]** FTC Consumer Reviews and Testimonials Rule（2024 年定案；经 terms.law/digitalapplied 转述核对；访问 2026-07-14）
  - 禁止虚假/AI 生成的用户评价与体验声明，违者可处民事罚款；AI 参与撰写的推广内容仍须满足真实性与披露要求
  - https://terms.law/2025/12/05/sponsorships-affiliates-ai-disclosure-rules-creators-cant-ignore/
- **[S43]** 美国版权局立场（经多来源交叉；访问 2026-07-14）
  - 纯 AI 生成作品不受版权保护，仅人类创作部分可登记；登记时须披露超过最低限度的 AI 生成内容
  - 经营含义：本项目内容资产的可保护性依赖人工编辑参与的实质性（编辑关口的第二重价值）
- **[S44]** GDPR/CCPA 对内容站的最小合规集（行业法务指引汇总；访问 2026-07-14）
  - 隐私政策 + Cookie 同意横幅（欧盟流量）+ 数据退出/删除通道；只要触达欧盟/加州用户即适用，与经营者所在地无关
  - https://affiliatemarketingclues.com/legal-guidelines-for-affiliate-marketers-how-to-stay-compliant-in-2025/

## M. 客户痛点一手证据（竞品公开评价归纳）

- **[S45]** Jasper 用户评价归纳（G2 1,270 条 4.7 分口径 + Reddit/Trustpilot/Capterra 负面主题；多家评测站交叉；访问 2026-07-14）
  - 高频抱怨：输出"generic/cookie-cutter"需大量人工编辑；价格 $49–69/席被认为不敌 ChatGPT $20（42% 用户提及价格顾虑）；SEO 能力需另购 Surfer（≈$75/月）叠加；计费/退订纠纷多
  - 用户流向：回退到裸用 ChatGPT/Claude + 自建提示词
  - https://autoposting.ai/blog/jasper-review ；https://www.eyesift.com/blog/jasper-ai-review/
- **[S46]** Surfer SEO 批评归纳（访问 2026-07-14）
  - 相关性打分法被指鼓励堆词与过度优化；AI 额度另收费；无发布与效果闭环
  - **痛点综合**：现有工具栈是"多件单点工具叠订阅"（写作 $49 + 优化 $75 + 热词 $39…），且都停在"草稿"环节——从选题到发布到效果验证的闭环缺失，正是本产品定位的空位证据

> 注：E–H 节中 earnifyhub、hakaru、monetizationguy、track360、dollarpocket、aeoguide 等属行业博客/工具站，
> 其数据为运营者调查或聚合口径，精度低于官方财报；正文引用时均以"区间"呈现并注明口径限制。
> Mediavine（5 万会话）与 Raptive（有说 2.5 万页面浏览/有说 10 万会话）门槛在不同来源存在出入，
> 正文采用保守口径：Mediavine 50K 会话、Raptive 100K 页面浏览。
