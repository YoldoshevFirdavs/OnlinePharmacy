# Push .env and .env.prod secrets to GitHub repository
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

# Function to set secret
function Set-Secret {
    param(
        [string]$Name,
        [string]$Value
    )
    
    Write-Host "   Setting $Name..." -NoNewline
    $result = gh secret set $Name --body $Value 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✓" -ForegroundColor Green
    } else {
        Write-Host " ✗" -ForegroundColor Red
    }
}

# Process .env file
if (Test-Path ".env") {
    Write-Host "📤 Pushing .env to GitHub Secrets..." -ForegroundColor Cyan
    
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^([^#]+?)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            if ($key -and $value) {
                Set-Secret -Name $key -Value $value
            }
        }
    }
} else {
    Write-Host "⚠️  .env file not found" -ForegroundColor Yellow
}

# Process .env.prod file
if (Test-Path ".env.prod") {
    Write-Host "📤 Pushing .env.prod to GitHub Secrets..." -ForegroundColor Cyan
    
    Get-Content ".env.prod" | ForEach-Object {
        if ($_ -match "^([^#]+?)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            if ($key -and $value) {
                # Add _PROD suffix for prod variables
                $prodKey = "${key}_PROD"
                Set-Secret -Name $prodKey -Value $value
            }
        }
    }
} else {
    Write-Host "⚠️  .env.prod file not found" -ForegroundColor Yellow
}

Write-Host "" -ForegroundColor Green
Write-Host "✅ All secrets pushed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 View secrets at: https://github.com/$repo/settings/secrets/actions" -ForegroundColor Cyan
