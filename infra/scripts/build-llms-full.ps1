# build-llms-full.ps1 — regenerate llms-full.txt by concatenating every
# page in nav order. Run from repo root:
#
#   powershell -File infra/scripts/build-llms-full.ps1
#   # or on PowerShell 7+:
#   pwsh -File infra/scripts/build-llms-full.ps1
#
# The nav order is hardcoded to mirror mkdocs.yml — keep the two in
# sync when adding / renaming pages. The output is UTF-8 (no BOM) for
# cross-platform AI-tool ingestion.

$ErrorActionPreference = 'Stop'

$docsRoot = Join-Path (Resolve-Path "$PSScriptRoot/../..") 'docs'
$outPath  = Join-Path (Resolve-Path "$PSScriptRoot/../..") 'llms-full.txt'

# Mirror mkdocs.yml nav: Home, Getting started, Concepts, How-to,
# Reference, Compliance, Troubleshooting. When you add / move / rename
# a page in mkdocs.yml, update this list.
$pages = @(
    'index.md',
    'getting-started/onboarding.md',
    'getting-started/tour.md',
    'getting-started/install.md',
    'getting-started/quickstart.md',
    'getting-started/configuration.md',
    'concepts/circuit-breaker.md',
    'concepts/budgets.md',
    'concepts/sensitive-tools.md',
    'concepts/workflow.md',
    'concepts/tracing.md',
    'concepts/control-plane.md',
    'concepts/api-keys.md',
    'concepts/policies.md',
    'concepts/tool-policies.md',
    'concepts/human-approval.md',
    'concepts/error-handling.md',
    'how-to/langgraph.md',
    'how-to/openai-agents.md',
    'how-to/crewai.md',
    'how-to/fastapi.md',
    'how-to/llm-frameworks.md',
    'how-to/cost-cap.md',
    'how-to/multi-agent.md',
    'how-to/multi-agent-orchestration.md',
    'how-to/streaming.md',
    'how-to/custom-tracking.md',
    'how-to/ci-cd.md',
    'reference/sdk-api.md',
    'reference/http-api.md',
    'reference/errors.md',
    'reference/llm-tool-catalog.md',
    'compliance/index.md',
    'compliance/geo-restrictions.md',
    'compliance/sanctions-screening.md',
    'troubleshooting.md'
)

# Pre-flight: every page must exist or we abort.
$missing = @()
foreach ($p in $pages) {
    $full = Join-Path $docsRoot $p
    if (-not (Test-Path $full)) {
        $missing += $p
    }
}
if ($missing.Count -gt 0) {
    Write-Host 'MISSING FILES (mkdocs.yml out of sync with this script):' -ForegroundColor Red
    $missing | ForEach-Object { Write-Host ('  ' + $_) -ForegroundColor Red }
    exit 1
}

$sb = [System.Text.StringBuilder]::new()

[void]$sb.AppendLine('# NullRun Docs -- Full Text Corpus')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('> Concatenated Markdown of every page in nav order, for')
[void]$sb.AppendLine('> agents that prefer a single-fetch corpus. See llms.txt')
[void]$sb.AppendLine('> for the structured index. Regenerate this file when')
[void]$sb.AppendLine('> content changes via infra/scripts/build-llms-full.ps1.')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('Source: https://github.com/nullrunio/nullrun-docs')
[void]$sb.AppendLine('Generated against main branch.')
[void]$sb.AppendLine('')

foreach ($p in $pages) {
    $urlPath = $p -replace '\.md$', ''
    if ($urlPath -eq 'index') {
        $url = 'https://docs.nullrun.io/'
    } else {
        $url = 'https://docs.nullrun.io/' + $urlPath + '/'
    }

    [void]$sb.AppendLine('---')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('# Source: ' + $url)
    [void]$sb.AppendLine('# File: docs/' + $p)
    [void]$sb.AppendLine('')

    $content = Get-Content -Raw -Path (Join-Path $docsRoot $p) -Encoding utf8
    [void]$sb.AppendLine($content)
    [void]$sb.AppendLine('')
}

# UTF-8 without BOM: AI tool corpora don't tolerate BOMs.
[System.IO.File]::WriteAllText(
    $outPath,
    $sb.ToString(),
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host ('Wrote ' + $outPath)
Write-Host ('Size: {0:N0} bytes' -f (Get-Item $outPath).Length)
Write-Host ('Pages: ' + $pages.Count)