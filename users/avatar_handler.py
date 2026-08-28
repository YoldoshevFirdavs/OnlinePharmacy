"""
Avatar Upload Handler with Detailed Logging
Features: File validation, storage path logging, upload confirmation
"""

import logging
import os
from datetime import datetime
from io import BytesIO

from django.conf import settings
from django.core.files.storage import default_storage
from PIL import Image

logger = logging.getLogger("avatar_upload")

# Create handler if not exists
if not logger.handlers:
    handler = logging.FileHandler(os.path.join(settings.BASE_DIR, "logs", "avatar_upload.log"))
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


class AvatarUploadHandler:
    """Handle avatar uploads with validation and logging"""

    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_FORMATS = ["JPEG", "PNG", "GIF", "WEBP"]

    @staticmethod
    def log_upload_start(user, file_name, file_size, file_type):
        """Log when avatar upload starts"""
        logger.info(f"=== AVATAR UPLOAD START ===")
        logger.info(f"User: {user.id} ({user.email})")
        logger.info(f"File name: {file_name}")
        logger.info(f"File size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
        logger.info(f"File type: {file_type}")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")

    @staticmethod
    def validate_file(file_obj):
        """
        Validate avatar file
        Returns: (is_valid, error_message)
        """
        logger.debug(f"--- Validating file ---")

        # Check file size
        if file_obj.size > AvatarUploadHandler.MAX_SIZE:
            error = f"Fayl hajmi 5MB dan oshmasligi kerak. Hozirgi: {file_obj.size / 1024 / 1024:.2f}MB"
            logger.warning(f"Size validation failed: {error}")
            return False, error
        logger.debug(f"✓ File size valid: {file_obj.size / 1024:.2f} KB")

        # Check file type
        if file_obj.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            error = f"Fayl turi noto'g'ri. Ruxsat etilgan: JPEG, PNG, GIF, WEBP. Hozirgi: {file_obj.content_type}"
            logger.warning(f"Type validation failed: {error}")
            return False, error
        logger.debug(f"✓ File type valid: {file_obj.content_type}")

        # Validate image format using PIL
        try:
            img = Image.open(file_obj)
            img.verify()
            logger.debug(f"✓ Image format valid: {img.format}")
        except Exception as e:
            error = f"Rasm fayl qayta ishlab bo'lmadi. Xato: {str(e)}"
            logger.warning(f"Image verification failed: {error}")
            return False, error

        return True, None

    @staticmethod
    def upload_avatar(user, file_obj):
        """
        Upload avatar file to storage
        Returns: (success, file_path, error_message)
        """
        AvatarUploadHandler.log_upload_start(user, file_obj.name, file_obj.size, file_obj.content_type)

        # Validate file
        is_valid, validation_error = AvatarUploadHandler.validate_file(file_obj)
        if not is_valid:
            logger.error(f"Upload failed - Validation: {validation_error}")
            return False, None, validation_error

        try:
            logger.debug(f"Starting file upload...")

            # Create storage directory path
            upload_dir = f"avatars/{user.id}"
            file_name = f"avatar_{datetime.now().timestamp()}.{file_obj.name.split('.')[-1]}"
            file_path = os.path.join(upload_dir, file_name)

            logger.debug(f"Upload directory: {upload_dir}")
            logger.debug(f"File name: {file_name}")
            logger.debug(f"Storage path: {file_path}")

            # Save file
            saved_path = default_storage.save(file_path, file_obj)
            logger.info(f"✓ File saved successfully")
            logger.info(f"Saved path: {saved_path}")

            # Get full path for logging
            if hasattr(default_storage, "location"):
                full_path = os.path.join(default_storage.location, saved_path)
                logger.info(f"Full storage path: {full_path}")

            # Update user avatar field
            old_avatar = user.avatar.name if user.avatar else "None"
            user.avatar = saved_path
            user.save(update_fields=["avatar"])
            logger.info(f"✓ User avatar field updated")
            logger.info(f"Previous avatar: {old_avatar}")
            logger.info(f"New avatar: {user.avatar.name}")

            logger.info(f"=== AVATAR UPLOAD COMPLETE ===")
            logger.info(f"Result: SUCCESS\n")

            return True, saved_path, None

        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            logger.error(f"✗ {error_msg}")
            logger.error(f"Exception: {type(e).__name__}")
            logger.error(f"=== AVATAR UPLOAD FAILED ===\n")
            return False, None, error_msg


def handle_avatar_upload(user, file_obj):
    """
    Convenience function to handle avatar upload
    Usage in views: success, path, error = handle_avatar_upload(user, file)
    """
    return AvatarUploadHandler.upload_avatar(user, file_obj)
