$ErrorActionPreference = "Continue"

Write-Host "== Python diagnostics ==" -ForegroundColor Cyan

Write-Host "`n[1] python --version"
python --version

Write-Host "`n[2] py -0p (installed launchers)"
py -0p

Write-Host "`n[3] where python"
where.exe python

Write-Host "`n[4] Active interpreter path"
python -c "import sys; print(sys.executable)"

Write-Host "`n[5] Active interpreter major.minor"
python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"

Write-Host "`n[6] python-telegram-bot package info"
python -m pip show python-telegram-bot

Write-Host "`n[7] Recommended test command (strict 3.10)"
Write-Host "powershell -ExecutionPolicy Bypass -File .\scripts\run_tests.ps1"
