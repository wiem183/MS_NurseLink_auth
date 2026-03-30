import uuid
from datetime import datetime, timezone, timedelta

import pytest
from jose import JWTError

from app.services.token_service import TokenService
from app.schemas.auth import JwtPayload


def test_access_token_contains_creation_timestamp():
    service = TokenService()
    user_id = uuid.uuid4()
    role = "ADMIN"
    created_at = datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)

    token = service.create_access_token(user_id, role, user_created_at=created_at)
    # decode and verify; should not raise
    payload = service.verify_access_token(token)
    assert isinstance(payload, JwtPayload)
    assert payload.sub == str(user_id)
    assert payload.role == role
    assert payload.created_at == int(created_at.timestamp())
    # iat should be very recent (within a minute)
    assert abs(payload.iat - int(datetime.now(tz=timezone.utc).timestamp())) < 60
    assert payload.exp > payload.iat


def test_verify_access_token_raises_on_invalid():
    service = TokenService()
    with pytest.raises(JWTError):
        service.verify_access_token("not-a-token")
