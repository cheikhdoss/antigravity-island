@echo off
title Antigravity Island Launcher
echo Lancement d'Antigravity Island...
if exist "%~dp0dist\AntigravityIsland\AntigravityIsland.exe" (
    start "" "%~dp0dist\AntigravityIsland\AntigravityIsland.exe"
) else (
    echo Le fichier .exe n'est pas encore compile. Lancement via Python...
    start pythonw "%~dp0main.py"
)
exit
