# AUTH REPAIR PLAN — REVIEW & CONFIRMATION

This document provides a review and confirmation of the proposed authentication repair plan. The plan is sound, and this review offers clarifications based on the current state of the codebase.

---

### General Confirmation

The proposed plan is **approved**. It correctly identifies the key areas for improvement: consolidating verification logic, ensuring robust session management, and cleaning up frontend flows. The high-level steps are logical and cover all necessary changes in the specified scope.

---

### Point-by-Point Analysis

#### 1. **Inventory (Inventarizatsiya)**
-   **Status:** **Approved.**
-   **Comment:** This is the correct first step. The previous audit already produced `docs/auth_api_overview.md` and `docs/otp_service_functions.md`, which serve as an excellent foundation for this. We can use these documents to confirm the current state before making changes.

#### 2. **Create `CheckSessionView`**
-   **Status:** **Approved & Already Implemented.**
-   **Comment:** This is a critical feature for a modern frontend. The good news is that this functionality already exists and works as described in the plan.
    -   **View:** `users/views.py` contains `CheckSessionView`.
    -   **URL:** `users/urls.py` has the path `login/check-session/`.
    -   **Behavior:** It correctly uses `IsAuthenticated` and `UserPublicSerializer` to return `{ "ok": true, "user": {...} }` on success and `401` on failure.
-   **Action:** No new implementation is needed. We just need to ensure the frontend uses it correctly.

#### 3. **Consolidate `VerifyOtpView` (Non-Admin)**
-   **Status:** **Approved with a key recommendation.**
-   **Comment:** The goal to have a single, unified verification endpoint for all non-admin users is absolutely correct. The existing `VerifyOtpView` in `users/views.py` is already designed for this exact purpose. It's robust, handles different OTP sources via `otp_service.verify_otp_once`, determines user roles, and generates JWT tokens.
-   **Recommendation:** Instead of creating a *new* `VerifyOtpView` or significantly altering the existing one's signature, we should **adapt the frontend to use the existing `VerifyOtpView`**.
    -   The current `VerifyOtpView` expects a `session_id` and `code`.
    -   The frontend (`auth.js`) already receives and stores a `session_id` when it calls `EmailLoginView` or `TelegramLoginView`.
    -   The logic for creating a new user is correctly placed in `EmailLoginView` and `TelegramLoginView` (`get_or_create`). This follows the Single Responsibility Principle, where the verification step is only responsible for verifying, not creating.
-   **Action:** The primary work will be in `static/js/auth.js` to ensure that after getting a `session_id`, it always calls `POST /api/v1/users/login/verify-otp/` with the `{ session_id, code }` payload. The backend view is already fit for purpose.

#### 4. **Frontend Changes**
-   **Status:** **Approved.**
-   **Comment:** This is a crucial part of the plan.
    -   **Session Polling:** The periodic session checker is **already implemented** in `static/js/header.js` as a result of the previous audit. It correctly calls `check-session` and triggers a logout.
    -   **Token Propagation:** The `sendRequest` utility in `static/js/utils.js` (inlined in `header.js` and `auth.js`) already correctly includes the `Authorization: Bearer <token>` header.
    -   **Redirect Logic:** The `getRedirectUrlByRole` function was added to `auth.js` to centralize role-based redirection. This should be used consistently.
-   **Action:** The main task is to refactor `auth.js` to use the unified `VerifyOtpView` as mentioned in point #3 and ensure the success callback correctly uses `getRedirectUrlByRole`.

#### 5. **Identify Redundant Views**
-   **Status:** **Approved.**
-   **Comment:** Based on the inventory, here are the primary candidates for discussion:
    -   **`RegistrationView`:** This view's functionality (`get_or_create` user and initiate OTP) is largely duplicated by `EmailLoginView` and `TelegramLoginView`. If the frontend exclusively uses the latter two, `RegistrationView` could potentially be deprecated or removed.
    -   **`DetermineRoleView`:** The frontend currently relies on this to show the correct UI (e.g., password field for admins). While the plan suggests integrating this logic, the current approach is valid and decoupled. Removing it would require a larger frontend refactor. **Recommendation:** Keep `DetermineRoleView` for now, as it serves a clear purpose in the current UI flow and is robust (it creates a user if one doesn't exist).

#### 6. **Testing**
-   **Status:** **Approved.**
-   **Comment:** The proposed testing plan is comprehensive and covers backend syntax, frontend builds, and critical user flows. This is essential.

---

### Summary & Next Steps

The plan is excellent. The key takeaway from this review is that several components (`CheckSessionView`, frontend polling) are already in place, which simplifies the work.

The recommended execution order is:
1.  **Confirm Frontend Flow:** Double-check that `static/js/auth.js` is the only place initiating login and verification.
2.  **Refactor `auth.js`:** Modify the OTP verification logic to consistently call the existing `VerifyOtpView` (`/api/v1/users/login/verify-otp/`) for all non-admin logins.
3.  **Review `RegistrationView`:** Decide whether to deprecate `RegistrationView` based on its usage in the frontend.
4.  **Execute Tests:** Run the full testing plan as described.

This approach minimizes backend changes and focuses the effort on the frontend, where the consolidation is most needed.