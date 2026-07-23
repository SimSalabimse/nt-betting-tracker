# Desk-skill smoke: coverage floor, MC phase progression, taxonomy weights.
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
    $names = @("daily-run","missed-audit","chain-explain","bankroll-tune","learning-rootcause")
    foreach ($n in $names) {
        $p = Join-Path $env:USERPROFILE ".grok\skills\$n\SKILL.md"
        if (-not (Test-Path $p)) { throw "missing $p" }
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

Write-Host ""
Write-Host "=== SMOKE SUMMARY ==="
$log | ForEach-Object { Write-Host $_ }
if ($failed -gt 0) {
    Write-Host "FAILED steps: $failed" -ForegroundColor Red
    exit 1
}
Write-Host "All smoke steps passed." -ForegroundColor Green
exit 0
