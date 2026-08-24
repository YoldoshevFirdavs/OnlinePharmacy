# Security Guide

This project stores environment variables in `.env` and should never commit secrets to the repository. Keep `.env` local and rotate keys regularly.

## Required secret handling

- Store the Django secret key in `SECRET_KEY`
- Keep database credentials in environment variables only
- Do not commit bot tokens, OTP secret material, or production credentials
- Configure `DEBUG=False` in production

## OTP and 2FA

- OTP flows must be treated as temporary one-time credentials
- Expire codes quickly and store only hashed values when possible
- Add logout/session invalidation on suspicious activity
- Avoid logging raw phone numbers or secrets in application logs

## Recommended protections

- Use HTTPS everywhere in production
- Keep `ALLOWED_HOSTS` restricted to expected domains
- Use Postgres and Redis credentials from the environment layer
- Restrict admin access to trusted IPs or staff-only policies
- Ensure CSRF is sent for all state-changing requests

## Security checklist

- Run `python manage.py check`
- Confirm `DEBUG=False` in production
- Validate admin-only routes and API permission classes
- Review the `UndoLog` restore flow before production exposure
- Review logs and avoid exposing user data in stack traces
