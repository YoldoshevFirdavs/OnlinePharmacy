"""
Ban Service - foydalanuvchilarning ban holatini boshqarish
Enhanced with device fingerprint support, dual approval, and revert workflow
"""

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import CustomUser

logger = logging.getLogger(__name__)


class BanService:
    """Ban qo'yish, olib tashlash va tekshirish xizmati - User va Fingerprint uchun"""

    @staticmethod
    def ban_user(user, duration_minutes=None, reason="", banned_for="", banned_by=None, is_permanent=False):
        """
        Foydalanuvchini ban qilish

        Args:
            user: CustomUser instance
            duration_minutes (int): Vaqtli ban bo'lsa, necha minutga
            reason (str): Ban sababi
            banned_for (str): Qaysi page uchun ban
            banned_by: Ban qo'ygan admin
            is_permanent (bool): Permanent ban bo'lsa True
        """
        if not isinstance(user, CustomUser):
            logger.error(f"BanService.ban_user: Invalid user type {type(user)}")
            return False

        try:
            user.banned_for = banned_for
            user.ban_reason = reason
            user.banned_by = banned_by
            user.is_permanent_ban = is_permanent

            if is_permanent:
                user.ban_until = None
            elif duration_minutes:
                user.ban_until = timezone.now() + timedelta(minutes=duration_minutes)

            user.save()

            # Audit log
            actor = banned_by.get_display_name() if banned_by else "System"
            logger.warning(
                f"[BAN] User {user.id} ({user.email}) banned by {actor} "
                f"for '{banned_for}' - Reason: {reason} - "
                f"Duration: {'Permanent' if is_permanent else f'{duration_minutes}min'}"
            )

            return True
        except Exception as e:
            logger.error(f"BanService.ban_user error: {str(e)}")
            return False

    @staticmethod
    def ban_by_fp(fp, duration_minutes=None, reason="", banned_for="", actor=None):
        """
        Device fingerprint asosida ban qo'yish

        Args:
            fp (str): Device fingerprint
            duration_minutes (int): Vaqtli ban bo'lsa, necha minutga
            reason (str): Ban sababi
            banned_for (str): Qaysi action uchun ban
            actor (str): Ban qo'ygan actor (user yoki 'system')
        """
        if not fp:
            logger.error("BanService.ban_by_fp: Empty fingerprint")
            return False

        try:
            now = timezone.now()
            ban_info = {
                "is_banned": True,
                "banned_for": banned_for,
                "ban_reason": reason,
                "ban_created_at": now.isoformat(),
                "ban_expires_at": (now + timedelta(minutes=duration_minutes)).isoformat() if duration_minutes else None,
                "is_permanent": duration_minutes is None,
                "actor": str(actor) if actor else "system",
            }

            # Store in cache with appropriate TTL
            cache_ttl = (duration_minutes * 60) if duration_minutes else None
            cache.set(f"ban_fp:{fp}", ban_info, timeout=cache_ttl)

            # Also try to update user if mapping exists
            user_id = cache.get(f"fp_user:{fp}")
            if user_id:
                try:
                    user = CustomUser.objects.get(id=user_id)
                    BanService.ban_user(
                        user,
                        duration_minutes=duration_minutes,
                        reason=reason,
                        banned_for=banned_for,
                        is_permanent=duration_minutes is None,
                    )
                except CustomUser.DoesNotExist:
                    pass

            # Audit log
            logger.warning(
                f"[BAN_FP] Fingerprint {fp[:8]}... banned by {actor} "
                f"for '{banned_for}' - Reason: {reason} - "
                f"Duration: {'Permanent' if not duration_minutes else f'{duration_minutes}min'}"
            )

            return True
        except Exception as e:
            logger.error(f"BanService.ban_by_fp error: {str(e)}")
            return False

    @staticmethod
    def unban_by_fp(fp, actor=None):
        """
        Device fingerprint asosida ban olib tashlash

        Args:
            fp (str): Device fingerprint
            actor: Ban olib tashlayotgan admin yoki system
        """
        if not fp:
            logger.error("BanService.unban_by_fp: Empty fingerprint")
            return False

        try:
            # Remove from cache
            old_ban_info = cache.get(f"ban_fp:{fp}")
            cache.delete(f"ban_fp:{fp}")

            # Also try to unban user if mapping exists
            user_id = cache.get(f"fp_user:{fp}")
            if user_id:
                try:
                    user = CustomUser.objects.get(id=user_id)
                    BanService.unban_user(user, actor=actor)
                except CustomUser.DoesNotExist:
                    pass

            # Audit log
            old_banned_for = old_ban_info.get("banned_for", "Unknown") if old_ban_info else "Unknown"
            actor_name = str(actor) if actor else "System"
            logger.warning(
                f"[UNBAN_FP] Fingerprint {fp[:8]}... unbanned by {actor_name} " f"(was banned for '{old_banned_for}')"
            )

            return True
        except Exception as e:
            logger.error(f"BanService.unban_by_fp error: {str(e)}")
            return False

    @staticmethod
    def is_fp_banned(fp):
        """
        Device fingerprint bannalangan yoki yo'qligini tekshirish

        Args:
            fp (str): Device fingerprint

        Returns:
            bool: True agar banned, False agar banned emas
        """
        if not fp:
            return False

        try:
            ban_info = cache.get(f"ban_fp:{fp}")
            if not ban_info or not ban_info.get("is_banned"):
                return False

            # Check if temporary ban expired
            if ban_info.get("ban_expires_at"):
                expires_at = timezone.datetime.fromisoformat(ban_info["ban_expires_at"])
                if timezone.now() >= expires_at:
                    # Ban expired, remove it
                    BanService.unban_by_fp(fp, actor="system")
                    return False

            return True
        except Exception as e:
            logger.error(f"BanService.is_fp_banned error: {str(e)}")
            return False

    @staticmethod
    def map_fp_to_user(fp, user):
        """
        Device fingerprint ni user bilan bog'lash

        Args:
            fp (str): Device fingerprint
            user: CustomUser instance
        """
        if not fp or not isinstance(user, CustomUser):
            return False

        try:
            # Store mapping in cache (24 hours TTL)
            cache.set(f"fp_user:{fp}", user.id, timeout=86400)

            # Also store reverse mapping for user lookup
            existing_fps = cache.get(f"user_fps:{user.id}", [])
            if fp not in existing_fps:
                existing_fps.append(fp)
                # Keep only last 5 fingerprints per user
                if len(existing_fps) > 5:
                    existing_fps = existing_fps[-5:]
                cache.set(f"user_fps:{user.id}", existing_fps, timeout=86400)

            return True
        except Exception as e:
            logger.error(f"BanService.map_fp_to_user error: {str(e)}")
            return False

    @staticmethod
    def get_user_by_fp(fp):
        """
        Device fingerprint orqali user topish

        Args:
            fp (str): Device fingerprint

        Returns:
            CustomUser instance yoki None
        """
        if not fp:
            return None

        try:
            user_id = cache.get(f"fp_user:{fp}")
            if user_id:
                return CustomUser.objects.get(id=user_id)
        except (CustomUser.DoesNotExist, Exception) as e:
            logger.error(f"BanService.get_user_by_fp error: {str(e)}")

        return None

    @staticmethod
    def record_blocked_event(actor, fp, path, reason, banned_for=None):
        """
        Bloklangan event-ni log qilish (fingerprint uchun)

        Args:
            actor (str): Kim tomonidan (user, system)
            fp (str): Device fingerprint
            path (str): Qaysi URL-ga kirsa bloklandi
            reason (str): Nima uchun bloklandi
            banned_for (str): Agar ban qo'yilgan bo'lsa
        """
        try:
            log_msg = (
                f"[BLOCKED_FP] Fingerprint {fp[:8] if fp else 'None'}... "
                f"blocked by {actor} - Path: {path} - Reason: {reason}"
            )
            if banned_for:
                log_msg += f" - Banned for: {banned_for}"

            logger.warning(log_msg)
            return True
        except Exception as e:
            logger.error(f"BanService.record_blocked_event error: {str(e)}")
            return False

    @staticmethod
    def unban_user(user, actor=None):
        """
        Ban olib tasklash

        Args:
            user: CustomUser instance
            actor: Ban olib tasklayotgan admin
        """
        if not isinstance(user, CustomUser):
            logger.error(f"BanService.unban_user: Invalid user type {type(user)}")
            return False

        try:
            old_banned_for = user.banned_for
            user.banned_for = None
            user.ban_until = None
            user.is_permanent_ban = False
            user.ban_reason = None
            user.save()

            # Audit log
            actor_name = actor.get_display_name() if actor else "System"
            logger.warning(
                f"[UNBAN] User {user.id} ({user.email}) unbanned by {actor_name} "
                f"(was banned for '{old_banned_for}')"
            )

            return True
        except Exception as e:
            logger.error(f"BanService.unban_user error: {str(e)}")
            return False

    @staticmethod
    def is_user_banned(user, for_page=None):
        """
        Foydalanuvchi bannalangan yoki yo'qligini tekshirish

        Args:
            user: CustomUser instance
            for_page (str): Qaysi page uchun ban tekshirish (opsional)

        Returns:
            bool: True agar banned, False agar banned emas
        """
        if not isinstance(user, CustomUser):
            return False

        try:
            # Page tekshirish
            if for_page and user.banned_for != for_page:
                return False

            # Agar banned_for bo'sh bo'lsa, ban yo'q
            if not user.banned_for:
                return False

            # Permanent ban
            if user.is_permanent_ban:
                return True

            # Vaqtli ban - vaqt tugagan yoki yo'qligini tekshirish
            if user.ban_until:
                if timezone.now() < user.ban_until:
                    return True
                else:
                    # Ban vaqti tugagan, avtomatik ochish
                    BanService.unban_user(user, actor=None)
                    return False

            return False
        except Exception as e:
            logger.error(f"BanService.is_user_banned error: {str(e)}")
            return False

    @staticmethod
    def record_blocked_event(user, path_attempted, reason, banned_for=None):
        """
        Bloklangan event-ni log qilish

        Args:
            user: CustomUser instance
            path_attempted (str): Qaysi URL-ga kirsa bloklandi
            reason (str): Nima uchun bloklandi
            banned_for (str): Agar ban qo'yilgan bo'lsa
        """
        try:
            log_msg = f"[BLOCKED] User {user.id} ({user.email}) tried to access {path_attempted} - " f"Reason: {reason}"
            if banned_for:
                log_msg += f" - Banned for: {banned_for}"

            logger.warning(log_msg)
            return True
        except Exception as e:
            logger.error(f"BanService.record_blocked_event error: {str(e)}")
            return False

    @staticmethod
    def increment_failed_attempts(
        user, field="failed_telegram_attempts", limit=None, ban_page="telegram_check", ban_duration_minutes=60
    ):
        """
        Noto'g'ri urinishlarni hisoblash va limitga yetganda ban qilish

        Args:
            user: CustomUser instance
            field (str): Qaysi field-ni increment qilish
            limit (int): Limit qiymat
            ban_page (str): Ban qo'yish uchun page nomi
            ban_duration_minutes (int): Ban vaqti (minutda)

        Returns:
            dict: {'incremented': bool, 'attempts': int, 'limit': int, 'banned': bool}
        """
        if not isinstance(user, CustomUser):
            return {"incremented": False, "attempts": 0, "limit": limit, "banned": False}

        try:
            if not hasattr(user, field):
                logger.error(f"BanService.increment_failed_attempts: User model no field '{field}'")
                return {"incremented": False, "attempts": 0, "limit": limit, "banned": False}

            current_attempts = getattr(user, field, 0) or 0
            current_attempts += 1
            setattr(user, field, current_attempts)

            banned = False
            if limit and current_attempts >= limit:
                # Ban qilish
                BanService.ban_user(
                    user,
                    duration_minutes=ban_duration_minutes,
                    reason=f"{field} limitga yetdi: {current_attempts}/{limit}",
                    banned_for=ban_page,
                    is_permanent=False,
                )
                banned = True

            user.save()

            return {"incremented": True, "attempts": current_attempts, "limit": limit, "banned": banned}
        except Exception as e:
            logger.error(f"BanService.increment_failed_attempts error: {str(e)}")
            return {"incremented": False, "attempts": 0, "limit": limit, "banned": False}

    @staticmethod
    def get_ban_info(user):
        """
        Ban haqida to'liq ma'lumot qaytarish

        Returns:
            dict: Ban tafsilotlari
        """
        if not isinstance(user, CustomUser):
            return None

        try:
            if not user.banned_for:
                return None

            # Agar vaqtli ban vaqti tugagan bo'lsa, avtomatik ochish
            if user.ban_until and timezone.now() >= user.ban_until:
                BanService.unban_user(user, actor=None)
                return None

            return {
                "is_banned": True,
                "banned_for": user.banned_for,
                "ban_reason": user.ban_reason,
                "ban_created_at": getattr(user, "ban_created_at", None),  # Agar model-da bo'lsa
                "ban_until": user.ban_until,
                "is_permanent": user.is_permanent_ban,
                "banned_by": user.banned_by.get_display_name() if user.banned_by else "System",
            }
        except Exception as e:
            logger.error(f"BanService.get_ban_info error: {str(e)}")
            return None

    @staticmethod
    def get_fp_ban_info(fp):
        """
        Device fingerprint ban haqida ma'lumot qaytarish

        Args:
            fp (str): Device fingerprint

        Returns:
            dict: Ban tafsilotlari yoki None
        """
        if not fp:
            return None

        try:
            ban_info = cache.get(f"ban_fp:{fp}")
            if not ban_info:
                return None

            # Check expiration
            if ban_info.get("ban_expires_at"):
                expires_at = timezone.datetime.fromisoformat(ban_info["ban_expires_at"])
                if timezone.now() >= expires_at:
                    BanService.unban_by_fp(fp, actor="system")
                    return None

            return ban_info
        except Exception as e:
            logger.error(f"BanService.get_fp_ban_info error: {str(e)}")
            return None

    # ═══════ DUAL APPROVAL WORKFLOW ═══════

    @staticmethod
    def create_unban_request(fp=None, user_id=None, requester_id=None, reason=""):
        """
        Create a new unban request with dual approval workflow

        Args:
            fp (str): Fingerprint to unban
            user_id (int): User ID to unban
            requester_id (int): Admin ID requesting unban
            reason (str): Reason for unban request

        Returns:
            dict: Request info with id and status
        """
        if not requester_id:
            logger.error("BanService.create_unban_request: requester_id required")
            return None

        request_id = str(uuid.uuid4())[:12]
        now = timezone.now()

        # Store pending request in cache
        request_info = {
            "request_id": request_id,
            "fp": fp,
            "user_id": user_id,
            "requester_id": requester_id,
            "reason": reason,
            "status": "pending",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat(),  # 24 hour timeout
            "approver_id": None,
            "approved_at": None,
            "rejection_reason": None,
        }

        cache_key = f"pending_unban:{request_id}"
        cache.set(cache_key, request_info, timeout=86400)  # 24 hours

        # Also store by fingerprint/user for easy lookup
        if fp:
            cache.set(f"unban_request_fp:{fp}", request_id, timeout=86400)
        if user_id:
            cache.set(f"unban_request_user:{user_id}", request_id, timeout=86400)

        logger.warning(
            f"[UNBAN_REQUEST] Admin {requester_id} requested unban for "
            f"{'fp:' + fp if fp else 'user:' + str(user_id)} - Reason: {reason}"
        )

        return request_info

    @staticmethod
    def get_unban_request(request_id):
        """Get unban request by ID"""
        cache_key = f"pending_unban:{request_id}"
        return cache.get(cache_key)

    @staticmethod
    def approve_unban_request(request_id, approver_id, is_superuser=False):
        """
        Approve an unban request

        Args:
            request_id (str): Request ID
            approver_id (int): Admin ID approving
            is_superuser (bool): Is approver superuser

        Returns:
            dict: {'success': bool, 'message': str, 'action': str}
        """
        request_info = BanService.get_unban_request(request_id)
        if not request_info:
            return {"success": False, "message": "Request not found", "action": "not_found"}

        if request_info["status"] != "pending":
            return {"success": False, "message": "Request already processed", "action": "already_processed"}

        # Check if request expired
        expires_at = timezone.datetime.fromisoformat(request_info["expires_at"])
        if timezone.now() >= expires_at:
            BanService.reject_unban_request(request_id, "Request expired")
            return {"success": False, "message": "Request expired", "action": "expired"}

        # Dual approval: cannot approve own request
        if request_info["requester_id"] == approver_id:
            return {
                "success": False,
                "message": "O'zingizni unban qila olmaysiz. Iltimos boshqa admindan tasdiq oling.",
                "action": "self_approval_forbidden",
            }

        # For permanent bans, only superuser can approve
        if request_info.get("is_permanent") and not is_superuser:
            return {
                "success": False,
                "message": "Permanent banlarni faqat superadmin tasdiqlashi mumkin",
                "action": "insufficient_permissions",
            }

        # Get the target
        fp = request_info.get("fp")
        user_id = request_info.get("user_id")

        # Unban the target
        success = False
        if fp:
            success = BanService.unban_by_fp(fp, actor=f"admin_{approver_id}")
        elif user_id:
            try:
                user = CustomUser.objects.get(id=user_id)
                success = BanService.unban_user(user, actor=f"admin_{approver_id}")
            except CustomUser.DoesNotExist:
                pass

        if not success:
            return {"success": False, "message": "Unban failed", "action": "unban_failed"}

        # Update request status
        now = timezone.now()
        request_info["status"] = "approved"
        request_info["approver_id"] = approver_id
        request_info["approved_at"] = now.isoformat()
        request_info["is_superuser"] = is_superuser

        cache_key = f"pending_unban:{request_id}"
        cache.set(cache_key, request_info, timeout=86400)

        # Remove from fingerprint/user lookup
        if fp:
            cache.delete(f"unban_request_fp:{fp}")
        if user_id:
            cache.delete(f"unban_request_user:{user_id}")

        logger.warning(
            f"[UNBAN_APPROVED] Admin {approver_id} approved unban request {request_id} "
            f"for {'fp:' + fp if fp else 'user:' + str(user_id)}"
        )

        return {"success": True, "message": "Unban approved", "action": "approved"}

    @staticmethod
    def reject_unban_request(request_id, rejection_reason="", approver_id=None):
        """Reject an unban request"""
        request_info = BanService.get_unban_request(request_id)
        if not request_info:
            return {"success": False, "message": "Request not found"}

        now = timezone.now()
        request_info["status"] = "rejected"
        request_info["rejection_reason"] = rejection_reason
        request_info["rejection_time"] = now.isoformat()
        request_info["rejection_admin_id"] = approver_id

        cache_key = f"pending_unban:{request_id}"
        cache.set(cache_key, request_info, timeout=86400)

        # Remove from fingerprint/user lookup
        if request_info.get("fp"):
            cache.delete(f"unban_request_fp:{request_info['fp']}")
        if request_info.get("user_id"):
            cache.delete(f"unban_request_user:{request_info['user_id']}")

        logger.warning(
            f"[UNBAN_REJECTED] Admin {approver_id} rejected unban request {request_id} " f"Reason: {rejection_reason}"
        )

        return {"success": True, "message": "Request rejected"}

    @staticmethod
    def create_revert_request(target_id, target_type="ban", requester_id=None, reason=""):
        """
        Create a revert request for audit record
        target_id: ban record ID or fingerprint/user_id
        target_type: 'ban', 'fp_ban', 'user_ban'
        """
        if not requester_id:
            logger.error("BanService.create_revert_request: requester_id required")
            return None

        request_id = str(uuid.uuid4())[:12]
        now = timezone.now()

        revert_info = {
            "request_id": request_id,
            "target_id": target_id,
            "target_type": target_type,
            "requester_id": requester_id,
            "reason": reason,
            "status": "pending",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
            "approver_id": None,
            "approved_at": None,
            "reverted_at": None,
            "rollback_data": None,
        }

        cache_key = f"pending_revert:{request_id}"
        cache.set(cache_key, revert_info, timeout=86400)

        return revert_info

    @staticmethod
    def approve_revert_request(request_id, approver_id, is_superuser=False):
        """Approve a revert request with dual approval"""
        revert_info = BanService.get_unban_request(request_id)  # Using same pattern
        if not revert_info or revert_info.get("target_type") != "revert":
            # Check revert-specific key
            revert_info = cache.get(f"pending_revert:{request_id}")

        if not revert_info:
            return {"success": False, "message": "Revert request not found"}

        if revert_info["status"] != "pending":
            return {"success": False, "message": "Request already processed"}

        # Check expiration
        expires_at = timezone.datetime.fromisoformat(revert_info["expires_at"])
        if timezone.now() >= expires_at:
            return {"success": False, "message": "Revert request expired"}

        # Self-approval forbidden
        if revert_info["requester_id"] == approver_id:
            return {"success": False, "message": "O'zingiz revert qila olmaysiz. Iltimos boshqa admindan tasdiq oling."}

        # For permanent changes, only superuser
        if revert_info.get("is_permanent") and not is_superuser:
            return {"success": False, "message": "Permanent o'zgarishlarni faqat superadmin tasdiqlashi mumkin"}

        # Perform revert (idempotent)
        revert_result = BanService._perform_revert(revert_info)

        # Update request status
        now = timezone.now()
        revert_info["status"] = "approved"
        revert_info["approver_id"] = approver_id
        revert_info["approved_at"] = now.isoformat()
        revert_info["reverted_at"] = now.isoformat()

        cache_key = f"pending_revert:{request_id}"
        cache.set(cache_key, revert_info, timeout=86400)

        logger.warning(f"[REVERT_APPROVED] Admin {approver_id} approved revert request {request_id}")

        return {
            "success": revert_result,
            "message": "Revert approved" if revert_result else "Revert failed",
            "action": "approved",
        }

    @staticmethod
    def _perform_revert(revert_info):
        """
        Perform the actual revert operation
        This is idempotent - can be called multiple times safely
        """
        target_type = revert_info.get("target_type")
        target_id = revert_info.get("target_id")

        try:
            if target_type == "fp_ban":
                # Revert fingerprint ban - unban if banned
                fp = target_id
                if BanService.is_fp_banned(fp):
                    BanService.unban_by_fp(fp, actor="revert")
                    return True
                return True  # Already unbanned - idempotent

            elif target_type == "user_ban":
                # Revert user ban
                try:
                    user = CustomUser.objects.get(id=target_id)
                    if BanService.is_user_banned(user):
                        BanService.unban_user(user, actor="revert")
                        return True
                    return True  # Already unbanned - idempotent
                except CustomUser.DoesNotExist:
                    return False

            elif target_type == "ban":
                # Generic ban revert - check both user and fp
                if BanService.is_fp_banned(target_id):
                    BanService.unban_by_fp(target_id, actor="revert")
                    return True
                try:
                    user = CustomUser.objects.get(id=target_id)
                    if BanService.is_user_banned(user):
                        BanService.unban_user(user, actor="revert")
                        return True
                except CustomUser.DoesNotExist:
                    pass
                return True  # No active ban to revert - idempotent

            else:
                logger.warning(f"Unknown target_type for revert: {target_type}")
                return False

        except Exception as e:
            logger.error(f"BanService._perform_revert error: {str(e)}")
            return False

    @staticmethod
    def get_admin_pending_requests(admin_id):
        """Get all pending unban requests created by admin"""
        pending_requests = []

        # Scan all pending requests (simplified - in production use Redis SCAN)
        for key in cache._cache.keys("*") if hasattr(cache, "_cache") else []:
            if key.startswith("pending_unban:"):
                try:
                    request_info = cache.get(key)
                    if request_info and request_info.get("status") == "pending":
                        pending_requests.append(request_info)
                except:
                    continue

        # Filter by requester
        return [r for r in pending_requests if r.get("requester_id") == admin_id]

    @staticmethod
    def record_audit_event(actor, action, target, reason="", extra_data=None):
        """
        Record audit log for ban/unban/revert events
        This is a simplified version - integrate with existing AuditLog model if available
        """
        try:
            audit_data = {
                "actor": actor,
                "action": action,
                "target": target,
                "reason": reason,
                "extra_data": extra_data or {},
                "timestamp": timezone.now().isoformat(),
                "ip_address": None,  # Will be set by middleware
                "user_agent": None,  # Will be set by middleware
            }

            # Store in cache for immediate access
            audit_key = f"audit:{action}:{timezone.now().strftime('%Y%m%d')}"
            audit_records = cache.get(audit_key, [])
            audit_records.append(audit_data)
            cache.set(audit_key, audit_records, timeout=2592000)  # 30 days

            # Log to file
            logger.warning(f"[AUDIT] {action}: {actor} -> {target} ({reason})")

            return audit_data
        except Exception as e:
            logger.error(f"BanService.record_audit_event error: {str(e)}")
            return None
