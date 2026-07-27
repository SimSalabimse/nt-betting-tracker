# Desk-skill smoke: coverage floor, MC phase progression, taxonomy weights,
# adaptive scan-merge / scan-depth (ESR), data-first MIC / can-bet / quality-veto,
# TRI decision template (Stage 3 Dual superseded).
# Usage (from tracker root): .\scripts\skill_smoke.ps1

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$failed = 0
$log = @()

function Invoke-Step {
    param([string]$Name, [scriptblock]$Block)
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    try {
        & $Block
        if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
            Write-Host "FAIL exit=$LASTEXITCODE" -ForegroundColor Red
            $script:failed++
            $script:log += "$Name : FAIL exit=$LASTEXITCODE"
        } else {
            Write-Host "OK" -ForegroundColor Green
            $script:log += "$Name : OK"
        }
    } catch {
        Write-Host "FAIL $_" -ForegroundColor Red
        $script:failed++
        $script:log += "$Name : FAIL $_"
    }
}

Write-Host "Tracker root: $Root"
Write-Host "Python: $(python --version 2>&1)"

# 0) Skills installed
Invoke-Step "skill_list" {
    & "$PSScriptRoot\skill_list.ps1"
    $names = @("daily-run","deep-research","missed-audit","chain-explain","bankroll-tune","learning-rootcause")
    foreach ($n in $names) {
        $p = Join-Path $env:USERPROFILE ".grok\skills\$n\SKILL.md"
        if (-not (Test-Path $p)) { throw "missing $p" }
    }
    # Data-first skill phrases (repo mirrors byte-synced with live)
    $dailyMirror = Join-Path $Root "docs\skills_mirror_daily-run.md"
    if (-not (Test-Path $dailyMirror)) { throw "missing $dailyMirror" }
    $dm = Get-Content $dailyMirror -Raw
    foreach ($needle in @(
        "assert-can-bet",
        "match-intel",
        "apply-quality-veto",
        "KD-place-law",
        "esr_data_v1",
        "re_expand_once",
        "TRI_DECISION",
        # PR5: A–D MIC justification + Agent D spawn contract
        "Match Intelligence Cards when present",
        "mic:grade",
        "n=40",
        "n=41",
        # PR-6 MIC multi-sport free pipeline + process_miss polish
        "process_miss_reason",
        "thin_public",
        "multi-sport free pipeline",
        "FIRECRAWL_API_KEY",
        "playwright install chromium",
        "require_for_deep"
    )) {
        if ($dm -notmatch [regex]::Escape($needle)) {
            throw "daily-run mirror missing required phrase: $needle"
        }
    }
    $deepMirror = Join-Path $Root "docs\skills_mirror_deep-research.md"
    if (-not (Test-Path $deepMirror)) { throw "missing $deepMirror" }
    $dpm = Get-Content $deepMirror -Raw
    foreach ($needle in @(
        "MIC primary",
        "process_miss",
        "thin_public",
        "require_for_deep",
        "v1_sports"
    )) {
        if ($dpm -notmatch [regex]::Escape($needle)) {
            throw "deep-research mirror missing required phrase: $needle"
        }
    }
}

# 1) Coverage floor Mechanism A/B
Invoke-Step "verify_coverage_floor --synthetic-large" {
    python scripts/verify_coverage_floor.py --synthetic-large
}

# 2) MC phase progression (fast)
Invoke-Step "mc_phase_progression --paths 50" {
    python scripts/mc_phase_progression.py --paths 50 --seed 42
}

# 3) Taxonomy weight smoke (Windows: stdlib 'nt' shadow — use nt_bootstrap)
Invoke-Step "taxonomy compute_learning_weight" {
    python -c @"
import nt_bootstrap  # noqa: F401
from nt.settlement_taxonomy import compute_learning_weight as w

a = w('highly_predictable', 'systematic_script_form')
b = w('unpredictable_from_available_info', 'true_randomness')
c = w('moderately_predictable', 'research_process_miss')
print('systematic_highly', a)
print('random_unpred', b)
print('process_mod', c)
assert abs(a - 1.0) < 1e-9, a
assert abs(b - 0.01) < 1e-9, b  # 0.05 * 0.20
assert abs(c - 0.7125) < 1e-9, c  # 0.95 * 0.75
print('taxonomy weight smoke PASS')
"@
}

# 4) TRI Decision golden template present (KD-place-law; Dual Stage 3 superseded)
Invoke-Step "tri_decision_template_present" {
    $p = Join-Path $Root "docs\templates\TRI_DECISION_TEMPLATE.md"
    if (-not (Test-Path $p)) { throw "missing $p" }
    $txt = Get-Content $p -Raw
    foreach ($needle in @(
        "KD-place-law",
        "decision_agent_edge",
        "decision_agent_guardian",
        "decision_agent_quality",
        "apply-quality-veto",
        "quality_veto_applied",
        "re_expand_once",
        "assert-can-bet"
    )) {
        if ($txt -notmatch [regex]::Escape($needle)) {
            throw "TRI template missing required phrase: $needle"
        }
    }
    Write-Host "tri-decision template OK: $p"
}

# 4b) CLI help: match-intel / assert-can-bet / apply-quality-veto
Invoke-Step "cli_help match-intel" {
    python run_nt.py research match-intel --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "match-intel --help exit $LASTEXITCODE" }
}
Invoke-Step "cli_help assert-can-bet" {
    python run_nt.py research assert-can-bet --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "assert-can-bet --help exit $LASTEXITCODE" }
}
Invoke-Step "cli_help apply-quality-veto" {
    python run_nt.py research apply-quality-veto --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "apply-quality-veto --help exit $LASTEXITCODE" }
}

# 4c) Soft-reset script: --help + --dry-run (plan only; never write)
Invoke-Step "soft_reset --help + dry-run" {
    $help = python scripts/soft_reset_data_first_500.py --help 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "soft_reset --help exit $LASTEXITCODE" }
    foreach ($needle in @("--dry-run", "--confirm", "esr_data_v1", "500")) {
        if ($help -notmatch [regex]::Escape($needle)) {
            throw "soft_reset help missing: $needle"
        }
    }
    # Dry-run must not mutate; may exit non-zero if pending open risk (script aborts) —
    # accept exit 0 (plan printed) or a clear pending-abort message.
    $dry = python scripts/soft_reset_data_first_500.py --dry-run 2>&1 | Out-String
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Host "soft_reset --dry-run plan OK"
    } elseif ($dry -match "pending|open risk|Refusing|abort") {
        Write-Host "soft_reset --dry-run pending/abort path OK (exit $code)"
    } else {
        throw "soft_reset --dry-run unexpected exit $code : $dry"
    }
    # Invoke-Step treats leftover LASTEXITCODE as failure — clear after accepted paths.
    $global:LASTEXITCODE = 0
}

# 5) scan-merge one-agent-missing path (pytest contract from PR0)
Invoke-Step "pytest scan-merge one-agent-missing" {
    python -m pytest tests/test_scan_merge.py::test_empty_agent_file_tolerated -q --tb=line
}

# 6) scan-depth 40/41 spawn fixture (pytest contract from PR3)
Invoke-Step "pytest scan-depth 40/41" {
    python -m pytest tests/test_scan_depth.py::test_should_spawn_agent_d_n40_false_n41_true -q --tb=line
}

Write-Host ""
Write-Host "=== SMOKE SUMMARY ==="
$log | ForEach-Object { Write-Host $_ }
if ($failed -gt 0) {
    Write-Host "FAILED steps: $failed" -ForegroundColor Red
    exit 1
}
Write-Host "All smoke steps passed." -ForegroundColor Green
exit 0
