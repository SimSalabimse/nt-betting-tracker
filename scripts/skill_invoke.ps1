# Print slash + first steps for a desk skill (does not run Grok).
# Usage: .\scripts\skill_invoke.ps1 daily-run

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("daily-run", "missed-audit", "chain-explain", "bankroll-tune", "learning-rootcause")]
    [string]$Skill
)

$ErrorActionPreference = "Stop"
$skillMd = Join-Path $env:USERPROFILE ".grok\skills\$Skill\SKILL.md"

if (-not (Test-Path $skillMd)) {
    Write-Error "Skill not installed: $skillMd"
}

Write-Host "=== /$Skill ===" -ForegroundColor Cyan
Write-Host "SKILL.md: $skillMd"
Write-Host "Law: load AGENTS.md first; engines in nt/ are law."
Write-Host ""

switch ($Skill) {
    "daily-run" {
        Write-Host @"
Grok: /daily-run [inbox/odds_….txt]

First steps:
  python run_nt.py status
  python run_nt.py settle --draft
  python run_nt.py research market-scan --odds <odds>
  python run_nt.py research board --odds <odds>
  python run_nt.py research light --odds <odds>
  # deep packs on engine deep_queue …
  python run_nt.py research ready --odds <odds>
  python run_nt.py recommend --odds <odds>
  # place-ack after user places on NT

Deliverables: outbox/PLACE_THESE.md · evidence/*.json · data/state/deep_queue.json
"@
    }
    "missed-audit" {
        Write-Host @"
Grok: /missed-audit

First steps:
  python run_nt.py research light --odds <odds> --json
  Get-Content data/state/deep_queue.json
  # decompose promotion_score for mid-band 1.80–2.20 not in queue
  # cheapest fix (research now > process > config proposal)

Deliverables: audit table + optional outbox/missed_audit_<date>.md
"@
    }
    "chain-explain" {
        Write-Host @"
Grok: /chain-explain <match> | <selection>

First steps:
  Read evidence/<pack>.json · deep_queue · PLACE_THESE · risk.json
  python run_nt.py research critique evidence/<pack>.json --odds <dec>
  python run_nt.py research p-model --odds <dec> --p <p_model>
  Emit full Reasoning Chain template (context→decision)

Deliverables: chain markdown · optional outbox/reasoning_<slug>.md
"@
    }
    "bankroll-tune" {
        Write-Host @"
Grok: /bankroll-tune

First steps:
  python run_nt.py capital status
  python run_nt.py status
  python scripts/mc_phase_progression.py --paths 50
  # propose config key deltas only after MC

Deliverables: proposal table · MC summary · no silent config edit
"@
    }
    "learning-rootcause" {
        Write-Host @"
Grok: /learning-rootcause

First steps:
  python run_nt.py settle --draft
  Classify predictability + variance_class + learning_weight
  python scripts/backfill_settlement_taxonomy.py --n 30 --dry-run
  python run_nt.py control-signals list --json

Deliverables: taxonomy table · settlement_reviews.jsonl · reweight report
"@
    }
}

Write-Host ""
Write-Host "Open skill body:"
Write-Host "  Get-Content `"$skillMd`""
