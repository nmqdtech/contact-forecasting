"""
Idempotent admin user bootstrap: called at startup if no users exist.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import get_password_hash
from app.models.user import User

logger = logging.getLogger(__name__)


async def init_admin(db: AsyncSession) -> None:
    count_result = await db.execute(select(func.count()).select_from(User))
    count = count_result.scalar()
    if count and count > 0:
        return

    admin = User(
        username=settings.ADMIN_USERNAME,
        email=f"{settings.ADMIN_USERNAME}@local.internal",
        hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
        is_admin=True,
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    logger.info("Admin user '%s' created.", settings.ADMIN_USERNAME)
