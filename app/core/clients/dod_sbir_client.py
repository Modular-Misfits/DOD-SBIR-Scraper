import httpx
import json
import urllib.parse
from typing import List, Tuple, Dict, Any, Optional

from app.core.config import settings
from app.api.v1.schemas import Topic, SearchRequest # Assuming schemas.py is in app.api.v1

class DoDSBIRClient:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.base_headers = {
            "User-Agent": settings.DOD_API_USER_AGENT,
            "Referer": settings.DOD_API_REFERER,
            "Accept": "application/json, text/plain, */*",
        }

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        # Combines base headers with any specific headers for the request
        headers = {**self.base_headers, **kwargs.pop("headers", {})}
        
        # If 'json' is in kwargs, ensure Content-Type is set
        if "json" in kwargs and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
            
        try:
            resp = await self.client.request(method, url, headers=headers, **kwargs)
            resp.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            return resp
        except httpx.TimeoutException as e:
            # Log e if you have a logger
            raise DoDSBIRAPIError(f"Request to {url} timed out.") from e
        except httpx.RequestError as e:
            # Log e
            raise DoDSBIRAPIError(f"Network error requesting {url}: {str(e)}") from e
        except httpx.HTTPStatusError as e:
            # Log e.response.text
            raise DoDSBIRAPIError(
                f"API request to {e.request.url} failed with status {e.response.status_code}. Response: {e.response.text[:200]}...",
                status_code=e.response.status_code
            ) from e


    async def search_topics(self, search_request: SearchRequest) -> Tuple[List[Topic], int, bool]:
        search_payload = {
            "searchText": search_request.term,
            "components": search_request.components or [], # Ensure it's a list
            "programYear": search_request.program_years[0] if search_request.program_years else None,
            "solicitationCycleNames": ["openTopics"], # Fixed as per original
            "releaseNumbers": [], # Fixed as per original
            "topicReleaseStatus": [591, 592], # Fixed as per original
            "modernizationPriorities": [], # Fixed as per original
            "sortBy": "finalTopicCode,asc", # Fixed as per original
            "technologyAreaIds": [], # Fixed as per original
            "component": None, # Fixed as per original
            "program": None # Fixed as per original
        }

        search_param_json = json.dumps(search_payload)
        encoded_search_param = urllib.parse.quote(search_param_json)
        
        full_url = f"{settings.DOD_SEARCH_API_URL}?searchParam={encoded_search_param}&size={search_request.page_size}&page={search_request.page}"

        resp = await self._request("GET", full_url)
        result = resp.json()
        
        topics_data = result.get("data", [])
        total_elements = result.get("total", 0)
        has_more = (search_request.page + 1) * search_request.page_size < total_elements
        
        topics = [Topic.model_validate(topic) for topic in topics_data]
        return topics, total_elements, has_more

    async def download_pdf_content(self, topic_id: str) -> bytes:
        pdf_url = settings.DOD_PDF_API_TEMPLATE.format(topic_uid=topic_id)
        # PDF download doesn't need Content-Type: application/json
        headers = self.base_headers.copy() 
        if "Content-Type" in headers:
            del headers["Content-Type"]

        resp = await self._request("GET", pdf_url, headers=headers, follow_redirects=True)
        return resp.content

# Custom Exception for the client
class DoDSBIRAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

# Global HTTP client instance (to be managed by lifespan)
http_client_store: Dict[str, httpx.AsyncClient] = {}

async def get_dod_sbir_client() -> DoDSBIRClient:
    if "client" not in http_client_store:
        # This case should ideally not happen if lifespan manager is used correctly
        # Or, create a new one, but it's less efficient.
        raise RuntimeError("HTTP client not initialized. Ensure lifespan manager is set up.")
    return DoDSBIRClient(http_client_store["client"])