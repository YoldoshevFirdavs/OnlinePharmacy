# UI Testing Checklist - Pharmacy Platform

**Date**: ________________  
**Tester**: ________________  
**Browser**: ________________  
**Device**: ________________  

---

## Shop Page (`/shop/`)

### Page Load & Layout
- [ ] Page loads without errors
- [ ] Search field visible at top
- [ ] Filter panel visible on left (collapsible on mobile)
- [ ] Product grid displays correctly
- [ ] Footer visible at bottom
- [ ] No console errors

### Search Functionality
- [ ] Type in search field → suggestions appear (150ms delay)
- [ ] Suggestions show: name, price, rating, image
- [ ] Click suggestion → navigate to product detail
- [ ] Search persists across page navigation
- [ ] Empty search shows all products

### Filtering
- [ ] Category filter works (updates grid)
- [ ] Price range slider works
- [ ] Brand filter works
- [ ] Rating filter works
- [ ] Multiple filters combine correctly
- [ ] "Clear filters" button resets all

### Product Grid
- [ ] 24 products displayed per page
- [ ] Each card shows: image (lazy-load), name, rating, seller, price
- [ ] Click card → navigate to product detail
- [ ] Cards are responsive (stack on mobile)
- [ ] Images load correctly (no broken images)

### Sorting
- [ ] Click "Reference" button → sort dropdown appears
- [ ] All 8 sort options work:
  - [ ] Most sold
  - [ ] Most viewed
  - [ ] A-Z
  - [ ] Z-A
  - [ ] Most expensive
  - [ ] Least expensive
  - [ ] Best rated
  - [ ] Most reviews
- [ ] Grid updates after sorting

### Pagination
- [ ] Pagination visible at bottom
- [ ] "Next" button works
- [ ] "Previous" button works
- [ ] Page number displays correctly
- [ ] Clicking pagination maintains filters

---

## Product Detail Page (`/products/<id>/`)

### Layout
- [ ] Left side: product image with controls
- [ ] Right side: product info panel
- [ ] Comments section below

### Product Image
- [ ] Image displays clearly
- [ ] Image dimensions responsive
- [ ] Lazy-load works (check Network tab)

### Product Info
- [ ] Seller avatar + name visible
- [ ] Seller name is clickable (→ seller page)
- [ ] Rating displayed with stars
- [ ] Description text readable
- [ ] Red warning block present (side effects, etc.)

### Quantity Selector
- [ ] "+" button increases quantity
- [ ] "-" button decreases quantity
- [ ] Quantity has min=1, max=stock
- [ ] Cannot go negative

### Add to Cart
- [ ] "Add to cart" button clickable
- [ ] Click → animation plays (pop effect)
- [ ] Toast notification appears
- [ ] Notification disappears after 3s

### Full Guide Button
- [ ] Button visible
- [ ] Click → navigate to `/products/<id>/full/`
- [ ] New page shows: Instruction, Storage, Side Effects, Contraindications

---

## Comments Section (YouTube-style)

### Comment Form (Authenticated)
- [ ] Form visible
- [ ] Star rating selector visible (1-5)
- [ ] Textarea for comment text
- [ ] "Post Comment" button
- [ ] "Clear" button

### Create Comment
- [ ] Type comment text
- [ ] Select rating (e.g., 5 stars)
- [ ] Click "Post Comment"
- [ ] Comment appears at top of list
- [ ] User avatar + name + timestamp displayed
- [ ] Rating badge shown

### Comment Display
- [ ] Comment text displays correctly
- [ ] User avatar shown
- [ ] Username shown (or seller badge)
- [ ] Timestamp shown (relative: "2 hours ago")
- [ ] Like count visible (if > 0)
- [ ] Nested replies indented

### Replies (Threaded)
- [ ] Hover comment → "Reply" button appears
- [ ] Click "Reply" → reply form opens (indented)
- [ ] Type reply text
- [ ] Click "Reply" → reply appears nested
- [ ] Reply has NO rating selector
- [ ] Reply shows user info + timestamp

### Emoji Reactions
- [ ] Hover comment → emoji reactions bar appears
- [ ] "😊 React" button visible
- [ ] Click button → emoji picker popup
- [ ] 6 emojis shown: 👍❤️😂😮😢😠
- [ ] Click emoji → reaction added
- [ ] Reaction counter increments
- [ ] Hover again → shows active reaction

### Edit Comment (Author Only)
- [ ] Hover own comment → "⋮" menu appears
- [ ] Click menu → "Edit" option visible
- [ ] Click "Edit" → edit form opens
- [ ] Edit textarea populated with current text
- [ ] Click "Save" → comment updates
- [ ] Timestamp shows "edited"

### Delete Comment (Author Only)
- [ ] Hover own comment → "⋮" menu
- [ ] Click menu → "Delete" option
- [ ] Confirmation dialog appears
- [ ] Click "Confirm" → comment removed
- [ ] Comment disappears from list

### Cannot Edit Others' Comments
- [ ] Hover others' comment → "⋮" menu NOT visible
- [ ] Try API PATCH endpoint → 403 Forbidden

### Comment Pagination
- [ ] Comments paginated (50 per page)
- [ ] Pagination controls at bottom
- [ ] Click "Next" → loads more comments
- [ ] Comments preserve order (newest first)

---

## Seller Page (`/sellers/<id>/`)

### Layout & Header
- [ ] Large seller avatar with gradient background
- [ ] Shop name displayed prominently
- [ ] Stats visible: Rating, Sells, Reviews

### About Section
- [ ] Shop description visible
- [ ] Contact info shown (email, phone)
- [ ] Website link (if provided)

### Products Grid
- [ ] Seller's products displayed
- [ ] Click product → navigate to detail page
- [ ] Products load responsively
- [ ] Lazy-load images

---

## Admin Analytics Dashboard (`/dashboard/admin/analytics/`)

### Metrics Cards
- [ ] Total Orders card
- [ ] Pending Orders card
- [ ] Delivered Orders card
- [ ] Total Revenue card
- [ ] Total Products card
- [ ] Out of Stock card
- [ ] Total Users card
- [ ] Total Comments card
- [ ] Unapproved Comments card

### Charts
- [ ] Daily Orders line chart (30 days)
- [ ] Daily Revenue bar chart (30 days)
- [ ] Order Status Distribution pie chart
- [ ] All charts render without errors

### Auto-Refresh (60 seconds)
- [ ] Load dashboard
- [ ] Wait 60 seconds
- [ ] Charts refresh automatically
- [ ] Timestamp updates
- [ ] No page reload

---

## Admin User History Page (`/dashboard/admin/user/<id>/history/`)

### Page Load
- [ ] User info displayed (name, email)
- [ ] History table visible

### History Table
- [ ] Timestamp column shows date+time
- [ ] Action column shows action type
- [ ] Product column shows product name (if applicable)
- [ ] Details column shows metadata (qty, rating, etc.)
- [ ] IP Address column visible

### Pagination
- [ ] 50 items per page
- [ ] "Next"/"Previous" buttons work
- [ ] Page number displays correctly

---

## Admin Order Detail Page (`/dashboard/admin/user/<id>/order/<id>/`)

### Order Info
- [ ] Order ID displayed
- [ ] Order status shown (with color badge)
- [ ] Total price displayed
- [ ] Created date shown
- [ ] Last updated date shown

### Customer Info
- [ ] Customer name displayed
- [ ] Email address shown
- [ ] Phone number shown

### Line Items Table
- [ ] Product name column
- [ ] Quantity column
- [ ] Unit price column
- [ ] Subtotal column (qty × price)

### Order Summary
- [ ] Subtotal calculated correctly
- [ ] Total matches order amount

---

## Responsive Design

### Desktop (1920px)
- [ ] All elements properly spaced
- [ ] Multi-column layouts working
- [ ] No horizontal scroll

### Tablet (768px)
- [ ] Filter panel collapses to sidebar
- [ ] Product grid shows 2-3 columns
- [ ] All text readable
- [ ] Touch targets ≥ 44px

### Mobile (375px)
- [ ] Filter panel collapses to menu
- [ ] Product grid shows 1-2 columns
- [ ] Comments stack properly
- [ ] All buttons clickable
- [ ] Images scale appropriately

---

## Performance

### Load Times
- [ ] Shop page FCP (First Contentful Paint): < 1.5s
- [ ] Product detail FCP: < 1.5s
- [ ] Analytics dashboard FCP: < 2s

### Image Loading
- [ ] Images lazy-load on scroll
- [ ] No layout shift during image load
- [ ] Images display crisp on all devices

### API Requests
- [ ] Search suggestions debounced (150ms)
- [ ] No duplicate requests
- [ ] Pagination loads < 500ms
- [ ] Admin analytics loads < 1s

### AJAX & Animations
- [ ] UI not blocked during API calls
- [ ] Loading spinners display
- [ ] Add-to-cart animation smooth
- [ ] Comment posting smooth

---

## Security & Authorization

### Authentication
- [ ] Cannot comment without login
- [ ] Cannot access history without login
- [ ] Cannot access admin pages without staff status

### Authorization
- [ ] Cannot edit others' comments
- [ ] Cannot delete others' comments
- [ ] Cannot modify history records
- [ ] Cannot access other users' history

---

## Cross-browser Testing

### Chrome (latest)
- [ ] All tests pass: ✅ / ❌

### Firefox (latest)
- [ ] All tests pass: ✅ / ❌

### Safari (latest)
- [ ] All tests pass: ✅ / ❌

### Edge (latest)
- [ ] All tests pass: ✅ / ❌

### Mobile Safari (iOS)
- [ ] All tests pass: ✅ / ❌

### Chrome Mobile (Android)
- [ ] All tests pass: ✅ / ❌

---

## Console & Network

### Console Errors
- [ ] No JavaScript errors
- [ ] No 404s for images
- [ ] No CORS errors
- [ ] No deprecation warnings

### Network Tab
- [ ] All CSS/JS files load
- [ ] Images load (check for 404s)
- [ ] API responses 200/201/204
- [ ] No slow requests (> 5s)

---

## Accessibility

- [ ] Images have alt text
- [ ] Form labels present
- [ ] Color contrast sufficient
- [ ] Keyboard navigation works
- [ ] ARIA labels appropriate

---

## Bug Reports

### Issue #1
**Component**: _____  
**Description**: _____  
**Steps**: _____  
**Expected**: _____  
**Actual**: _____  
**Severity**: Critical / High / Medium / Low  

### Issue #2
**Component**: _____  
**Description**: _____  
**Steps**: _____  
**Expected**: _____  
**Actual**: _____  
**Severity**: Critical / High / Medium / Low  

---

## Sign-off

**Total Checks**: ___/___  
**Passed**: ___  
**Failed**: ___  

**Overall Status**: ✅ PASS / ❌ FAIL  

**Comments**: _____________________________________________________________________  

**Tester Signature**: ________________________  
**Date**: ________________________
