"""
Custom Django form widgets for OnlinePharmacy
"""

from django import forms
from django.utils.html import format_html


class AvatarUploadWidget(forms.ClearableFileInput):
    """
    Custom avatar upload widget with preview
    - Shows current avatar path (no "Clear" checkbox)
    - File picker with validation
    - Shows uploaded file immediately
    """

    template_name = "dashboard/widgets/avatar_upload.html"

    def get_context(self, name, value, attrs):
        """Get context for template rendering"""
        context = super().get_context(name, value, attrs)

        # Add custom context
        context["widget"].update(
            {
                "show_clear": False,  # Hide Clear checkbox
            }
        )

        return context
