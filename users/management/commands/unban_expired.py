"""
Management command - vaqtli banlarni avtomatik ochish (User va Fingerprint)
Har daqiqada yoki har 5 daqiqada ishga tushadigan command
Enhanced to handle both user bans and fingerprint bans from cache
"""

import logging

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import CustomUser
from users.services import BanService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Vaqtli banlarni avtomatik ochish (ban_expires_at tugagan foydalanuvchilar va fingerprint banlar)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Hech nima o'zgartirmaydi, faqat qancha ban ochiladi ko'rsatadi",
        )
        parser.add_argument(
            "--fingerprints-only",
            action="store_true",
            help="Faqat fingerprint banlarni tekshiradi",
        )
        parser.add_argument(
            "--users-only",
            action="store_true",
            help="Faqat user banlarni tekshiradi",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        fingerprints_only = options.get("fingerprints_only", False)
        users_only = options.get("users_only", False)

        total_unbanned = 0

        try:
            # User banlarni tekshirish
            if not fingerprints_only:
                user_count = self._handle_user_bans(dry_run)
                total_unbanned += user_count

            # Fingerprint banlarni tekshirish
            if not users_only:
                fp_count = self._handle_fingerprint_bans(dry_run)
                total_unbanned += fp_count

            if total_unbanned == 0:
                self.stdout.write(self.style.SUCCESS("✓ Vaqti tugagan banlar yo'q - hamma faol"))
            else:
                self.stdout.write(self.style.SUCCESS(f"✓ Jami {total_unbanned} ta ban ochildi"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Xatolik: {str(e)}"))
            logger.error(f"[UNBAN] Management command error: {str(e)}")

    def _handle_user_bans(self, dry_run=False):
        """User banlarni tekshirish va ochish"""
        try:
            # Ban vaqti tugagan foydalanuvchilarni topish
            now = timezone.now()
            expired_bans = CustomUser.objects.filter(
                is_permanent_ban=False, ban_until__isnull=False, ban_until__lte=now, banned_for__isnull=False
            )

            count = expired_bans.count()

            if count == 0:
                self.stdout.write(self.style.SUCCESS("✓ Vaqti tugagan user banlar yo'q"))
                return 0

            self.stdout.write(f"📋 {count} ta user ban vaqti tugagan")

            # Dry run
            if dry_run:
                self.stdout.write(self.style.WARNING(f"[DRY RUN] {count} ta user ban ochiladi:"))
                for user in expired_bans:
                    self.stdout.write(f"  - User {user.id}: {user.email} (ban sababi: '{user.banned_for}')")
                return count

            # Haqiqiy unban
            for user in expired_bans:
                BanService.unban_user(user, actor=None)
                self.stdout.write(self.style.SUCCESS(f"✓ User {user.id} ({user.email}) unbanned"))

            logger.warning(f"[UNBAN] {count} expired user bans were removed by management command")
            return count

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ User ban tekshirishda xatolik: {str(e)}"))
            logger.error(f"[UNBAN] User bans error: {str(e)}")
            return 0

    def _handle_fingerprint_bans(self, dry_run=False):
        """Fingerprint banlarni cache-dan tekshirish va ochish"""
        try:
            # Redis cache-dagi fingerprint banlarni topish
            # This is a simplified approach - in production, you might want to use Redis SCAN
            expired_fps = []

            # Get all cache keys that match our pattern (this is simplified)
            # In a real implementation, you'd use Redis SCAN for better performance
            cache_keys = self._get_fingerprint_ban_keys()

            now = timezone.now()

            for key in cache_keys:
                if key.startswith("ban_fp:"):
                    ban_info = cache.get(key)
                    if ban_info and ban_info.get("ban_expires_at"):
                        try:
                            expires_at = timezone.datetime.fromisoformat(ban_info["ban_expires_at"])
                            if now >= expires_at:
                                fp = key.replace("ban_fp:", "")
                                expired_fps.append((fp, ban_info))
                        except (ValueError, TypeError) as e:
                            # Invalid timestamp format, skip
                            logger.warning(f"[UNBAN] Invalid timestamp in fingerprint ban {key}: {e}")
                            continue

            count = len(expired_fps)

            if count == 0:
                self.stdout.write(self.style.SUCCESS("✓ Vaqti tugagan fingerprint banlar yo'q"))
                return 0

            self.stdout.write(f"📋 {count} ta fingerprint ban vaqti tugagan")

            # Dry run
            if dry_run:
                self.stdout.write(self.style.WARNING(f"[DRY RUN] {count} ta fingerprint ban ochiladi:"))
                for fp, ban_info in expired_fps:
                    reason = ban_info.get("ban_reason", "Noma'lum")
                    self.stdout.write(f"  - Fingerprint {fp[:8]}...: {reason}")
                return count

            # Haqiqiy unban
            for fp, ban_info in expired_fps:
                success = BanService.unban_by_fp(fp, actor="management_command")
                if success:
                    reason = ban_info.get("ban_reason", "Noma'lum")
                    self.stdout.write(self.style.SUCCESS(f"✓ Fingerprint {fp[:8]}... unbanned (reason: {reason})"))

            logger.warning(f"[UNBAN] {count} expired fingerprint bans were removed by management command")
            return count

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Fingerprint ban tekshirishda xatolik: {str(e)}"))
            logger.error(f"[UNBAN] Fingerprint bans error: {str(e)}")
            return 0

    def _get_fingerprint_ban_keys(self):
        """
        Get all cache keys for fingerprint bans
        This is a simplified implementation - in production with Redis,
        you'd use SCAN command for better performance
        """
        try:
            # This is a workaround since Django cache doesn't expose key iteration
            # In production, you might want to use direct Redis connection
            from django.core.cache.backends.redis import RedisCache

            if isinstance(cache, RedisCache):
                # Direct Redis access for scanning keys
                redis_client = cache._cache.get_client(write=True)
                return [key.decode() for key in redis_client.scan_iter(match="ban_fp:*")]
            else:
                # Fallback for other cache backends - this is less efficient
                # but works for development/testing
                self.stdout.write(
                    self.style.WARNING("⚠️  Non-Redis cache detected - fingerprint ban cleanup might be limited")
                )
                return []

        except Exception as e:
            logger.error(f"[UNBAN] Error getting fingerprint ban keys: {str(e)}")
            return []
