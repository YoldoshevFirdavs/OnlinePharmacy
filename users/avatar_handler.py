"""
Avatar Upload Handler
Features: File validation, storage path handling
"""

import os
from datetime import datetime

from django.conf import settings
from django.core.files.storage import default_storage
from PIL import Image


class AvatarUploadHandler:
    """Handle avatar uploads with validation"""

    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_FORMATS = ["JPEG", "PNG", "GIF", "WEBP"]

    @staticmethod
    def validate_file(file_obj):
        """
        Validate avatar file
        Returns: (is_valid, error_message)
        """
        # Check file size
        if file_obj.size > AvatarUploadHandler.MAX_SIZE:
            error = f"Fayl hajmi 5MB dan oshmasligi kerak. Hozirgi: {file_obj.size / 1024 / 1024:.2f}MB"
            return False, error

        # Check file type
        if file_obj.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            error = f"Fayl turi noto'g'ri. Ruxsat etilgan: JPEG, PNG, GIF, WEBP."
            return False, error

        # Validate image format using PIL
        try:
            file_obj.seek(0)
            img = Image.open(file_obj)
            img.load()
        except Exception:
            return False, "Rasm fayl qayta ishlab bo'lmadi. Fayl buzilganmi?"

        return True, None

    @staticmethod
    def upload_avatar(user, file_obj):
        """
        Upload avatar file to storage
        Returns: (success, file_path, error_message)
        """
        # Validate file
        is_valid, validation_error = AvatarUploadHandler.validate_file(file_obj)
        if not is_valid:
            return False, None, validation_error

        try:
            # Reset file pointer before saving
            file_obj.seek(0)

            # Create storage directory path
            upload_dir = f"avatars/{user.id}"
            file_name = f"avatar_{datetime.now().timestamp()}.{file_obj.name.split('.')[-1]}"
            file_path = os.path.join(upload_dir, file_name)

            # Save file
            saved_path = default_storage.save(file_path, file_obj)

            # Update user avatar field
            user.avatar = saved_path
            user.save(update_fields=["avatar"])

            return True, saved_path, None

        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            return False, None, error_msg


def handle_avatar_upload(user, file_obj):
    """
    Convenience function to handle avatar upload
    Usage in views: success, path, error = handle_avatar_upload(user, file)
    """
    return AvatarUploadHandler.upload_avatar(user, file_obj)
