from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from contextlib import asynccontextmanager
import httpx

from app.core.config import settings
from app.api.v1.router import api_router_v1
from app.utils.openapi import generate_custom_openapi_schema
from app.core.clients.dod_sbir_client import http_client_store, DoDSBIRAPIError
from app.api.v1.schemas import ErrorResponse # For custom exception handler


# Lifespan manager for httpx.AsyncClient
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize AsyncClient and store it
    # Configure timeout for the client globally
    timeout = httpx.Timeout(30.0, connect=5.0) # 30s total, 5s connect
    async with httpx.AsyncClient(timeout=timeout) as client:
        http_client_store["client"] = client
        yield
    # Shutdown: Clean up (AsyncClient context manager handles this)
    http_client_store.clear()

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url=None,  # Disable default docs
    redoc_url=None, # Disable default redoc
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Assign the custom OpenAPI schema generator
def custom_openapi_schema_for_app():
    return generate_custom_openapi_schema(app)

app.openapi = custom_openapi_schema_for_app

# Custom Swagger UI endpoint
@app.get("/api/v1/docs", include_in_schema=False)
async def custom_swagger_ui_html_endpoint():
    return get_swagger_ui_html(
        openapi_url="/api/v1/openapi.json", # Make sure this matches the openapi_json_url
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
    )

# OpenAPI JSON endpoint
@app.get("/api/v1/openapi.json", include_in_schema=False)
async def get_openapi_json_endpoint():
    return JSONResponse(app.openapi())


# Include API routers
app.include_router(api_router_v1, prefix="/api/v1")


# Custom exception handler for DoDSBIRAPIError
@app.exception_handler(DoDSBIRAPIError)
async def dod_sbir_api_exception_handler(request: Request, exc: DoDSBIRAPIError):
    status_code = exc.status_code if exc.status_code else 502  # Bad Gateway
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(detail=str(exc), code="DOD_API_ERROR").model_dump(),
    )

# Root path (optional)
@app.get("/", include_in_schema=False)
async def root():
    return {"message": f"Welcome to {settings.APP_TITLE}. See /api/v1/docs for API documentation."}

# For running with uvicorn directly (python app/main.py)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)