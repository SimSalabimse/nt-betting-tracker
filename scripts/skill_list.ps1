# List installed NT desk skills (user-scope Grok).
# Usage (from tracker root): .\scripts\skill_list.ps1

$ErrorActionPreference = "Stop"
$skillsRoot = Join-Path $env:USERPROFILE ".grok\skills"
$names = @(
    "daily-run",
    "missed-audit",
    "chain-explain",
    "bankroll-tune",
    "learning-rootcause"
)

Write-Host "Grok skills root: $skillsRoot"
Write-Host ""

foreach ($n in $names) {
    $skillMd = Join-Path $skillsRoot "$n\SKILL.md"
    if (Test-Path $skillMd) {
        $len = (Get-Item $skillMd).Length
        Write-Host ("[OK]  /{0,-20} {1}  ({2} bytes)" -f $n, $skillMd, $len)
    } else {
        Write-Host ("[MISS] /{0,-20} missing: {1}" -f $n, $skillMd) -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Docs: docs/DESK_SKILLS.md  |  Law: AGENTS.md"
Write-Host "Invoke in Grok: /daily-run  /missed-audit  /chain-explain  /bankroll-tune  /learning-rootcause"
