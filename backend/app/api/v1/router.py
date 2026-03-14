"""
Aggregate all v1 sub-routers.
"""
from fastapi import APIRouter, Depends

from app.api.v1 import auth, channels, config, exports, forecasts, hiring_waves, projects, seasonality, summary, training, uploads
from app.core.security import get_current_user

# Protected dependency applied to all non-auth routers
_protected = [Depends(get_current_user)]

api_router = APIRouter()

# Auth routes — no protection
api_router.include_router(auth.router,        prefix="/auth",        tags=["auth"])

# Protected routes
api_router.include_router(uploads.router,     prefix="/uploads",     tags=["uploads"],     dependencies=_protected)
api_router.include_router(channels.router,    prefix="/channels",    tags=["channels"],    dependencies=_protected)
api_router.include_router(training.router,    prefix="/training",    tags=["training"],    dependencies=_protected)
api_router.include_router(forecasts.router,   prefix="/forecasts",   tags=["forecasts"],   dependencies=_protected)
api_router.include_router(seasonality.router, prefix="/seasonality", tags=["seasonality"], dependencies=_protected)
api_router.include_router(config.router,      prefix="/config",      tags=["config"],      dependencies=_protected)
api_router.include_router(summary.router,     prefix="/summary",     tags=["summary"],     dependencies=_protected)
api_router.include_router(exports.router,      prefix="/exports",      tags=["exports"],      dependencies=_protected)
api_router.include_router(hiring_waves.router, prefix="/hiring-waves", tags=["hiring-waves"], dependencies=_protected)
api_router.include_router(projects.router,     prefix="/projects",     tags=["projects"],     dependencies=_protected)
