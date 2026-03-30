
import logging
from datetime import datetime, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def notify_profile_service(
    user_id: str,
    role: str,
    created_at: datetime,
    first_name: str,
    last_name: str,
) -> None:
    url = f"{settings.PROFILE_SERVICE_URL}/internal/profiles"

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    payload = {
        "user_id": str(user_id),
        "role": role,
        "created_at": created_at.isoformat(),
        "full_name": f"{first_name} {last_name}",
    }
    headers = {
        "x-internal-key": settings.INTERNAL_API_KEY,
        "Content-Type": "application/json",
    }

    logger.info(
        "Notifying profile service | url=%s user_id=%s role=%s",
        url, user_id, role,
    )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=payload, headers=headers)

            logger.info(
                "Profile service response | status=%s body=%s",
                response.status_code,
                response.text,
            )

            response.raise_for_status()
            logger.info("Profile created successfully for user %s", user_id)

    except httpx.HTTPStatusError as e:
        # Non-blocking — user is already saved in the auth DB.
        # Profile service can be resynced later; don't fail registration.
        logger.warning(
            "Profile service HTTP error for user %s (non-fatal): %s - %s",
            user_id,
            e.response.status_code,
            e.response.text,
        )

    except httpx.RequestError as e:
        # Non-blocking — profile service is down or unreachable.
        # Registration still succeeds; profile sync will be retried on next call.
        logger.warning(
            "Could not reach profile service for user %s (non-fatal): %s",
            user_id,
            str(e),
        )