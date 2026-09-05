# PATI installer for Windows 10/11 (owner decision: Windows, no local GPU).
# $0 stack: Python + pip + PATI (all free/open source). No credit card anywhere.
#
# Run in PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass; .\install.ps1
#
# What it does:
#   1. Detect prerequisites (Python 3.10+, pip) and explain how to fix gaps
#   2. Create an isolated venv under %USERPROFILE%\PATI\venv
#   3. Install PATI + agent into the venv (from local repo or PyPI)
#   4. Create default PATI workspace folders
#   5. Start the control plane (Task Scheduler service option)
#   6. Launch the Local Agent setup wizard (pairing, folders, permissions)
#
param(
    [string]$PatiSource = "",   # path to this repo, or empty for PyPI
    [switch]$SkipAutostart,
    [switch]$SkipWizard
)

$ErrorActionPreference = "Stop"
$Home_ = $env:USERPROFILE
$PatiHome = Join-Path $Home_ "PATI"
$VenvDir = Join-Path $PatiHome "venv"

function Info($m)  { Write-Host "[PATI] $m" -ForegroundColor Cyan }
function Ok($m)    { Write-Host "[ OK ] $m" -ForegroundColor Green }
function Warn($m)  { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Fail($m)  { Write-Host "[FAIL] $m" -ForegroundColor Red; exit 1 }

Info "PATI installer - Personal AI Tool Infrastructure (COST=`$0)"
Info "Free-only policy: FREE_ONLY=true MAX_SPEND=0 (hard requirement, enforced in code)"

# ---------------------------------------------------------------- 1. checks
Info "Checking prerequisites..."
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Fail "Python not found. Install free Python 3.10+ from https://www.python.org/downloads/ " +
         "(tick 'Add python.exe to PATH'), then re-run this installer."
}
$pyVer = & python -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')"
if ([int]$pyVer -lt 310) { Fail "Python 3.10+ required, found $pyVer. Free update: python.org" }
Ok "Python $pyVer found"

$pipOk = & python -m pip --version 2>$null
if (-not $pipOk) { Fail "pip missing. Free fix: python -m ensurepip --upgrade" }
Ok "pip available"

# ---------------------------------------------------------------- 2. venv
if (-not (Test-Path $VenvDir)) {
    Info "Creating isolated environment at $VenvDir"
    & python -m venv $VenvDir | Out-Null
}
$Pip  = Join-Path $VenvDir "Scripts\pip.exe"
$Py   = Join-Path $VenvDir "Scripts\python.exe"

# ---------------------------------------------------------------- 3. install
Info "Installing PATI (all dependencies are free/open source: fastapi MIT, uvicorn BSD, httpx BSD, psutil BSD, pydantic MIT, sqlite public domain)..."
if ($PatiSource -and (Test-Path $PatiSource)) {
    & $Pip install -e $PatiSource 2>&1 | Select-Object -Last 2
} else {
    & $Pip install pati 2>&1 | Select-Object -Last 2
}
if ($LASTEXITCODE -ne 0) { Fail "pip install failed" }
Ok "PATI installed"

# ---------------------------------------------------------------- 4. workspace
$Workspace = Join-Path $PatiHome "workspace"
foreach ($d in @($Workspace,
                 (Join-Path $PatiHome "Projects\AI"),
                 (Join-Path $PatiHome "Projects\Video"),
                 (Join-Path $PatiHome "Projects\Research"))) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}
Ok "PATI workspace ready: $Workspace (this is the default authorized folder)"

# ---------------------------------------------------------------- 5. control plane
$ServerScript = Join-Path $VenvDir "Scripts\pati-server.exe"
Info "Starting PATI control plane on http://127.0.0.1:8000 ..."
$sched = Get-ScheduledTask -TaskName "PATI-Server" -ErrorAction SilentlyContinue
if (-not $sched) {
    $action = New-ScheduledTaskAction -Execute $ServerScript -Argument "--host 127.0.0.1 --port 8000"
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    Register-ScheduledTask -TaskName "PATI-Server" -Action $action -Trigger $trigger -Force | Out-Null
}
Start-Process $ServerScript -ArgumentList "--host","127.0.0.1","--port","8000" -WindowStyle Hidden
Start-Sleep -Seconds 4
try {
    $h = Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 5
    Ok "control plane healthy (v$($h.version), FREE_ONLY=$($h.free_only))"
} catch {
    Warn "control plane did not answer yet - start manually with: pati-server"
}

# Admin token for pairing
$tokenFile = Join-Path $Home_ ".pati\data\bootstrap_admin_token.txt"
if (Test-Path $tokenFile) {
    $env:PATI_TOKEN = (Get-Content $tokenFile -Raw).Trim()
    $env:PATI_SERVER = "http://127.0.0.1:8000"
    $code = & (Join-Path $VenvDir "Scripts\pati.exe") admin-pair 2>$null
    Info "Pairing code for this computer:"
    Write-Host $code -ForegroundColor Magenta
}

# ---------------------------------------------------------------- 6. agent wizard
$AgentExe = Join-Path $VenvDir "Scripts\pati-agent.exe"
if (-not $SkipWizard) {
    Info "Launching the Local Agent setup wizard (12 steps - folders, permissions, tests)"
    & $AgentExe setup --server http://127.0.0.1:8000
    & $AgentExe doctor
}

if (-not $SkipAutostart) {
    $sched2 = Get-ScheduledTask -TaskName "PATI-Agent" -ErrorAction SilentlyContinue
    if (-not $sched2) {
        $action2 = New-ScheduledTaskAction -Execute $AgentExe -Argument "run"
        $trigger2 = New-ScheduledTaskTrigger -AtLogOn
        Register-ScheduledTask -TaskName "PATI-Agent" -Action $action2 -Trigger $trigger2 -Force | Out-Null
    }
    Ok "Agent autostart registered (Task Scheduler: PATI-Agent)"
}

Info "Optional free remote access (PC + free tunnel):"
Info "  winget install --id Cloudflare.cloudflared ; then run installer\enable-tunnel.ps1"
Info "Install complete. Try: pati submit `"Create a folder called Test 01 in my workspace`" --wait"
