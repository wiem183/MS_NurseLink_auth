# app/models/otp_code.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    purpose = Column(String(30), nullable=False)  # "email_verification" | "password_reset"

    # Set after OTP is verified — only used for password_reset purpose
    reset_token = Column(String(64), nullable=True, unique=True, index=True)

    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        return not self.used and not self.is_expired()

    def __repr__(self) -> str:
        return (
            f"<OTPCode email={self.email} purpose={self.purpose} "
            f"used={self.used} expires_at={self.expires_at}>"
        )