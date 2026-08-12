// @ts-check
const { test, expect } = require('@playwright/test');

// Base URL for your Django development server
const BASE_URL = 'http://localhost:8000';

test.describe('Authentication Flow', () => {

  test.beforeEach(async ({ page }) => {
    // Mock grecaptcha.execute for all tests to prevent actual reCAPTCHA calls
    // and control its behavior for conditional tests.
    await page.addInitScript(() => {
      window.grecaptcha = {
        execute: async (siteKey, options) => {
          console.log('Mock grecaptcha.execute called with:', siteKey, options);
          // Return a mock token for successful reCAPTCHA execution
          return 'mock_recaptcha_token_from_e2e';
        }
      };
      window.RECAPTCHA_SITE_KEY = 'mock_site_key'; // Ensure site key is present
    });

    // Navigate to the authentication page before each test
    await page.goto(`${BASE_URL}/auth/`);
  });

  test('should display email login form by default', async ({ page }) => {
    await expect(page.locator('#emailInput')).toBeVisible();
    await expect(page.locator('#telegramAuthSection')).toBeHidden();
    await expect(page.locator('#btnEmail')).toHaveClass(/active/);
  });

  test('should switch to Telegram auth section', async ({ page }) => {
    await page.locator('#btnTelegram').click();
    await expect(page.locator('#telegramSection')).toBeVisible();
    await expect(page.locator('#emailSection')).toBeHidden();
    await expect(page.locator('#btnTelegram')).toHaveClass(/active/);
  });

  test('should show error for empty email submission', async ({ page }) => {
    await page.locator('#emailBtn').click();
    const errorMessage = page.locator('#email-error-message');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toHaveText(/Email manzilini kiriting./);
  });

  test('should successfully request OTP for a valid email', async ({ page }) => {
    // Mock the API response for sending OTP
    await page.route('**/api/v1/users/login/email/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Kod yuborildi', session_id: 'mock_session_id_123', otp_code: '123456' }),
      });
    });

    await page.locator('#nameInput').fill('Test User');
    await page.locator('#emailInput').fill('test@example.com');
    await page.locator('#emailBtn').click();

    const authFeedback = page.locator('#auth-feedback');
    await expect(authFeedback).toBeVisible();
    await expect(authFeedback).toHaveText(/Kod yuborildi/);
    await expect(authFeedback).toHaveClass(/success/);

    const otpArea = page.locator('#otp-area');
    await expect(otpArea).toBeVisible();
    await expect(page.locator('#otp-input')).toBeVisible();
    await expect(page.locator('#timer')).toBeVisible();
  });

  test('should show error for failed OTP request', async ({ page }) => {
    // Mock the API response for sending OTP
    await page.route('**/api/v1/users/login/email/', async route => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Xatolik yuz berdi' }),
      });
    });

    await page.locator('#nameInput').fill('Test User');
    await page.locator('#emailInput').fill('invalid-email');
    await page.locator('#emailBtn').click();

    const authFeedback = page.locator('#auth-feedback');
    await expect(authFeedback).toBeVisible();
    await expect(authFeedback).toHaveText(/Xatolik yuz berdi/);
    await expect(authFeedback).toHaveClass(/error/);
    await expect(page.locator('#otp-area')).toBeHidden();
  });

  test('should successfully verify OTP and redirect', async ({ page }) => {
    // First, simulate OTP request
    await page.route('**/api/v1/users/login/email/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Kod yuborildi', session_id: 'mock_session_id_123', otp_code: '123456' }),
      });
    });
    await page.locator('#nameInput').fill('Test User');
    await page.locator('#emailInput').fill('test@example.com');
    await page.locator('#emailBtn').click();
    await expect(page.locator('#otp-area')).toBeVisible();

    // Mock the API response for OTP verification
    await page.route('**/api/v1/users/verify-otp/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          next: `${BASE_URL}/account/`,
          access: 'mock_access_token',
          refresh: 'mock_refresh_token',
        }),
      });
    });

    await page.locator('#otp-input').fill('123456');
    await page.locator('#otp-submit').click();

    const authFeedback = page.locator('#auth-feedback');
    await expect(authFeedback).toBeVisible();
    await expect(authFeedback).toHaveText(/Muvaffaqiyatli kirish/);
    await expect(authFeedback).toHaveClass(/success/);

    // Expect redirection
    await page.waitForURL(`${BASE_URL}/account/`);
    expect(page.url()).toBe(`${BASE_URL}/account/`);
  });

  test('should show error for invalid OTP submission', async ({ page }) => {
    // First, simulate OTP request
    await page.route('**/api/v1/users/login/email/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Kod yuborildi', session_id: 'mock_session_id_123', otp_code: '123456' }),
      });
    });
    await page.locator('#nameInput').fill('Test User');
    await page.locator('#emailInput').fill('test@example.com');
    await page.locator('#emailBtn').click();
    await expect(page.locator('#otp-area')).toBeVisible();

    // Mock the API response for failed OTP verification
    await page.route('**/api/v1/users/verify-otp/', async route => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Noto‘g‘ri kod' }),
      });
    });

    await page.locator('#otp-input').fill('654321'); // Incorrect OTP
    await page.locator('#otp-submit').click();

    const otpErrorMessageModal = page.locator('#otp-error-message-modal');
    await expect(otpErrorMessageModal).toBeVisible();
    await expect(otpErrorMessageModal).toHaveText(/Noto‘g‘ri kod./);
    await expect(page.locator('#otp-area')).toBeVisible(); // Modal should remain open
  });

  test('should resend OTP', async ({ page }) => {
    // First, simulate OTP request
    await page.route('**/api/v1/users/login/email/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Kod yuborildi', session_id: 'mock_session_id_123', otp_code: '123456' }),
      });
    });
    await page.locator('#nameInput').fill('Test User');
    await page.locator('#emailInput').fill('test@example.com');
    await page.locator('#emailBtn').click();
    await expect(page.locator('#otp-area')).toBeVisible();

    // Mock the API response for resending OTP
    await page.route('**/api/v1/users/login/email/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Yangi kod yuborildi.', session_id: 'mock_session_id_456', otp_code: '654321' }),
      });
    });

    // Simulate timer expiring or click resend link if visible
    // For testing, we can directly click the resend link if it's made visible for testing purposes
    // Or, we can just click it and assume the backend handles the resend logic.
    // The resend link is initially hidden and becomes visible after timer expires.
    // To test this, we can force its visibility or wait for timer. For E2E, waiting is more realistic.
    // However, for a quick test, we can just click it.
    // Let's assume the timer has expired for this test.
    await page.locator('#resend-link').click();

    const authFeedback = page.locator('#auth-feedback');
    await expect(authFeedback).toBeVisible();
    await expect(authFeedback).toHaveText(/Yangi kod yuborildi./);
    await expect(authFeedback).toHaveClass(/success/);
    // Timer should restart, resend link should be hidden again
    await expect(page.locator('#resend-link')).toHaveClass(/hidden/);
  });

  test('should close OTP modal', async ({ page }) => {
    // First, simulate OTP request to open modal
    await page.route('**/api/v1/users/login/email/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Kod yuborildi', session_id: 'mock_session_id_123', otp_code: '123456' }),
      });
    });
    await page.locator('#nameInput').fill('Test User');
    await page.locator('#emailInput').fill('test@example.com');
    await page.locator('#emailBtn').click();
    await expect(page.locator('#otp-area')).toBeVisible();

    await page.locator('#closeOtpAreaBtn').click();
    await expect(page.locator('#otp-area')).toBeHidden();
    await expect(page.locator('#otp-input')).toHaveValue(''); // OTP input should be cleared
  });

  // --- Conditional reCAPTCHA E2E Tests ---

  test('should send X-Incognito: true header and recaptcha token when in simulated incognito mode', async ({ page }) => {
    // Stub browser APIs to simulate incognito mode
    await page.addInitScript(() => {
      // Chrome/Edge heuristic: temporary filesystem API
      window.RequestFileSystem = undefined;
      window.webkitRequestFileSystem = undefined;

      // Safari/other heuristics fallback: indexedDB
      // We need to make indexedDB.open('test') fail to simulate incognito
      const originalIndexedDBOpen = indexedDB.open;
      indexedDB.open = (name) => {
        const request = originalIndexedDBOpen(name); // Call original to get a valid IDBRequest object
        if (name === 'test') {
          setTimeout(() => {
            // Manually trigger onerror to simulate incognito detection
            const errorEvent = new Event('error');
            Object.defineProperty(errorEvent, 'target', { value: request });
            Object.defineProperty(request, 'error', { value: new DOMException('QuotaExceededError', 'QuotaExceededError') });
            if (request.onerror) {
              request.onerror(errorEvent);
            }
          }, 0); // Execute immediately after the current task
        }
        return request;
      };
    });

    // Re-navigate after adding init script for incognito simulation
    await page.goto(`${BASE_URL}/auth/`);

    // Switch to Telegram auth section
    await page.locator('#btnTelegram').click();

    // Intercept the login request to check headers and payload
    const [request] = await Promise.all([
      page.waitForRequest(req => req.url().includes('/api/v1/users/login/telegram/') && req.method() === 'POST'),
      page.route('**/api/v1/users/login/telegram/', async route => {
        // Mock a successful response from the backend
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Kod yuborildi', session_id: 'mock_session_id_incognito', deeplink: 'https://t.me/testbot?start=mock_session_id_incognito' }),
        });
      }),
      page.locator('#nameInput').fill('Incognito User'),
      page.locator('#phoneInput').fill('998901234567'),
      page.locator('#telegramBtn').click(),
    ]);

    // Assert the request headers and payload
    expect(request.headers()['x-incognito']).toBe('true');
    const requestBody = JSON.parse(request.postData());
    expect(requestBody.incognito).toBe(true);
    expect(requestBody.recaptcha_token).toBe('mock_recaptcha_token_from_e2e'); // Should have the mocked token

    // Assert OTP modal opens
    await expect(page.locator('#otp-area')).toBeVisible();
    await expect(page.locator('#otp-input')).toBeVisible();
  });

  test('should NOT send X-Incognito header and recaptcha token when NOT in simulated incognito mode', async ({ page }) => {
    // No specific initScript for incognito simulation, so it should default to non-incognito.
    // The grecaptcha.execute mock is already in beforeEach, but it should not be called by frontend if not incognito.

    // Switch to Telegram auth section
    await page.locator('#btnTelegram').click();

    // Intercept the login request to check headers and payload
    const [request] = await Promise.all([
      page.waitForRequest(req => req.url().includes('/api/v1/users/login/telegram/') && req.method() === 'POST'),
      page.route('**/api/v1/users/login/telegram/', async route => {
        // Mock a successful response from the backend
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Kod yuborildi', session_id: 'mock_session_id_normal', deeplink: 'https://t.me/testbot?start=mock_session_id_normal' }),
        });
      }),
      page.locator('#nameInput').fill('Normal User'),
      page.locator('#phoneInput').fill('998901234567'),
      page.locator('#telegramBtn').click(),
    ]);

    // Assert the request headers and payload
    expect(request.headers()['x-incognito']).toBe('false');
    const requestBody = JSON.parse(request.postData());
    expect(requestBody.incognito).toBe(false);
    expect(requestBody.recaptcha_token).toBeUndefined(); // reCAPTCHA token should NOT be sent

    // Assert OTP modal opens
    await expect(page.locator('#otp-area')).toBeVisible();
    await expect(page.locator('#otp-input')).toBeVisible();
  });
});