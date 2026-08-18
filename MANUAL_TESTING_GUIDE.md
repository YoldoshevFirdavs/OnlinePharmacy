# Manual Testing Guide - Pharmacy Platform Refactor

**Status**: Ready for testing (11/12 tasks completed)  
**Date**: August 2026  
**Scope**: API endpoints, UI components, immutability, threading, AJAX, background tasks

---

## 1. API Testing with curl

### 1.1 Products API - Filtering & Search

#### Test 1.1.1: Get all products (paginated)
```bash
curl -X GET "http://localhost:8000/api/v1/products/?page=1&page_size=10" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, 10 products returned, pagination info

#### Test 1.1.2: Filter by category
```bash
curl -X GET "http://localhost:8000/api/v1/products/?category=1" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, only products from category 1

#### Test 1.1.3: Filter by price range
```bash
curl -X GET "http://localhost:8000/api/v1/products/?price_min=50&price_max=200" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, products within price range

#### Test 1.1.4: Filter by rating
```bash
curl -X GET "http://localhost:8000/api/v1/products/?rating_min=4.0" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, products with rating >= 4.0

#### Test 1.1.5: Search suggestions
```bash
curl -X GET "http://localhost:8000/api/v1/products/suggest/?query=aspirin" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, array of top 10 matching products with id, name, rating, price

#### Test 1.1.6: Search with pagination and sorting
```bash
curl -X GET "http://localhost:8000/api/v1/products/?search=vitamin&ordering=-average_rating&page_size=5" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, vitamins sorted by rating descending

---

### 1.2 Comments API - Threaded (YouTube-style)

**Setup**: Get a product ID first, create test user, get auth token

#### Test 1.2.1: Get comments for product
```bash
PRODUCT_ID=1
curl -X GET "http://localhost:8000/api/v1/products/$PRODUCT_ID/comments/?page=1&page_size=10" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, paginated list of top-level comments with nested replies

#### Test 1.2.2: Create top-level comment with rating
```bash
PRODUCT_ID=1
TOKEN="your_jwt_token_here"

curl -X POST "http://localhost:8000/api/v1/products/$PRODUCT_ID/comments/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product": '$PRODUCT_ID',
    "content": "Great product, highly recommend!",
    "rating": 5
  }'
```
**Expected**: 201 CREATED, comment returned with user info, rating=5, parent=null

#### Test 1.2.3: Create reply to comment (no rating)
```bash
PRODUCT_ID=1
COMMENT_ID=1
TOKEN="your_jwt_token"

curl -X POST "http://localhost:8000/api/v1/products/$PRODUCT_ID/comments/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product": '$PRODUCT_ID',
    "content": "I agree!",
    "parent": '$COMMENT_ID'
  }'
```
**Expected**: 201 CREATED, reply with parent_id, rating=null (replies don't have rating)

#### Test 1.2.4: Add emoji reaction (like)
```bash
COMMENT_ID=1
TOKEN="your_jwt_token"

curl -X POST "http://localhost:8000/api/v1/comments/$COMMENT_ID/like/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "emoji": "like"
  }'
```
**Expected**: 201 CREATED, reaction record returned

#### Test 1.2.5: Add different emoji (heart)
```bash
COMMENT_ID=1
TOKEN="your_jwt_token"

curl -X POST "http://localhost:8000/api/v1/comments/$COMMENT_ID/like/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "emoji": "heart"
  }'
```
**Expected**: 201 CREATED, second emoji reaction added

#### Test 1.2.6: Remove emoji reaction
```bash
COMMENT_ID=1
TOKEN="your_jwt_token"

curl -X POST "http://localhost:8000/api/v1/comments/$COMMENT_ID/unlike/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "emoji": "like"
  }'
```
**Expected**: 204 NO CONTENT, like removed

#### Test 1.2.7: Edit own comment
```bash
COMMENT_ID=1
TOKEN="your_jwt_token"

curl -X PATCH "http://localhost:8000/api/v1/comments/$COMMENT_ID/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Updated: Excellent product!"
  }'
```
**Expected**: 200 OK, comment updated

#### Test 1.2.8: Delete own comment
```bash
COMMENT_ID=1
TOKEN="your_jwt_token"

curl -X DELETE "http://localhost:8000/api/v1/comments/$COMMENT_ID/" \
  -H "Authorization: Bearer $TOKEN"
```
**Expected**: 204 NO CONTENT, comment deleted

#### Test 1.2.9: Cannot edit others' comment (403)
```bash
COMMENT_ID=2  # Someone else's comment
TOKEN="your_jwt_token"

curl -X PATCH "http://localhost:8000/api/v1/comments/$COMMENT_ID/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hacked!"}'
```
**Expected**: 403 FORBIDDEN, "You can only edit your own comments"

---

### 1.3 User History API - Immutable Audit Log

#### Test 1.3.1: Get own history (paginated)
```bash
TOKEN="your_jwt_token"

curl -X GET "http://localhost:8000/api/v1/user/history/?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, paginated history, immutable records

#### Test 1.3.2: Log action - view product
```bash
PRODUCT_ID=1
TOKEN="your_jwt_token"

curl -X POST "http://localhost:8000/api/v1/user/history/log/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "view_product",
    "product_id": '$PRODUCT_ID'
  }'
```
**Expected**: 201 CREATED, history entry recorded with timestamp, IP address

#### Test 1.3.3: Log action - add to cart
```bash
PRODUCT_ID=1
TOKEN="your_jwt_token"

curl -X POST "http://localhost:8000/api/v1/user/history/log/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_to_cart",
    "product_id": '$PRODUCT_ID',
    "meta": {"quantity": 2, "variant": "large"}
  }'
```
**Expected**: 201 CREATED, history with JSON metadata

#### Test 1.3.4: Verify history is read-only (cannot update)
```bash
HISTORY_ID=1
TOKEN="your_jwt_token"

curl -X PATCH "http://localhost:8000/api/v1/user/history/$HISTORY_ID/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "edit"}'
```
**Expected**: 405 METHOD NOT ALLOWED or 403 FORBIDDEN

---

### 1.4 Admin Analytics API

#### Test 1.4.1: Get analytics data (admin only)
```bash
ADMIN_TOKEN="your_admin_jwt_token"

curl -X GET "http://localhost:8000/dashboard/api/admin/analytics/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, returns:
- orders: {total, last_7_days, last_30_days, pending, delivered}
- revenue: {total, last_7_days, last_30_days}
- products: {total, out_of_stock, low_stock}
- users: {total, customers, sellers}
- comments: {total, approved, unapproved}
- charts: {daily_orders, daily_revenue, order_status}

#### Test 1.4.2: Get user history (admin only)
```bash
USER_ID=2
ADMIN_TOKEN="your_admin_jwt_token"

curl -X GET "http://localhost:8000/dashboard/api/admin/user/$USER_ID/history/?page=1&page_size=50" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, paginated history for that user

#### Test 1.4.3: Get order detail (admin only)
```bash
USER_ID=2
ORDER_ID=5
ADMIN_TOKEN="your_admin_jwt_token"

curl -X GET "http://localhost:8000/dashboard/api/admin/user/$USER_ID/order/$ORDER_ID/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```
**Expected**: 200 OK, returns order with customer info and line items

---

## 2. UI Smoke Tests

### 2.1 Shop Page (`/shop/`)

**Test 2.1.1**: Load shop page
- ✅ Page loads in < 3 seconds
- ✅ Search field visible at top
- ✅ Filter panel on left side
- ✅ Product grid displays 24 items
- ✅ No console errors

**Test 2.1.2**: Search with suggestions
1. Type "aspirin" in search field
2. ✅ Dropdown appears with top 10 suggestions (debounce 150ms)
3. ✅ Each suggestion shows: name, price, rating
4. ✅ Click suggestion → navigates to product detail

**Test 2.1.3**: Filter by category
1. Click category filter
2. Select "Vitaminlar"
3. ✅ Product grid updates (no page reload)
4. ✅ All cards show Vitaminlar products
5. ✅ Count updates

**Test 2.1.4**: Filter by price range
1. Adjust price slider: $50 - $200
2. ✅ Products update in real-time
3. ✅ Only products within range displayed

**Test 2.1.5**: Sort products
1. Click "Reference" button (sort)
2. ✅ Dropdown shows 8 options:
   - Most sold
   - Most viewed
   - A-Z (name)
   - Z-A (name)
   - Most expensive
   - Least expensive
   - Best rated
   - Most reviews
3. Select "Best rated"
4. ✅ Products reorder by rating (descending)

**Test 2.1.6**: Pagination
1. Scroll to bottom
2. ✅ Pagination buttons visible
3. Click "Next"
4. ✅ Page 2 loads (24 more items)

---

### 2.2 Product Detail Page (`/products/<id>/`)

**Test 2.2.1**: Load product detail
- ✅ Left side: product image with lazy-load
- ✅ Right side: product info panel
- ✅ Seller avatar + name (clickable → seller page)
- ✅ Rating display with stars
- ✅ Description text
- ✅ Red warning block (side effects, contraindications)
- ✅ "Full Guide" button

**Test 2.2.2**: Quantity selector & Add to cart
1. Click "+" button to increase quantity to 3
2. ✅ Quantity updates
3. Click "Add to cart"
4. ✅ Animation plays (pop effect)
5. ✅ Toast notification: "Added 3 items to cart"

**Test 2.2.3**: Full guide page
1. Click "Full Guide" button
2. ✅ Navigate to `/products/<id>/full/`
3. ✅ Shows: Instruction, Storage, Side Effects (red), Contraindications (red)

**Test 2.2.4**: Comments section (YouTube-style)
1. Scroll to comments section
2. ✅ Comment form visible (if logged in)
3. ✅ 5-star rating selector visible
4. Type comment: "Great product!"
5. Click "Post Comment"
6. ✅ Comment appears in list (at top)
7. ✅ User avatar, name, timestamp visible
8. ✅ Comment shows rating (if provided)

**Test 2.2.5**: Add reply to comment
1. Hover over comment → "Reply" button appears
2. Click "Reply"
3. ✅ Reply form opens (indented)
4. Type: "I agree!"
5. Click "Reply"
6. ✅ Reply appears nested under parent comment (indented)
7. ✅ Reply has NO rating selector

**Test 2.2.6**: Emoji reactions
1. Hover over comment → emoji reactions bar appears
2. Click "😊 React"
3. ✅ Emoji picker popup appears with 6 options: 👍❤️😂😮😢😠
4. Click "👍"
5. ✅ Reaction counter shows "1"
6. Hover again → thumbs up button shows "1"
7. Click again
8. ✅ Reaction removed, counter goes to 0

**Test 2.2.7**: Edit comment (author only)
1. Find own comment
2. Hover over it → "⋮" menu appears
3. Click menu → "Edit" option
4. ✅ Edit form opens
5. Change text to "Updated: Great!"
6. Click "Save"
7. ✅ Comment updates in-place

**Test 2.2.8**: Delete comment
1. Hover own comment → "⋮" menu
2. Click "Delete"
3. ✅ Confirmation dialog
4. Click "Confirm"
5. ✅ Comment removed from list

---

### 2.3 Seller Page (`/sellers/<id>/`)

**Test 2.3.1**: Load seller page
- ✅ Large avatar header with gradient background
- ✅ Shop name displayed prominently
- ✅ Stats: Rating, Total Sells, Total Reviews
- ✅ "About" section with shop description
- ✅ Product grid (seller's products)
- ✅ Contact info at bottom

**Test 2.3.2**: Seller products
1. Scroll down to products section
2. ✅ Products displayed in grid
3. Click product card
4. ✅ Navigate to product detail
5. ✅ Check seller info matches

---

### 2.4 Admin Dashboard (`/dashboard/admin/analytics/`)

**Test 2.4.1**: Load analytics dashboard
- ✅ Metrics cards displayed:
  - Total Orders
  - Pending Orders
  - Delivered Orders
  - Total Revenue
  - Total Products
  - Out of Stock
  - Total Users
  - Total Comments
  - Unapproved Comments

**Test 2.4.2**: Charts auto-refresh (1 minute)
1. Page loads
2. ✅ Three charts visible:
   - Daily Orders (line chart, last 30 days)
   - Daily Revenue (bar chart, last 30 days)
   - Order Status Distribution (pie chart)
3. Wait 60 seconds
4. ✅ Charts refresh automatically (without page reload)
5. ✅ Last updated timestamp changes

**Test 2.4.3**: User history page `/dashboard/admin/user/<id>/history/`
1. Navigate to user history admin page
2. ✅ User info displayed (name, email)
3. ✅ History table shows:
   - Timestamp
   - Action (view_product, add_to_cart, etc.)
   - Product/Resource
   - Details (qty, rating, etc.)
   - IP address
4. ✅ Pagination visible (50 items per page)
5. Click "Next"
6. ✅ Load more history records

**Test 2.4.4**: Order detail page `/dashboard/admin/user/<id>/order/<id>/`
1. Navigate to order detail admin page
2. ✅ Order info: ID, Status, Total, Created date
3. ✅ Customer info: Name, Email, Phone
4. ✅ Line items table:
   - Product name
   - Quantity
   - Unit price
   - Subtotal
5. ✅ Order summary section with total

---

### 2.5 Immutability Tests (History)

**Test 2.5.1**: Verify history cannot be edited
1. Get a history record ID from user history page
2. Try to PATCH it via API
3. ✅ 405 METHOD NOT ALLOWED or 403 FORBIDDEN

**Test 2.5.2**: Verify history cannot be deleted
1. Try to DELETE a history record via API
2. ✅ Operation fails with 405 or 403

**Test 2.5.3**: Verify history timestamps are immutable
1. Get history record
2. Try to update timestamp
3. ✅ Operation fails

---

### 2.6 Performance Tests

**Test 2.6.1**: Shop page load time
- ✅ First paint: < 1.5s
- ✅ Full load: < 3s
- ✅ Images lazy-load on scroll

**Test 2.6.2**: Product suggestions (debounce)
1. Type "a" in search
2. Type "s" quickly
3. Type "p" quickly
4. ✅ Only ONE API request (after 150ms pause)
5. Results appear in < 200ms

**Test 2.6.3**: Comment loading
1. Navigate to product with 100+ comments
2. ✅ Page loads quickly (pagination: 50/page)
3. Click "Next" → next batch loads in < 500ms

**Test 2.6.4**: Analytics dashboard charts
1. Load analytics page
2. ✅ Charts render in < 2s
3. Resize browser
4. ✅ Charts responsive, update without error

---

## 3. Cross-browser Testing

- ✅ Chrome (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Edge (latest)
- ✅ Mobile Safari (iOS)
- ✅ Chrome Mobile (Android)

**Responsive breakpoints**:
- ✅ Desktop (1920px)
- ✅ Tablet (768px)
- ✅ Mobile (375px)

---

## 4. Security Tests

**Test 4.1**: Authentication required
- ✅ Cannot create comment without login
- ✅ Cannot access history without login
- ✅ Cannot access admin analytics without staff status

**Test 4.2**: Authorization
- ✅ Cannot edit others' comments
- ✅ Cannot delete others' comments
- ✅ Cannot modify history records

**Test 4.3**: Input validation
- ✅ Comment rating must be 1-5
- ✅ Reply cannot have rating
- ✅ Invalid emoji rejected

---

## 5. Bug Reporting Template

```
**Title**: [Component] Brief description

**Environment**: 
- Browser: Chrome 120
- Device: Desktop/Mobile
- URL: /products/1/
- User: Authenticated/Anonymous

**Steps to Reproduce**:
1. Load page
2. Scroll to comments
3. Click emoji picker

**Expected**: Emoji picker shows 6 emojis

**Actual**: Emoji picker empty or blank

**Screenshots**: [Attach]

**Console Errors**: [Copy from DevTools]
```

---

## 6. Sign-off Checklist

- [ ] All API tests passing
- [ ] All UI smoke tests passing
- [ ] Performance tests acceptable
- [ ] Cross-browser compatibility verified
- [ ] Mobile responsiveness checked
- [ ] Security requirements met
- [ ] No console errors or warnings
- [ ] Comments immutability verified
- [ ] History immutability verified
- [ ] Admin dashboard charts updating
- [ ] AJAX requests not blocking UI
- [ ] Pagination working correctly
- [ ] Search suggestions debouncing
- [ ] Emoji reactions aggregating correctly
- [ ] Threading/nested comments displaying properly

---

**Testing Completed**: _____________________  
**Tester Name**: _____________________  
**Issues Found**: _____________________  
**Sign-off**: _____________________
