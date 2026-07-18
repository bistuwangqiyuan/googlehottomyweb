# deploy.ps1 - One-command production deploy of the TrendFlow site to Vercel.
#
# Prerequisites (one-time, see GO-LIVE-CHECKLIST.md):
#   1. vercel login   (or set $env:VERCEL_TOKEN)
#   2. Optional: $env:ADMIN_USER / $env:ADMIN_PASS for the /admin spot-check console
#
# Usage:
#   powershell -File deploy/deploy.ps1            # production deploy
#   powershell -File deploy/deploy.ps1 -DryRun    # environment checks only, no deploy

param(
    [switch]$DryRun
)

# Native commands (vercel/npm) write progress to stderr; with "Stop" preference
# PowerShell 5.1 would turn that into a terminating error, so stay on "Continue"
# and check $LASTEXITCODE explicitly after each native call.
$ErrorActionPreference = "Continue"
$SiteDir = Join-Path $PSScriptRoot "..\site"

function Fail([string]$msg) {
    Write-Host "ERROR: $msg"
    exit 1
}
$TokenArgs = @()
if ($env:VERCEL_TOKEN) { $TokenArgs = @("--token", $env:VERCEL_TOKEN) }

Write-Host "== 1/4 Check Vercel CLI =="
$vercel = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercel) {
    Write-Host "Vercel CLI not found; installing globally via npm..."
    npm install -g vercel 2>&1 | Out-String | Write-Host
    if ($LASTEXITCODE -ne 0) { Fail "npm install -g vercel failed" }
}
$ver = vercel --version 2>&1 | Out-String
Write-Host $ver.Trim()

Write-Host "== 2/4 Check login state =="
# vercel prints its banner to stderr; the username is the last non-empty stdout line
$whoamiLines = @((vercel whoami @TokenArgs 2>$null | Out-String).Trim() -split "`r?`n" | Where-Object { $_ -ne "" })
$whoami = if ($whoamiLines.Count -gt 0) { $whoamiLines[-1] } else { "" }
if ($LASTEXITCODE -ne 0) {
    if ($DryRun) {
        Write-Host "[dry-run] NOT logged in to Vercel. Run 'vercel login' or set VERCEL_TOKEN (see GO-LIVE-CHECKLIST.md)."
        Write-Host "[dry-run] All other environment checks passed."
        exit 0
    }
    Fail "Not logged in to Vercel. Run 'vercel login' or set VERCEL_TOKEN (see GO-LIVE-CHECKLIST.md)."
}
Write-Host "Logged in as: $whoami"

Write-Host "== 3/4 Project link and environment variables =="
Push-Location $SiteDir
try {
    if (-not (Test-Path ".vercel/project.json")) {
        Write-Host "First deploy: linking/creating Vercel project 'trendflow-site'"
        if (-not $DryRun) {
            vercel link --yes --project trendflow-site @TokenArgs
        }
    }
    # /admin credentials (if unset, the console stays fail-closed; rest of the site is unaffected)
    if ($env:ADMIN_USER -and $env:ADMIN_PASS -and -not $DryRun) {
        Write-Host "Injecting ADMIN_USER / ADMIN_PASS env vars"
        $env:ADMIN_USER | vercel env add ADMIN_USER production --force @TokenArgs
        $env:ADMIN_PASS | vercel env add ADMIN_PASS production --force @TokenArgs
    }
    if ($env:NEXT_PUBLIC_SITE_URL -and -not $DryRun) {
        $env:NEXT_PUBLIC_SITE_URL | vercel env add NEXT_PUBLIC_SITE_URL production --force @TokenArgs
    }

    Write-Host "== 4/4 Production deploy =="
    if ($DryRun) {
        Write-Host "[dry-run] Would run: vercel deploy --prod (root: site/)"
        Write-Host "[dry-run] All environment checks passed."
    } else {
        $url = (vercel deploy --prod --yes @TokenArgs 2>&1 | Out-String).Trim().Split("`n")[-1]
        if ($LASTEXITCODE -ne 0) { Fail "vercel deploy failed: $url" }
        Write-Host ""
        Write-Host "Deployed: $url"
        Write-Host "Verify with: python ..\tests\e2e_site.py --base-url $url"
    }
} finally {
    Pop-Location
}
