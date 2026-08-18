#!/bin/bash
# API Testing Script - Pharmacy Platform
# Usage: bash testing/curl_api_tests.sh
# Prerequisites: Running Django server on http://localhost:8000

set -e

BASE_URL="http://localhost:8000"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Pharmacy Platform API Testing ===${NC}\n"

# Helper function for pretty printing
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local auth=$5
    
    echo -e "${YELLOW}Testing: $name${NC}"
    echo "Request: $method $endpoint"
    
    if [ -z "$data" ]; then
        if [ -z "$auth" ]; then
            curl -X "$method" "$BASE_URL$endpoint" \
                -H "Content-Type: application/json" -w "\nStatus: %{http_code}\n"
        else
            curl -X "$method" "$BASE_URL$endpoint" \
                -H "Authorization: Bearer $auth" \
                -H "Content-Type: application/json" -w "\nStatus: %{http_code}\n"
        fi
    else
        if [ -z "$auth" ]; then
            curl -X "$method" "$BASE_URL$endpoint" \
                -H "Content-Type: application/json" \
                -d "$data" -w "\nStatus: %{http_code}\n"
        else
            curl -X "$method" "$BASE_URL$endpoint" \
                -H "Authorization: Bearer $auth" \
                -H "Content-Type: application/json" \
                -d "$data" -w "\nStatus: %{http_code}\n"
        fi
    fi
    echo -e "\n---\n"
}

# ============ PRODUCTS API ============
echo -e "${GREEN}1. PRODUCTS API TESTS${NC}\n"

test_endpoint \
    "Get all products (paginated)" \
    "GET" \
    "/api/v1/products/?page=1&page_size=10"

test_endpoint \
    "Filter by category" \
    "GET" \
    "/api/v1/products/?category=1"

test_endpoint \
    "Filter by price range" \
    "GET" \
    "/api/v1/products/?price_min=50&price_max=200"

test_endpoint \
    "Filter by rating" \
    "GET" \
    "/api/v1/products/?rating_min=4.0"

test_endpoint \
    "Search suggestions" \
    "GET" \
    "/api/v1/products/suggest/?query=aspirin"

# ============ COMMENTS API ============
echo -e "${GREEN}2. COMMENTS API TESTS${NC}\n"
echo -e "${YELLOW}Note: Replace TOKEN with actual JWT and IDs with real values${NC}\n"

PRODUCT_ID=1
COMMENT_ID=1
TOKEN="your_jwt_token_here"

test_endpoint \
    "Get comments for product" \
    "GET" \
    "/api/v1/products/$PRODUCT_ID/comments/"

test_endpoint \
    "Create top-level comment with rating" \
    "POST" \
    "/api/v1/products/$PRODUCT_ID/comments/" \
    '{
        "product": '$PRODUCT_ID',
        "content": "Great product!",
        "rating": 5
    }' \
    "$TOKEN"

test_endpoint \
    "Create reply (no rating)" \
    "POST" \
    "/api/v1/products/$PRODUCT_ID/comments/" \
    '{
        "product": '$PRODUCT_ID',
        "content": "I agree!",
        "parent": '$COMMENT_ID'
    }' \
    "$TOKEN"

test_endpoint \
    "Add emoji reaction (like)" \
    "POST" \
    "/api/v1/comments/$COMMENT_ID/like/" \
    '{
        "emoji": "like"
    }' \
    "$TOKEN"

test_endpoint \
    "Add different emoji (heart)" \
    "POST" \
    "/api/v1/comments/$COMMENT_ID/like/" \
    '{
        "emoji": "heart"
    }' \
    "$TOKEN"

test_endpoint \
    "Remove emoji reaction" \
    "POST" \
    "/api/v1/comments/$COMMENT_ID/unlike/" \
    '{
        "emoji": "like"
    }' \
    "$TOKEN"

test_endpoint \
    "Edit own comment" \
    "PATCH" \
    "/api/v1/comments/$COMMENT_ID/" \
    '{
        "content": "Updated: Excellent!"
    }' \
    "$TOKEN"

# ============ USER HISTORY API ============
echo -e "${GREEN}3. USER HISTORY API TESTS${NC}\n"

test_endpoint \
    "Get own history" \
    "GET" \
    "/api/v1/user/history/?page=1&page_size=20" \
    "" \
    "$TOKEN"

test_endpoint \
    "Log action - view product" \
    "POST" \
    "/api/v1/user/history/log/" \
    '{
        "action": "view_product",
        "product_id": '$PRODUCT_ID'
    }' \
    "$TOKEN"

test_endpoint \
    "Log action - add to cart" \
    "POST" \
    "/api/v1/user/history/log/" \
    '{
        "action": "add_to_cart",
        "product_id": '$PRODUCT_ID',
        "meta": {"quantity": 2}
    }' \
    "$TOKEN"

# ============ ADMIN ANALYTICS API ============
echo -e "${GREEN}4. ADMIN ANALYTICS API TESTS${NC}\n"
echo -e "${YELLOW}Note: Requires admin JWT token${NC}\n"

ADMIN_TOKEN="your_admin_jwt_token_here"
USER_ID=2
ORDER_ID=5

test_endpoint \
    "Get analytics data (admin)" \
    "GET" \
    "/dashboard/api/admin/analytics/" \
    "" \
    "$ADMIN_TOKEN"

test_endpoint \
    "Get user history (admin)" \
    "GET" \
    "/dashboard/api/admin/user/$USER_ID/history/" \
    "" \
    "$ADMIN_TOKEN"

test_endpoint \
    "Get order detail (admin)" \
    "GET" \
    "/dashboard/api/admin/user/$USER_ID/order/$ORDER_ID/" \
    "" \
    "$ADMIN_TOKEN"

echo -e "${GREEN}=== Testing Complete ===${NC}\n"
