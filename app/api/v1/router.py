from fastapi import APIRouter
from app.api.v1.endpoints import topics

api_router_v1 = APIRouter()
api_router_v1.include_router(topics.router, prefix="/topics", tags=["SBIR Topics"])
# Add other v1 routers here if you have more modules