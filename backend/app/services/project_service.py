"""Project CRUD service."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project

MAX_PROJECTS = 5


async def list_projects(db: AsyncSession) -> list[Project]:
    result = await db.execute(select(Project).order_by(Project.created_at))
    return list(result.scalars().all())


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project | None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def create_project(
    db: AsyncSession, name: str, description: str | None = None
) -> Project:
    count_result = await db.execute(select(func.count()).select_from(Project))
    count = count_result.scalar_one()
    if count >= MAX_PROJECTS:
        raise ValueError(f"Maximum of {MAX_PROJECTS} projects allowed")
    project = Project(name=name, description=description)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
) -> Project | None:
    project = await get_project(db, project_id)
    if project is None:
        return None
    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> bool:
    project = await get_project(db, project_id)
    if project is None:
        return False
    count_result = await db.execute(select(func.count()).select_from(Project))
    count = count_result.scalar_one()
    if count <= 1:
        raise ValueError("Cannot delete the last project")
    await db.delete(project)
    await db.commit()
    return True
