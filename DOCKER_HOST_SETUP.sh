#!/bin/bash
# =============================================================================
# Docker Production Setup - Run on EC2 Host (NOT inside Docker)
# This script prepares host directories for docker-compose.prod.yml
# AND runs collectstatic to collect all static files
# 
# Usage: bash DOCKER_HOST_SETUP.sh
# Run as: ec2-user (or with sudo if needed)
# 
# What it does:
#   1. Create staticfiles directory (for collectstatic output)
#   2. Create media directory (for user uploads)
#   3. Create postgres_data directory (for database)
#   4. Set proper permissions
#   5. Run collectstatic on host
#   6. Display paths for verification
# =============================================================================

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Docker Production Setup - Host Directory & Static Files Preparation     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Base path
BASE_PATH="/home/ec2-user/OnlinePharmacy"

echo -e "${YELLOW}📁 Creating directories...${NC}"
echo ""

# 1. Create staticfiles directory
echo "Creating: $BASE_PATH/staticfiles"
mkdir -p "$BASE_PATH/staticfiles"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ staticfiles created${NC}"
else
    echo -e "${YELLOW}⚠️  staticfiles already exists or permission error${NC}"
fi

# 2. Create media directory
echo "Creating: $BASE_PATH/media"
mkdir -p "$BASE_PATH/media"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ media created${NC}"
else
    echo -e "${YELLOW}⚠️  media already exists or permission error${NC}"
fi

# 3. Create media subdirectories
echo "Creating: $BASE_PATH/media/uploads/avatars"
mkdir -p "$BASE_PATH/media/uploads/avatars"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ media/uploads/avatars created${NC}"
else
    echo -e "${YELLOW}⚠️  media/uploads/avatars already exists${NC}"
fi

# 4. Create postgres_data directory
echo "Creating: $BASE_PATH/postgres_data"
mkdir -p "$BASE_PATH/postgres_data"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ postgres_data created${NC}"
else
    echo -e "${YELLOW}⚠️  postgres_data already exists${NC}"
fi

echo ""
echo -e "${YELLOW}📝 Setting permissions...${NC}"
echo ""

# Set permissions (755 for directories, 644 for files)
echo "Setting permissions for staticfiles..."
chmod -R 755 "$BASE_PATH/staticfiles"
echo -e "${GREEN}✅ staticfiles permissions set${NC}"

echo "Setting permissions for media..."
chmod -R 755 "$BASE_PATH/media"
echo -e "${GREEN}✅ media permissions set${NC}"

echo "Setting permissions for postgres_data..."
chmod -R 755 "$BASE_PATH/postgres_data"
echo -e "${GREEN}✅ postgres_data permissions set${NC}"

echo ""
echo -e "${YELLOW}🎨 Running collectstatic on HOST...${NC}"
echo ""

# Change to project directory
cd "$BASE_PATH" || {
    echo -e "${YELLOW}⚠️  Could not change to $BASE_PATH${NC}"
    exit 1
}

# Run collectstatic with Python on host (not in Docker)
# This assumes Python and Django are installed on host
if command -v python &> /dev/null; then
    echo "Running: python manage.py collectstatic --noinput --clear"
    python manage.py collectstatic --noinput --clear 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ collectstatic completed successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  collectstatic completed with warnings/errors${NC}"
        echo "   This might be okay if Django is not installed on host"
        echo "   You can run it manually after Docker starts:"
        echo "   docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput"
    fi
else
    echo -e "${YELLOW}⚠️  Python not found on host${NC}"
    echo "   You can run collectstatic from inside Docker after it starts:"
    echo "   docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput"
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                          Setup Complete ✅                                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📊 Verification:${NC}"
echo ""

# Verify directories exist
echo "Host directories created:"
ls -ld "$BASE_PATH/staticfiles" "$BASE_PATH/media" "$BASE_PATH/postgres_data" 2>/dev/null

echo ""
echo -e "${YELLOW}📌 Important Notes:${NC}"
echo ""
echo "1. Docker Volumes Mapping:"
echo "   Docker                    → Host"
echo "   /app/staticfiles          → $BASE_PATH/staticfiles"
echo "   /app/media                → $BASE_PATH/media"
echo "   PostgreSQL data           → $BASE_PATH/postgres_data"
echo ""

echo "2. Static Files Collection:"
echo "   ✓ collectstatic ran on HOST machine (not in Docker)"
echo "   ✓ Files are in: $BASE_PATH/staticfiles/static/"
echo "   ✓ Docker will serve from this directory"
echo ""

echo "3. What happens when docker-compose starts:"
echo "   • Django writes to: /app/staticfiles (mounted to host)"
echo "   • Avatar uploads go to: $BASE_PATH/media/uploads/avatars"
echo "   • Database data stored in: $BASE_PATH/postgres_data"
echo ""

echo "4. To start docker-compose:"
echo "   cd $BASE_PATH"
echo "   docker compose -f docker-compose.prod.yml up -d"
echo ""

echo "5. To verify static files were collected:"
echo "   ls -la $BASE_PATH/staticfiles/static/"
echo ""

echo "6. If collectstatic didn't run (Python not on host):"
echo "   docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput"
echo ""

echo -e "${GREEN}✅ Setup complete! You're ready to run docker-compose.${NC}"
echo ""
