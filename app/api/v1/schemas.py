from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union
from datetime import datetime

class Topic(BaseModel):
    topicCode: str = Field(..., description="The unique code identifier for the topic")
    topicTitle: str = Field(..., description="The title of the topic")
    component: str = Field(..., description="The component (e.g., Army, Navy, etc.)")
    topicStatus: str = Field(..., description="The current status of the topic")
    solicitationTitle: str = Field(..., description="The title of the solicitation")
    topicId: str = Field(..., description="The internal topic ID used for PDF downloads")
    programYear: Optional[int] = Field(None, description="The program year")
    releaseNumber: Optional[str] = Field(None, description="The release number")
    technologyArea: Optional[str] = Field(None, description="The technology area")
    keywords: Optional[List[str]] = Field(default_factory=list, description="List of keywords associated with the topic")
    # created_at: datetime = Field(default_factory=datetime.utcnow, description="When this record was created") 
    # ^ Commented out as it's not from the external API, more for DB records. Add back if you persist.

    @field_validator('releaseNumber', mode='before')
    @classmethod
    def convert_release_number_to_string(cls, v: Optional[Union[str, int]]) -> Optional[str]:
        if v is None:
            return None
        return str(v)

class SearchResponse(BaseModel):
    topics: List[Topic] = Field(..., description="List of topics matching the search criteria")
    total: int = Field(..., description="Total number of topics matching the search criteria")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_more: bool = Field(..., description="Whether there are more pages available")

class SearchRequest(BaseModel):
    term: Optional[str] = Field(None, description="Search term to filter topics")
    page: int = Field(0, ge=0, description="Page number (0-based)")
    page_size: int = Field(10, ge=1, le=100, description="Number of items per page")
    components: Optional[List[str]] = Field(None, description="Filter by components")
    program_years: Optional[List[int]] = Field(None, description="Filter by program years")
    # status: Optional[List[str]] = Field(None, description="Filter by topic status") # Not used in query_api

# ... (other models are the same)
class DownloadRequest(BaseModel):
    selected_topics: List[str] = Field(..., min_length=1, description="List of topic codes to download")
    search_term: Optional[str] = Field(None, description="Original search term used to find these topics")
    page: int = Field(..., ge=0, description="Page number where these topics were found (0-based)")
    page_size: int = Field(10, ge=1, le=100, description="Page size used for the original search") # Added for more robust re-query


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    #timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the error occurred")