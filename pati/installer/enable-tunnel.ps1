# Enables a FREE Cloudflare Tunnel so Z.ai / phone / other devices can reach
# your local PATI control plane without opening ports or paying anything.
#
# One-time:  winget install --id Cloudflare.cloudflared
#            cloudflared tunnel login            (browser consent, free account)
# Then:      .\enable-tunnel.ps1
#
param([string]$TunnelName = "pati")
$ErrorActionPreference = "Stop"

function Info($m) { Write-Host "[PATI] $m" -ForegroundColor Cyan }
function Fail($m) { Write-Host "[FAIL] $m" -ForegroundColor Red; exit 1 }

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Fail "cloudflared not found. Free install: winget install --id Cloudflare.cloudflared"
}
Info "Creating free tunnel '$TunnelName' -> http://127.0.0.1:8000"
cloudflared tunnel create $TunnelName
$id = (cloudflared tunnel list | Select-String $TunnelName) -split '\s+' | Select-Object -First 1
$conf = "$env:USERPROFILE\.cloudflared\config.yml"
@"
tunnel: $id
credentials-file: $env:USERPROFILE\.cloudflared\$id.json
ingress:
  - hostname: $TunnelName.YOURDOMAIN.com
    service: http://127.0.0.1:8000
  - service: http_status:404
"@ | Set-Content $conf
Info "Config written to $conf"
Info "Edit YOURDOMAIN.com (any free Cloudflare domain) then run:"
Info "  cloudflared tunnel route dns $TunnelName $TunnelName.YOURDOMAIN.com"
Info "  cloudflared tunnel run $TunnelName"
Info "Optional autostart: cloudflared service install"
Info "SECURITY: PATI still requires bearer tokens for every call; the tunnel adds transport only."
