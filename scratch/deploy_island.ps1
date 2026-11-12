# Script de déploiement et démarrage autonome d'Antigravity Island
Write-Host "Arrêt des processus AntigravityIsland existants..."
Get-Process -Name "*AntigravityIsland*" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

$src = "C:\Users\pro\.gemini\antigravity\scratch\antigravity-island\dist\AntigravityIsland"
$dest = "C:\Users\pro\Desktop\AntigravityIsland"

Write-Host "Synchronisation vers $dest ..."
robocopy $src $dest /MIR /NP /NDL /NFL /NJH /NJS

Start-Sleep -Seconds 1
Write-Host "Démarrage d'AntigravityIsland.exe ..."
$exe = Join-Path $dest "AntigravityIsland.exe"
Start-Process "explorer.exe" -ArgumentList "`"$exe`""

Start-Sleep -Seconds 3
Get-Process -Name "*AntigravityIsland*" | Select-Object Id, ProcessName, Responding
