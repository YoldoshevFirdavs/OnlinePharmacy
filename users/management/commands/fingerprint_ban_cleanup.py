"""
Management command - Fingerprint ban cleanup and statistics
Comprehensive fingerprint ban management with Redis integration
"""

import json
import logging

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone

from users.services import BanService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fingerprint ban tozalash va statistika (Redis cache bilan ishlash)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--stats",
            action="store_true",
            help="Fingerprint ban statistikasini ko'rsatish",
        )
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Vaqti tugagan fingerprint banlarni tozalash",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Hech nima o'zgartirmaydi, faqat qancha ban ochiladi ko'rsatadi",
        )
        parser.add_argument(
            "--clear-rate-limits",
            action="store_true",
            help="Barcha rate limiting counterlarni tozalash",
        )
        parser.add_argument(
            "--clear-ip-blocks",
            action="store_true",
            help="Barcha IP bloklarini tozalash",
        )
        parser.add_argument(
            "--fingerprint",
            type=str,
            help="Muayyan fingerprint haqida ma'lumot olish",
        )

    def handle(self, *args, **options):
        try:
            if options.get("stats"):
                self._show_stats()

            if options.get("cleanup"):
                self._cleanup_expired_bans(options.get("dry_run", False))

            if options.get("clear_rate_limits"):
                self._clear_rate_limits(options.get("dry_run", False))

            if options.get("clear_ip_blocks"):
                self._clear_ip_blocks(options.get("dry_run", False))

            if options.get("fingerprint"):
                self._show_fingerprint_info(options["fingerprint"])

            # Agar hech qanday argument berilmagan bo'lsa, default stats ko'rsatish
            if not any(
                [
                    options.get("stats"),
                    options.get("cleanup"),
                    options.get("clear_rate_limits"),
                    options.get("clear_ip_blocks"),
                    options.get("fingerprint"),
                ]
            ):
                self._show_stats()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Xatolik: {str(e)}"))
            logger.error(f"[FP_CLEANUP] Management command error: {str(e)}")

    def _show_stats(self):
        """Fingerprint ban statistikasini ko'rsatish"""
        try:
            self.stdout.write(self.style.SUCCESS("📊 Fingerprint Ban Statistikasi"))
            self.stdout.write("=" * 50)

            # Get Redis client
            redis_client = self._get_redis_client()
            if not redis_client:
                self.stdout.write(self.style.ERROR("Redis ulanishi yo'q"))
                return

            # Count different types of keys
            ban_keys = list(redis_client.scan_iter(match="ban_fp:*"))
            rate_keys = list(redis_client.scan_iter(match="rate_fp:*"))
            ip_block_keys = list(redis_client.scan_iter(match="ip_block:*"))
            user_mapping_keys = list(redis_client.scan_iter(match="fp_user:*"))
            main_page_keys = list(redis_client.scan_iter(match="main_page_fp:*"))

            self.stdout.write(f"🚫 Fingerprint banlar: {len(ban_keys)}")
            self.stdout.write(f"⚡ Rate limit counterlar: {len(rate_keys)}")
            self.stdout.write(f"🔒 IP bloklar: {len(ip_block_keys)}")
            self.stdout.write(f"👤 Fingerprint->User mapping: {len(user_mapping_keys)}")
            self.stdout.write(f"🏠 Main page counterlar: {len(main_page_keys)}")

            # Analyze ban details
            if ban_keys:
                self.stdout.write("\n📋 Ban tafsilotlari:")
                permanent_bans = 0
                temporary_bans = 0
                expired_bans = 0
                now = timezone.now()

                for key in ban_keys[:10]:  # Limit to first 10 for display
                    try:
                        ban_info_raw = redis_client.get(key)
                        if ban_info_raw:
                            ban_info = json.loads(ban_info_raw)
                            fp = key.decode().replace("ban_fp:", "")

                            if ban_info.get("is_permanent"):
                                permanent_bans += 1
                                status = "🔴 Permanent"
                            elif ban_info.get("ban_expires_at"):
                                expires_at = timezone.datetime.fromisoformat(ban_info["ban_expires_at"])
                                if now >= expires_at:
                                    expired_bans += 1
                                    status = "🟡 Expired"
                                else:
                                    temporary_bans += 1
                                    status = f'🟠 Expires: {expires_at.strftime("%Y-%m-%d %H:%M")}'
                            else:
                                status = "❓ Unknown"

                            reason = ban_info.get("ban_reason", "N/A")[:30]
                            self.stdout.write(f"  {fp[:8]}...: {status} - {reason}")
                    except Exception as e:
                        continue

                if len(ban_keys) > 10:
                    self.stdout.write(f"  ... va yana {len(ban_keys) - 10} ta")

                self.stdout.write(f"\n📈 Ban turlari:")
                self.stdout.write(f"  🔴 Permanent: {permanent_bans}")
                self.stdout.write(f"  🟠 Temporary: {temporary_bans}")
                self.stdout.write(f"  🟡 Expired: {expired_bans}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Statistika xatoligi: {str(e)}"))

    def _cleanup_expired_bans(self, dry_run=False):
        """Vaqti tugagan fingerprint banlarni tozalash"""
        try:
            self.stdout.write(self.style.SUCCESS("🧹 Vaqti tugagan fingerprint banlarni tozalash"))

            redis_client = self._get_redis_client()
            if not redis_client:
                self.stdout.write(self.style.ERROR("Redis ulanishi yo'q"))
                return

            ban_keys = list(redis_client.scan_iter(match="ban_fp:*"))
            expired_fps = []
            now = timezone.now()

            for key in ban_keys:
                try:
                    ban_info_raw = redis_client.get(key)
                    if ban_info_raw:
                        ban_info = json.loads(ban_info_raw)
                        if ban_info.get("ban_expires_at"):
                            expires_at = timezone.datetime.fromisoformat(ban_info["ban_expires_at"])
                            if now >= expires_at:
                                fp = key.decode().replace("ban_fp:", "")
                                expired_fps.append((fp, ban_info))
                except Exception as e:
                    continue

            if not expired_fps:
                self.stdout.write(self.style.SUCCESS("✓ Vaqti tugagan banlar yo'q"))
                return

            self.stdout.write(f"🔍 {len(expired_fps)} ta vaqti tugagan ban topildi")

            if dry_run:
                self.stdout.write(self.style.WARNING("[DRY RUN] Quyidagi banlar ochilar edi:"))
                for fp, ban_info in expired_fps:
                    reason = ban_info.get("ban_reason", "N/A")
                    expires = ban_info.get("ban_expires_at", "N/A")
                    self.stdout.write(f"  {fp[:8]}...: {reason} (expired: {expires})")
            else:
                for fp, ban_info in expired_fps:
                    success = BanService.unban_by_fp(fp, actor="cleanup_command")
                    if success:
                        reason = ban_info.get("ban_reason", "N/A")
                        self.stdout.write(self.style.SUCCESS(f"✓ {fp[:8]}... unbanned: {reason}"))

                logger.warning(f"[FP_CLEANUP] {len(expired_fps)} expired fingerprint bans removed")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Cleanup xatoligi: {str(e)}"))

    def _clear_rate_limits(self, dry_run=False):
        """Barcha rate limiting counterlarni tozalash"""
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                return

            rate_keys = list(redis_client.scan_iter(match="rate_fp:*"))

            if not rate_keys:
                self.stdout.write(self.style.SUCCESS("✓ Rate limit counterlar yo'q"))
                return

            self.stdout.write(f"🧹 {len(rate_keys)} ta rate limit counter tozalanmoqda")

            if not dry_run:
                for key in rate_keys:
                    redis_client.delete(key)
                self.stdout.write(self.style.SUCCESS("✓ Barcha rate limit counterlar tozalandi"))
            else:
                self.stdout.write(self.style.WARNING("[DRY RUN] Rate limit counterlar tozalanardi"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Rate limit tozalash xatoligi: {str(e)}"))

    def _clear_ip_blocks(self, dry_run=False):
        """Barcha IP bloklarini tozalash"""
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                return

            ip_keys = list(redis_client.scan_iter(match="ip_block:*"))

            if not ip_keys:
                self.stdout.write(self.style.SUCCESS("✓ IP bloklar yo'q"))
                return

            self.stdout.write(f"🧹 {len(ip_keys)} ta IP blok tozalanmoqda")

            if not dry_run:
                for key in ip_keys:
                    redis_client.delete(key)
                self.stdout.write(self.style.SUCCESS("✓ Barcha IP bloklar tozalandi"))
            else:
                self.stdout.write(self.style.WARNING("[DRY RUN] IP bloklar tozalanardi"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ IP blok tozalash xatoligi: {str(e)}"))

    def _show_fingerprint_info(self, fingerprint):
        """Muayyan fingerprint haqida ma'lumot ko'rsatish"""
        try:
            self.stdout.write(self.style.SUCCESS(f"🔍 Fingerprint ma'lumoti: {fingerprint[:8]}..."))

            # Ban info
            ban_info = BanService.get_fp_ban_info(fingerprint)
            if ban_info:
                self.stdout.write(f"🚫 Ban holati: Banned")
                self.stdout.write(f'   Sabab: {ban_info.get("ban_reason", "N/A")}')
                self.stdout.write(f'   Tur: {ban_info.get("banned_for", "N/A")}')

                if ban_info.get("is_permanent"):
                    self.stdout.write(f"   Muddat: Permanent")
                elif ban_info.get("ban_expires_at"):
                    self.stdout.write(f'   Tugaydi: {ban_info["ban_expires_at"]}')

                self.stdout.write(f'   Qo\'ygan: {ban_info.get("actor", "N/A")}')
            else:
                self.stdout.write(f"✅ Ban holati: Not banned")

            # User mapping
            user = BanService.get_user_by_fp(fingerprint)
            if user:
                self.stdout.write(f"👤 User: {user.email} (ID: {user.id})")
            else:
                self.stdout.write(f"👤 User: No mapping found")

            # Rate limiting info
            rate_count = cache.get(f"rate_fp:{fingerprint}", 0)
            self.stdout.write(f"⚡ Rate limit: {rate_count} requests this second")

            # Main page counter
            main_page_count = cache.get(f"main_page_fp:{fingerprint}", 0)
            self.stdout.write(f"🏠 Main page: {main_page_count} requests this hour")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Fingerprint ma'lumot xatoligi: {str(e)}"))

    def _get_redis_client(self):
        """Redis client olish"""
        try:
            from django.core.cache.backends.redis import RedisCache

            if isinstance(cache, RedisCache):
                return cache._cache.get_client(write=True)
            else:
                self.stdout.write(self.style.WARNING("⚠️  Redis cache ishlatilmayapti"))
                return None
        except Exception as e:
            logger.error(f"[FP_CLEANUP] Redis client error: {str(e)}")
            return None
