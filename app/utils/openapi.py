from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI

from app.api.v1.schemas import ( # Import all your Pydantic models
    Topic, SearchResponse, SearchRequest, 
    DownloadRequest, ErrorResponse
)

def generate_custom_openapi_schema(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Ensure components and schemas keys exist
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}

    # Add Pydantic models to the schema
    # FastAPI usually does this if models are used in request/response bodies or response_model.
    # This ensures they are present even if not directly referenced in all paths,
    # or if you want to define them with a specific name.
    all_schemas = {
        "Topic": Topic.model_json_schema(),
        "SearchResponse": SearchResponse.model_json_schema(),
        "SearchRequest": SearchRequest.model_json_schema(),
        "DownloadRequest": DownloadRequest.model_json_schema(),
        "ErrorResponse": ErrorResponse.model_json_schema(),
    }
    
    # Update schema with our models, potentially overwriting auto-generated ones if names conflict
    # but ensuring ours are used.
    openapi_schema["components"]["schemas"].update(all_schemas)

    # FastAPI 0.100+ handles HTTPValidationError automatically, so manual addition might not be needed.
    # If you need a specific structure or older FastAPI version, you might add it:
    # if "HTTPValidationError" not in openapi_schema["components"]["schemas"]:
    #     openapi_schema["components"]["schemas"]["HTTPValidationError"] = { ... }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema