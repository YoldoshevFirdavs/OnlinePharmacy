# Push .env secrets to GitHub repository
# Requires: GitHub CLI (gh) - https://cli.github.com/

Write-Host "=== GitHub Secrets Push Script ===" -ForegroundColor Cyan

# Check if GitHub CLI is installed
if (-not (Get-Command "gh" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ GitHub CLI is not installed. Please install it first:" -ForegroundColor Red
    Write-Host "   Download: https://cli.github.com/" -ForegroundColor Yellow
    exit 1
}

# Check if authenticated
Write-Host "Checking GitHub authentication..."
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ You are not authenticated with GitHub." -ForegroundColor Red
    Write-Host "   Please run: gh auth login" -ForegroundColor Yellow
    exit 1
}

# Get repository info
$repo = gh repo view --json nameWithOwner --jq ".nameWithOwner"
Write-Host "✅ Repository: $repo" -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    exit 1
}

Write-Host "📤 Pushing .env to GitHub Secrets..." -ForegroundColor Cyan

# Process .env file
$lines = Get-Content ".env"
foreach ($line in $lines) {
    # Skip empty lines and comments
    if ($line -match "^\s*$" -or $line -match "^\s*#") {
        continue
    }
    
    # Match KEY=VALUE pattern
    if ($line -match "^([^=]+)=(.*)$") {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        
        # Skip if key or value is empty
        if (-not $key -or -not $value) {
            continue
        }
        
        # Set the secret
        Write-Host "   Setting $key..." -NoNewline
        $result = gh secret set $key --body $value 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✓" -ForegroundColor Green
        } else {
            Write-Host " ✗" -ForegroundColor Red
        }
    }
}

Write-Host "" -ForegroundColor Green
Write-Host "✅ All secrets from .env pushed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 View secrets at: https://github.com/$repo/settings/secrets/actions" -ForegroundColor Cyan