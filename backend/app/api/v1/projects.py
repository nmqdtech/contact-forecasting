"""Project routes: GET/POST/PATCH/DELETE /projects"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import project_service

router = APIRouter()


@router.get("", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    return await project_service.list_projects(db)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await project_service.create_project(db, body.name, body.description)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await project_service.update_project(
        db, project_id, body.name, body.description
    )
    if result is None:
        raise HTTPException(404, "Project not found")
    return result


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    try:
        deleted = await project_service.delete_project(db, project_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    if not deleted:
        raise HTTPException(404, "Project not found")
