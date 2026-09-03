# Windows uninstaller - removes scheduled tasks, venv and (optionally) data.
param([switch]$KeepData)
$ErrorActionPreference = "SilentlyContinue"
Write-Host "[PATI] uninstalling (free software, no leftovers billed to anyone)" -ForegroundColor Cyan

Unregister-ScheduledTask -TaskName "PATI-Agent" -Confirm:$false
Unregister-ScheduledTask -TaskName "PATI-Server" -Confirm:$false
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*PATI\venv*" } | Stop-Process

Remove-Item -Recurse -Force "$env:USERPROFILE\PATI\venv"
Remove-Item -Recurse -Force "$env:USERPROFILE\.cloudflared\config.yml" -ErrorAction SilentlyContinue
if (-not $KeepData) {
    Remove-Item -Recurse -Force "$env:USERPROFILE\.pati"
    Remove-Item -Recurse -Force "$env:USERPROFILE\PATI\data"
    Write-Host "[PATI] data removed (artifacts, db, audit logs)"
} else {
    Write-Host "[PATI] data kept under $env:USERPROFILE\PATI\data"
}
Write-Host "[PATI] uninstall complete"
