// tokenStore.js
let _accessToken = localStorage.getItem('access_token') || null;

export function getAccessToken() {
  return _accessToken;
}

export function setAccessToken(token) {
  _accessToken = token;
  if (token) {
    localStorage.setItem('access_token', token);
  } else {
    localStorage.removeItem('access_token');
  }
}

export function clearAuthTokens() {
  setAccessToken(null);
  // Assuming refresh token is handled by HttpOnly cookies and not directly in JS localStorage
  // If there are other tokens in localStorage, clear them here.
}
