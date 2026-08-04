# OTP Service Functions Overview

This document lists all functions in `users/otp_service.py` and their purpose.

---

### Core OTP & Session Functions

-   `def generate_numeric_code(length: int) -> str`
    -   **Description:** Generates a cryptographically secure numeric string of a given length.
    -   **Side-effects:** None.

-   `def generate_session_id() -> str`
    -   **Description:** Generates a URL-safe random string for use as a session ID.
    -   **Side-effects:** None.

-   `def hash_otp_with_salt(otp: str, salt: Optional[str]) -> Tuple[str, str]`
    -   **Description:** Hashes an OTP string with a new or provided salt using SHA256.
    -   **Side-effects:** None.

-   `def verify_otp_code(provided_code: str, otp_hash_obj: OtpHash) -> bool`
    -   **Description:** Securely compares a provided code against a stored `OtpHash` object using a constant-time comparison to prevent timing attacks.
    -   **Side-effects:** None.

-   `def create_otp_session(purpose: str, *args, **kwargs)`
    -   **Description:** Creates an `OtpSession` data object containing a new session ID and purpose (`telegram` or `email`).
    -   **Side-effects:** None (returns an object).

-   `def bind_session_to_user(session_id: str, user_id: int, identifier: str, ttl: int) -> bool`
    -   **Description:** Stores session metadata (user ID, identifier) in the cache, linking it to a session ID for a specified time-to-live (TTL).
    -   **Side-effects:** Writes to Django cache (key: `auth_session:<session_id>`).

-   `def get_session_meta(session_id: str) -> Optional[Dict[str, Any]]`
    -   **Description:** Retrieves session metadata from the cache by its session ID.
    -   **Side-effects:** Reads from Django cache.

-   `def delete_session(session_id: str) -> bool`
    -   **Description:** Deletes session metadata from the cache.
    -   **Side-effects:** Deletes from Django cache.

### OTP Storage & Retrieval

-   `def store_otp_hash(identifier: str, otp_hash_obj: OtpHash, ttl: int) -> bool`
    -   **Description:** Stores a serialized `OtpHash` object in the cache, keyed by the user's identifier (e.g., email or phone number).
    -   **Side-effects:** Writes to Django cache (key: `otp_code:<identifier>`).

-   `def get_otp_hash(identifier: str) -> Optional[OtpHash]`
    -   **Description:** Retrieves and deserializes an `OtpHash` object from the cache using the user's identifier.
    -   **Side-effects:** Reads from Django cache.

-   `def delete_otp(identifier: str) -> bool`
    -   **Description:** Deletes a stored OTP hash from the cache, typically after successful verification.
    -   **Side-effects:** Deletes from Django cache.

-   `def store_bot_otp(session_id: str, otp_code: str, ttl: int) -> bool`
    -   **Description:** Hashes and stores an OTP specifically for the Telegram bot flow, keyed by session ID.
    -   **Side-effects:** Writes to Django cache (key: `otp:<session_id>:telegram`).

-   `def get_bot_otp(session_id: str) -> Optional[OtpHash]`
    -   **Description:** Retrieves a stored Telegram bot OTP from the cache.
    -   **Side-effects:** Reads from Django cache.

### Admin-Specific Functions

-   `def create_admin_session(identifier: str, user_id: int) -> Dict[str, Any]`
    -   **Description:** Creates and stores metadata for an admin-specific login session in the cache.
    -   **Side-effects:** Writes to Django cache (key: `admin_session:<session_id>`).

-   `def get_admin_session_meta(session_id: str) -> Optional[Dict[str, Any]]`
    -   **Description:** Retrieves admin session metadata from the cache.
    -   **Side-effects:** Reads from Django cache.

-   `def delete_admin_session(session_id: str) -> None`
    -   **Description:** Deletes an admin session from the cache.
    -   **Side-effects:** Deletes from Django cache.

-   `def store_admin_code_hash(session_id: str, code: str, ttl: int) -> bool`
    -   **Description:** Stores a hashed OTP for an admin session, keyed by the session ID.
    -   **Side-effects:** Writes to Django cache (key: `admin_code:<session_id>`).

-   `def get_admin_code_hash(session_id: str) -> Optional[OtpHash]`
    -   **Description:** Retrieves a hashed admin OTP from the cache.
    -   **Side-effects:** Reads from Django cache.

-   `def delete_admin_code(session_id: str) -> None`
    -   **Description:** Deletes a stored admin OTP from the cache.
    -   **Side-effects:** Deletes from Django cache.

-   `def verify_admin_code(session_id: str, provided_code: str) -> Tuple[bool, Optional[Dict[str, Any]]]`
    -   **Description:** Verifies an admin OTP and returns the associated session metadata on success.
    -   **Side-effects:** Reads from Django cache.

### Security & Rate Limiting

-   `def is_banned(identifier: str) -> bool`
    -   **Description:** Checks if an identifier (IP, email) is currently in a temporary lockout period for failed admin login attempts.
    -   **Side-effects:** Reads from Django cache.

-   `def record_failed_attempt(identifier: str) -> bool`
    -   **Description:** Increments the failed login attempt counter for an admin. Bans the identifier if the attempt threshold is reached.
    -   **Side-effects:** Writes to Django cache (both an attempt counter and a ban flag).

-   `def reset_failed_attempts(identifier: str)`
    -   **Description:** Clears the failed attempt counter and any active ban for an admin identifier upon successful login.
    -   **Side-effects:** Deletes from Django cache.

-   `def verify_otp_once(session_id: str, provided_code: str, identifier: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]`
    -   **Description:** A comprehensive function to verify a user's OTP. It finds the session, finds the correct OTP hash (for email or bot), verifies the code, and cleans up the cache on success.
    -   **Side-effects:** Reads from and deletes from Django cache.

-   `def check_rate_limit(scope: str, window: int) -> Tuple[bool, int]`
    -   **Description:** A generic rate-limiting checker used to prevent abuse of OTP requests.
    -   **Side-effects:** Reads from and writes to Django cache.
