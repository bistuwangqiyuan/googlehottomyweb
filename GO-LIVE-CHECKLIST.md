# GO-LIVE 清单（合计约 10 分钟人工操作）

系统已全部开发并在本地生产模式通过全套 E2E 测试（见 `VERIFICATION-REPORT.md`）。
以下 3 项涉及账号与付款，是**仅有的人工环节**；每项完成后，其余全部由脚本自动执行。

## 人工步骤 1：Vercel 登录（约 3 分钟）

1. 访问 https://vercel.com/signup 用 GitHub 账号注册/登录（免费 Hobby 计划即可）；
2. 本机执行：

```powershell
npm install -g vercel
vercel login          # 浏览器确认即可
```

（或在 https://vercel.com/account/tokens 创建 token 并 `$env:VERCEL_TOKEN = "..."`，全程免交互。）

## 人工步骤 2：Porkbun 充值 + API key（约 5 分钟）

1. 注册 https://porkbun.com 并完成邮箱/手机验证；
2. 账户充值 $2（Account → Billing → Add Funds）；
3. 在 https://porkbun.com/account/api 创建 API key，记下 key 与 secret：

```powershell
$env:PORKBUN_API_KEY    = "pk1_..."
$env:PORKBUN_SECRET_KEY = "sk1_..."
```

> 注意：Porkbun 要求账户**至少有过一次注册订单**才能用 API 注册域名。
> 若是全新账户，先在网页上注册选定域名（脚本 `--dry-run` 会告诉你哪个可用、多少钱），
> 之后 DNS/绑定仍由脚本完成。

## 人工步骤 3：LLM key —— ✅ 已完成（2026-07-19）

已配置为 AI 成稿 + 独立第二模型审核 + 宕机降级链（探测记录
`data/llm_provider_probe.json`，任何人可用自己的 key 重跑
`scripts/13_llm_provider_probe.py` 复现选型）：

| Secret | 当前值 | 角色 |
|---|---|---|
| `LLM_API_KEY/_BASE_URL/_MODEL` | 智谱 `glm-4.6` | 成稿主力 |
| `LLM_FALLBACK_*` | 月之暗面 `moonshot-v1-32k` | 成稿备用 |
| `REVIEW_API_KEY/_BASE_URL/_MODEL` | 通义 `qwen-max` | 独立审核（与成稿不同厂商） |
| `REVIEW_FALLBACK_*` | 月之暗面 `moonshot-v1-32k` | 审核备用 |

全链失败时：生成回退确定性简报模板（零编造），LLM 内容审核 fail-closed 拒发。

## 凭据就位后：一条命令上线

```powershell
# 1. 部署站点（≈1 分钟）
powershell -File deploy/deploy.ps1

# 2. 注册 <$2 域名 + 配 DNS + 绑定 Vercel（≈2 分钟；先 --dry-run 预检不扣费）
python deploy/register_domain.py --dry-run
python deploy/register_domain.py

# 3. 对真实域名跑同一套 E2E（生产环境测试闭环）
python tests/e2e_site.py --base-url https://<你的域名>
```

## 上线后自动运行的部分（无需任何操作）

- GitHub Actions 每 6 小时运行内容流水线（`.github/workflows/content-pipeline.yml`），
  新内容自动提交 → Vercel 检测到推送自动重新构建部署；
- 每周花 10 分钟访问 `https://<域名>/admin`（Basic Auth，凭据即部署时设置的
  `ADMIN_USER`/`ADMIN_PASS`）抽检内容与审计日志，发现问题一键下架。

## 费用核对（2026-07-18 通过 Porkbun 公开 API 实测）

| 项目 | 费用 |
|---|---|
| Vercel Hobby | $0 |
| GitHub Actions（公开仓库） | $0 |
| 域名（.bond $1.34 / .sbs $1.54 / .click $1.54 / .top $1.63 首年；1.111B 数字 .xyz $0.99 含续费） | < $2/年 |
| LLM（可选，简报模式为 $0） | 按用量 |
