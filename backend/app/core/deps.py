"""
Shared FastAPI dependencies. `get_current_user` is what MOD-05 needs to
attribute a submission to an aspirant; `require_role` closes the
role-gating TODO that used to live in api/v1/syllabus.py — every
content_editor/admin/mentor-only endpoint added from MOD-06 onward
depends on it instead of re-implementing a role check inline. `require_plan`
is the MOD-12 analogue for plan-gated (post-payment) endpoints.
"""
from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.security import decode_access_token

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user


def require_role(*allowed_roles: str):
    """Dependency factory: `Depends(require_role("mentor", "admin"))`."""

    async def _check(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This action requires one of: {', '.join(allowed_roles)}",
            )
        return user

    return _check


def require_plan(*allowed_plans: str):
    """Dependency factory: `Depends(require_plan("full_prep"))`. Gates an
    endpoint on the caller's *current, non-expired* subscription plan —
    this is what actually enforces "access after payment" at the route
    level, on top of the AI-grading quota check billing already does
    per-call in answers.py.
    """
    from app.services.billing import get_or_create_subscription, is_entitled  # avoid import cycle at module load

    async def _check(
        user: dict = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ) -> dict:
        sub = await get_or_create_subscription(db, str(user["_id"]))
        if not is_entitled(sub, *allowed_plans):
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                f"This feature requires one of these plans: {', '.join(allowed_plans)}. "
                f"Current plan: '{sub['plan']}'. Upgrade in Billing to unlock it.",
            )
        return user

    return _check
