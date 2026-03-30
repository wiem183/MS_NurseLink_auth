# app/services/auth_service.py
import random
import secrets
import string
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.enums import UserRole
from app.models.otp_code import OTPCode
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponseDto, LoginDto, RegisterDto
from app.services.email_service import send_otp_email, send_verification_email
from app.services.password_service import PasswordService
from app.services.profile_client import notify_profile_service
from app.services.token_service import TokenService

logger = get_logger("app.auth")

PURPOSE_EMAIL_VERIFICATION = "email_verification"
PURPOSE_PASSWORD_RESET = "password_reset"


def _generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))


def _generate_reset_token() -> str:
    return secrets.token_hex(32)


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        token_service: TokenService,
        password_service: PasswordService,
    ) -> None:
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.token_service = token_service
        self.password_service = password_service

    # ── Register ──────────────────────────────────────────────────────────────

    async def register(self, dto: RegisterDto) -> AuthResponseDto:
        logger.info(f"[REGISTER] Attempt | email={dto.email} role={dto.role}")

        existing = await self.user_repo.find_by_email(dto.email.lower())
        if existing:
            logger.warning(f"[REGISTER] Conflict — email already exists | email={dto.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with that email already exists.",
            )

        # Nurses must complete KYC before logging in → start inactive.
        # Patients and Admins are immediately active.
        is_active = dto.role != UserRole.NURSE

        user = User(
            email=dto.email.lower(),
            password_hash=self.password_service.hash_password(dto.password),
            first_name=dto.first_name,
            last_name=dto.last_name,
            phone=dto.phone,
            role=dto.role,
            is_active=is_active,
        )
        user = await self.user_repo.create(user)
        logger.info(f"[REGISTER] User created | id={user.id} email={user.email} role={user.role}")

        await notify_profile_service(
            user_id=str(user.id),
            role=user.role.value,
            created_at=user.created_at,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        logger.debug(f"[REGISTER] Profile service notified | user_id={user.id}")

        await self._send_otp(
            email=user.email,
            first_name=user.first_name,
            purpose=PURPOSE_EMAIL_VERIFICATION,
        )

        logger.info(f"[REGISTER] Success | email={user.email}")
        return await self._issue_tokens(user)

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, dto: LoginDto) -> AuthResponseDto:
        logger.info(f"[LOGIN] Attempt | email={dto.email}")

        user = await self.user_repo.find_by_email(dto.email.lower())
        if not user or not self.password_service.verify_password(
            dto.password, user.password_hash
        ):
            logger.warning(f"[LOGIN] Failed — invalid credentials | email={dto.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.is_active:
            logger.warning(f"[LOGIN] Failed — account deactivated | email={dto.email} id={user.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact support.",
            )

        if not user.is_email_verified:
            logger.warning(
                f"[LOGIN] Blocked — email not verified | email={user.email} id={user.id} | sending new OTP"
            )
            await self._send_otp(
                email=user.email,
                first_name=user.first_name,
                purpose=PURPOSE_EMAIL_VERIFICATION,
            )
            # Commit before raising so the OTP is persisted despite the rollback
            await self.user_repo.db.commit()
            logger.info(f"[LOGIN] New OTP committed | email={user.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "EMAIL_NOT_VERIFIED",
                    "email": user.email,
                    "role": user.role.value,
                    "message": "Please verify your email before logging in. A new OTP has been sent.",
                },
            )

        user.last_login_at = datetime.utcnow()
        await self.user_repo.save(user)

        logger.info(f"[LOGIN] Success | email={user.email} id={user.id} role={user.role}")
        return await self._issue_tokens(user)

    # ── Refresh ───────────────────────────────────────────────────────────────

    async def refresh(self, raw_token: str) -> AuthResponseDto:
        logger.debug("[REFRESH] Token refresh attempt")
        try:
            rt = await self.token_service.verify_refresh_token(
                raw_token, self.token_repo
            )
        except ValueError as exc:
            logger.warning(f"[REFRESH] Failed — {exc}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
            )

        user = await self.user_repo.find_by_id(rt.user_id)
        if not user or not user.is_active:
            logger.warning(f"[REFRESH] Failed — user not found or inactive | user_id={rt.user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive.",
            )

        new_refresh = await self.token_service.rotate_refresh_token(
            raw_token, user.id, self.token_repo
        )
        access = self.token_service.create_access_token(user.id, user.role.value)

        logger.info(f"[REFRESH] Success | email={user.email} id={user.id}")
        return self._build_response(user, access, new_refresh)

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(self, raw_token: str) -> None:
        logger.info("[LOGOUT] Token revoked")
        await self.token_repo.revoke(raw_token)

    async def logout_all(self, user_id: uuid.UUID) -> None:
        logger.info(f"[LOGOUT_ALL] All tokens revoked | user_id={user_id}")
        await self.token_repo.revoke_all_for_user(user_id)

    # ── Email verification ────────────────────────────────────────────────────

    async def verify_email(self, email: str, otp: str) -> None:
        logger.info(f"[VERIFY_EMAIL] Attempt | email={email}")

        user = await self.user_repo.find_by_email(email.lower())
        if not user:
            logger.warning(f"[VERIFY_EMAIL] User not found | email={email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable.",
            )

        if user.is_email_verified:
            logger.info(f"[VERIFY_EMAIL] Already verified | email={email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email déjà vérifié.",
            )

        await self._consume_otp(
            email=email.lower(),
            otp=otp,
            purpose=PURPOSE_EMAIL_VERIFICATION,
        )

        user.is_email_verified = True
        user.updated_at = datetime.utcnow()
        await self.user_repo.db.flush()

        logger.info(f"[VERIFY_EMAIL] Success | email={email} id={user.id}")

    # ── Resend verification ───────────────────────────────────────────────────

    async def resend_verification(self, email: str) -> None:
        logger.info(f"[RESEND_OTP] Request | email={email}")

        user = await self.user_repo.find_by_email(email.lower())
        if not user:
            logger.debug(f"[RESEND_OTP] Silent skip — email not found | email={email}")
            return

        if user.is_email_verified:
            logger.info(f"[RESEND_OTP] Already verified | email={email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email déjà vérifié.",
            )

        await self._send_otp(
            email=user.email,
            first_name=user.first_name,
            purpose=PURPOSE_EMAIL_VERIFICATION,
        )
        logger.info(f"[RESEND_OTP] New OTP sent | email={email}")

    # ── Password reset ────────────────────────────────────────────────────────

    async def request_password_reset(self, email: str) -> str:
        logger.info(f"[PASSWORD_RESET] Reset requested | email={email}")
        user = await self.user_repo.find_by_email(email.lower())
        if user:
            await self._send_otp(
                email=user.email,
                first_name=user.first_name,
                purpose=PURPOSE_PASSWORD_RESET,
            )
            logger.info(f"[PASSWORD_RESET] OTP sent | email={email}")
        else:
            logger.debug(f"[PASSWORD_RESET] Silent skip — email not found | email={email}")
        return "Si cet email est enregistré, un code vous a été envoyé."

    async def verify_otp(self, email: str, otp: str) -> str:
        logger.info(f"[PASSWORD_RESET] OTP verify attempt | email={email}")
        db = self.user_repo.db
        record = await self._consume_otp(
            email=email.lower(),
            otp=otp,
            purpose=PURPOSE_PASSWORD_RESET,
            mark_used=False,
        )
        record.used = True
        reset_token = _generate_reset_token()
        record.reset_token = reset_token
        await db.flush()
        logger.info(f"[PASSWORD_RESET] OTP verified — reset token issued | email={email}")
        return reset_token

    async def reset_password(
        self,
        email: str,
        reset_token: str,
        new_password: str,
        confirm_password: str,
    ) -> None:
        logger.info(f"[PASSWORD_RESET] Password change attempt | email={email}")

        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match.",
            )
        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le mot de passe doit contenir au moins 6 caractères.",
            )

        db = self.user_repo.db
        result = await db.execute(
            select(OTPCode).where(
                OTPCode.email == email.lower(),
                OTPCode.reset_token == reset_token,
                OTPCode.used == True,  # noqa: E712
                OTPCode.purpose == PURPOSE_PASSWORD_RESET,
            )
        )
        record = result.scalar_one_or_none()

        if not record:
            logger.warning(f"[PASSWORD_RESET] Invalid or already used token | email={email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token invalide ou déjà utilisé.",
            )

        token_deadline = record.expires_at + timedelta(
            minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
        )
        if datetime.utcnow() > token_deadline:
            logger.warning(f"[PASSWORD_RESET] Token expired | email={email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token expiré. Veuillez recommencer.",
            )

        user = await self.user_repo.find_by_email(email.lower())
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable.",
            )

        user.password_hash = self.password_service.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        record.reset_token = None
        await db.flush()
        logger.info(f"[PASSWORD_RESET] Password updated successfully | email={email} id={user.id}")

    # ── Get current user ──────────────────────────────────────────────────────

    async def get_me(self, user: User) -> User:
        logger.debug(f"[GET_ME] | email={user.email} id={user.id}")
        return user

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _send_otp(self, email: str, first_name: str, purpose: str) -> None:
        db = self.user_repo.db

        existing_result = await db.execute(
            select(OTPCode).where(
                OTPCode.email == email,
                OTPCode.purpose == purpose,
                OTPCode.used == False,  # noqa: E712
            )
        )
        invalidated = 0
        for record in existing_result.scalars().all():
            record.used = True
            invalidated += 1
        await db.flush()
        if invalidated:
            logger.debug(
                f"[OTP] Invalidated {invalidated} old OTP(s) | email={email} purpose={purpose}"
            )

        otp = _generate_otp()
        otp_record = OTPCode(
            email=email,
            code=otp,
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        )
        db.add(otp_record)
        await db.flush()
        logger.info(
            f"[OTP] New OTP created | email={email} purpose={purpose} "
            f"expires_in={settings.OTP_EXPIRE_MINUTES}min"
        )

        try:
            if purpose == PURPOSE_EMAIL_VERIFICATION:
                send_verification_email(to_email=email, otp=otp, first_name=first_name)
            else:
                send_otp_email(to_email=email, otp=otp, first_name=first_name)
            logger.info(f"[OTP] Email sent successfully | email={email} purpose={purpose}")
        except Exception as exc:
            logger.error(f"[OTP] SMTP error | email={email} purpose={purpose} error={exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de l'envoi de l'email. Réessayez.",
            )

    async def _consume_otp(
        self,
        email: str,
        otp: str,
        purpose: str,
        mark_used: bool = True,
    ) -> OTPCode:
        db = self.user_repo.db

        result = await db.execute(
            select(OTPCode)
            .where(
                OTPCode.email == email,
                OTPCode.purpose == purpose,
                OTPCode.used == False,  # noqa: E712
            )
            .order_by(OTPCode.created_at.desc())
        )
        record = result.scalar_one_or_none()

        invalid = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code invalide ou expiré.",
        )

        if not record:
            logger.warning(f"[OTP] No valid OTP found | email={email} purpose={purpose}")
            raise invalid

        if record.is_expired():
            record.used = True
            await db.flush()
            logger.warning(
                f"[OTP] Expired | email={email} purpose={purpose} expired_at={record.expires_at}"
            )
            raise invalid

        if record.attempts >= settings.OTP_MAX_ATTEMPTS:
            record.used = True
            await db.flush()
            logger.warning(
                f"[OTP] Max attempts reached | email={email} purpose={purpose} "
                f"attempts={record.attempts}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives. Veuillez demander un nouveau code.",
            )

        record.attempts += 1
        await db.flush()

        if record.code != otp:
            logger.warning(
                f"[OTP] Wrong code | email={email} purpose={purpose} "
                f"attempts={record.attempts}/{settings.OTP_MAX_ATTEMPTS}"
            )
            raise invalid

        if mark_used:
            record.used = True
            await db.flush()

        logger.info(f"[OTP] Consumed successfully | email={email} purpose={purpose}")
        return record

    async def _issue_tokens(self, user: User) -> AuthResponseDto:
        access = self.token_service.create_access_token(
            user.id, user.role.value, user_created_at=user.created_at
        )
        refresh = await self.token_service.create_refresh_token(
            user.id, self.token_repo
        )
        logger.debug(f"[TOKEN] Issued access + refresh | email={user.email} id={user.id}")
        return self._build_response(user, access, refresh)

    @staticmethod
    def _build_response(user: User, access: str, refresh: str) -> AuthResponseDto:
        return AuthResponseDto(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            access_token=access,
            refresh_token=refresh,
        )