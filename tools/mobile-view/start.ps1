# NT mobile-view launcher (production path on Windows).
# Default: LocalOnly 127.0.0.1. Opt-in LAN: -Lan [-BindHost <ip>]
#
# CLI --host and MOBILE_VIEW_HOST must agree; this script is the production path
# (it does NOT call server.main() — uvicorn gets --host explicitly).

param(
  [switch]$Lan,
  [string]$BindHost = "",
  [int]$Port = 8787,
  [switch]$IConfirmAccessConfigured,
  [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if ($ProjectRoot) {
  $env:NT_PROJECT_ROOT = (Resolve-Path $ProjectRoot).Path
}

# --- Normative bind block (must match server.resolve_bind_host) ---
if ($Lan) {
  $env:MOBILE_VIEW_LAN = "1"
  $bindHost = if ($BindHost) { $BindHost } else { "0.0.0.0" }
  Write-Host "WARNING: LAN bind enabled ($bindHost). View-only desk is reachable on bound interfaces." -ForegroundColor Yellow
  Write-Host "Prefer Tailscale or -BindHost <single-IP> over 0.0.0.0 when practical." -ForegroundColor Yellow
} else {
  Remove-Item Env:MOBILE_VIEW_LAN -ErrorAction SilentlyContinue
  $bindHost = "127.0.0.1"
  if ($BindHost -and $BindHost -notin @("127.0.0.1", "localhost", "::1")) {
    Write-Error "-BindHost requires -Lan"
    exit 1
  }
}

if ($Lan -and $IConfirmAccessConfigured) {
  Write-Host "DOUBLE WARNING: -Lan combined with Cloudflare public path widens origin beyond Access-only. Prefer not to combine." -ForegroundColor Red
}

$env:MOBILE_VIEW_HOST = $bindHost
$env:MOBILE_VIEW_PORT = "$Port"

# MUST match resolve_bind_host() outcome — operators use this path, not server.main()
$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }
& $py -m uvicorn server:app --host $bindHost --port $Port --log-level info
