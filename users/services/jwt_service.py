"""
JWT token management service - extracted from large views module.
Handles token generation, validation, rotation, and blacklisting.
"""

import logging
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


class JWTService:
    """Service for JWT token operations"""

    @staticmethod
    def create_tokens_for_user(user) -> Dict[str, str]:
        """
        Create JWT tokens for a user.

        Args:
            user: Django user instance

        Returns:
            Dictionary with 'access' and 'refresh' tokens
        """
        try:
            refresh = RefreshToken.for_user(user)
            return {"access": str(refresh.access_token), "refresh": str(refresh)}
        except Exception as e:
            logger.error(f"Failed to create tokens for user {user.id}: {e}")
            raise

    @staticmethod
    def validate_refresh_token(refresh_token: str) -> Tuple[bool, Optional[RefreshToken], str]:
        """
        Validate a refresh token.

        Args:
            refresh_token: Refresh token string

        Returns:
            Tuple of (is_valid, token_object, error_message)
        """
        try:
            token = RefreshToken(refresh_token)
            token.check_exp()  # Check if token is expired
            return True, token, ""
        except TokenError as e:
            logger.warning(f"Token validation failed: {e}")
            return False, None, str(e)
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            return False, None, "Invalid token"

    @staticmethod
    def rotate_refresh_token(old_token: RefreshToken) -> Tuple[str, str]:
        """
        Rotate refresh token (create new refresh token).

        Args:
            old_token: Valid RefreshToken instance

        Returns:
            Tuple of (new_access_token, new_refresh_token)
        """
        try:
            # Create new tokens with rotation
            new_access_token = str(old_token.access_token)
            new_refresh_token = str(old_token)

            # Blacklist old token if rotation is enabled
            if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION", True):
                old_token.blacklist()

            return new_access_token, new_refresh_token
        except Exception as e:
            logger.error(f"Token rotation failed: {e}")
            raise

    @staticmethod
    def blacklist_token(refresh_token: str) -> bool:
        """
        Blacklist a refresh token (logout).

        Args:
            refresh_token: Token string to blacklist

        Returns:
            True if successful, False otherwise
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"Token blacklisted successfully")
            return True
        except TokenError as e:
            logger.warning(f"Cannot blacklist invalid token: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during token blacklisting: {e}")
            return False

    @staticmethod
    def get_cookie_settings() -> Dict:
        """
        Get cookie settings from Django settings.

        Returns:
            Dictionary with cookie configuration
        """
        jwt_settings = settings.SIMPLE_JWT
        return {
            "httponly": True,
            "secure": jwt_settings.get("AUTH_COOKIE_SECURE", True),
            "samesite": jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
            "max_age": jwt_settings.get("REFRESH_TOKEN_LIFETIME").total_seconds(),
        }
