"""
Aggregate all v1 sub-routers.
"""
from fastapi import APIRouter

from app.api.v1 import channels, config, exports, forecasts, seasonality, summary, training, uploads

api_router = APIRouter()

api_router.include_router(uploads.router,     prefix="/uploads",     tags=["uploads"])
api_router.include_router(channels.router,    prefix="/channels",    tags=["channels"])
api_router.include_router(training.router,    prefix="/training",    tags=["training"])
api_router.include_router(forecasts.router,   prefix="/forecasts",   tags=["forecasts"])
api_router.include_router(seasonality.router, prefix="/seasonality", tags=["seasonality"])
api_router.include_router(config.router,      prefix="/config",      tags=["config"])
api_router.include_router(summary.router,     prefix="/summary",     tags=["summary"])
api_router.include_router(exports.router,     prefix="/exports",     tags=["exports"])
