from fastapi import APIRouter

from app.api.v1 import analysis, auth, dashboard, insights, videos

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(videos.router)
api_v1_router.include_router(analysis.router)
api_v1_router.include_router(insights.router)
api_v1_router.include_router(dashboard.router)
