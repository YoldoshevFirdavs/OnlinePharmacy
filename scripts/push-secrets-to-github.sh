#!/bin/bash
# Push .env and .env.prod secrets to GitHub repository

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI is not installed. Please install it first:"
    echo "   macOS: brew install gh"
    echo "   Windows: winget install --id GitHub.cli"
    echo "   Linux: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ You are not authenticated with GitHub."
    echo "   Please run: gh auth login"
    exit 1
fi

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q ".nameWithOwner")
echo "✅ Repository: $REPO"

# Push .env file
if [ -f ".env" ]; then
    echo "📤 Pushing .env to GitHub Secrets..."
    
    # Read .env and set each variable as a secret
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # Skip empty lines and comments
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        
        # Trim whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        # Skip if value is empty
        [ -z "$value" ] && continue
        
        # Set the secret
        if gh secret set "$key" --body "$value" &> /dev/null; then
            echo "   ✓ $key"
        else
            echo "   ✗ Failed to set $key"
        fi
    done < .env
else
    echo "⚠️  .env file not found"
fi

# Push .env.prod file
if [ -f ".env.prod" ]; then
    echo "📤 Pushing .env.prod to GitHub Secrets..."
    
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # Skip empty lines and comments
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        
        # Trim whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        # Skip if value is empty
        [ -z "$value" ] && continue
        
        # Add _PROD suffix for prod variables
        prod_key="${key}_PROD"
        
        # Set the secret
        if gh secret set "$prod_key" --body "$value" &> /dev/null; then
            echo "   ✓ $prod_key"
        else
            echo "   ✗ Failed to set $prod_key"
        fi
    done < .env.prod
else
    echo "⚠️  .env.prod file not found"
fi

echo "✅ All secrets pushed successfully!"
echo ""
echo "📋 You can view secrets at: https://github.com/$REPO/settings/secrets/actions"
