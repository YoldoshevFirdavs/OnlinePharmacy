$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

function Info([string]$Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

try {
    $required = "3.10"
    $venvPath = ".venv310"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

    Info "Checking Python launcher for 3.10"
    try {
        $py310Version = py -3.10 --version 2>&1
    }
    catch {
        Fail "Python 3.10 is not available via 'py -3.10'. Install Python 3.10 and try again."
    }
    if ($LASTEXITCODE -ne 0) {
        Fail "Python 3.10 launcher check failed: $py310Version"
    }
    Info "$py310Version"

    if (-not (Test-Path $venvPython)) {
        Info "Creating virtual environment at $venvPath"
        py -3.10 -m venv $venvPath
        if ($LASTEXITCODE -ne 0) { Fail "Failed to create virtual environment .venv310" }
    }

    if (-not (Test-Path $activateScript)) {
        Fail "Activation script not found at $activateScript"
    }

    Info "Activating $venvPath"
    . $activateScript

    $minor = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($minor -ne $required) {
        Fail "Tests must run with Python $required, current: $minor"
    }

    Info "Python version:"
    python --version

    Info "Installing dependencies"
    python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Fail "Failed to upgrade pip" }
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Fail "Failed to install requirements.txt" }

    Info "Running tests"
    python -m pytest -q @args
    if ($LASTEXITCODE -ne 0) { Fail "Tests failed. Run .\scripts\diagnose_python.ps1 for details." }

    Write-Host "[OK] Tests finished successfully." -ForegroundColor Green
}
catch {
    Fail "Unexpected failure: $($_.Exception.Message)"
}

