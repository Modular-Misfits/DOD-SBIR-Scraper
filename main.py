import fastapi
from fastapi import Request, Form, Query
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
import httpx # Asynchronous HTTP client
import os
import json
import urllib.parse # For URL encoding
import aiofiles # For async file operations
import io
import zipfile
from typing import List

app = fastapi.FastAPI()

# Setup templates
templates = Jinja2Templates(directory="templates")

SEARCH_API = "https://www.dodsbirsttr.mil/topics/api/public/topics/search"
PDF_API_TEMPLATE = "https://www.dodsbirsttr.mil/topics/api/public/topics/{topic_uid}/download/PDF"

# Create downloads directory if it doesn't exist
os.makedirs('downloads', exist_ok=True)

async def query_api(term: str | None, page: int):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36", # More common UA
            "Referer": "https://www.dodsbirsttr.mil/topics-app/",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json"
        }
        search_payload = {
            "searchText": term if term else None,
            "components": None,
            "programYear": None,
            "solicitationCycleNames": ["openTopics"], # Consider making this configurable or broader
            "releaseNumbers": [],
            "topicReleaseStatus": [591, 592], # These might change, representing "Open" and "Pre-Release"
            "modernizationPriorities": [],
            "sortBy": "finalTopicCode,asc",
            "technologyAreaIds": [],
            "component": None,
            "program": None
        }
        # Encode the search_payload correctly for the URL parameter
        search_param_json = json.dumps(search_payload)
        encoded_search_param = urllib.parse.quote(search_param_json)
        
        full_url = f"{SEARCH_API}?searchParam={encoded_search_param}&size=10&page={page}" # Reduced size for faster testing

        async with httpx.AsyncClient(timeout=30.0) as client: # Added timeout
            resp = await client.get(full_url, headers=headers)
            resp.raise_for_status() # Will raise an httpx.HTTPStatusError for 4xx/5xx
            result = resp.json()
        
        topics_data = result.get("data", [])
        # The API returns totalElements and totalPages, use totalElements for better pagination logic
        total_elements = result.get("total", 0) 
        page_size = 10 # Should match the 'size' parameter above
        has_more = (page + 1) * page_size < total_elements
        
        return topics_data, has_more
    except httpx.HTTPStatusError as e:
        error_detail = f"API request failed with status {e.response.status_code}."
        try:
            error_content = e.response.json()
            error_detail += f" Response: {error_content}"
        except json.JSONDecodeError:
            error_detail += f" Response (text): {e.response.text}"
        raise RuntimeError(error_detail)
    except Exception as e:
        raise RuntimeError(f"API query failed: {e}")

@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    term: str | None = Query(None), # Optional query parameter
    page: int = Query(0, ge=0)      # Query parameter with default 0, must be >= 0
):
    topics = None
    error_message = None
    has_more_pages = False

    if term and term.strip():
        try:
            topics, has_more_pages = await query_api(term.strip(), page)
        except RuntimeError as e:
            error_message = str(e)
            topics = [] # Ensure topics is an empty list on error to avoid template issues
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "topics": topics,
        "term": term,
        "error": error_message,
        "page": page,
        "has_more": has_more_pages
    })

@app.post("/download")
async def download_selected_pdfs(
    request: Request,
    term: str = Form(...),
    page: int = Form(...),
    selected: List[str] = Form(...) # List of selected topic codes
):
    try:
        current_page_topics, _ = await query_api(term, page)
        topic_map = {t['topicCode']: t for t in current_page_topics}
    except RuntimeError as e:
        return HTMLResponse(f"<h2>Error fetching topic list for download: {e}</h2><a href='/?term={term}&page={page}'>Back</a>")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.dodsbirsttr.mil/topics-app/"
    }

    # If only one file is selected, return it directly
    if len(selected) == 1:
        code = selected[0]
        topic_detail = topic_map.get(code)
        if not topic_detail:
            return HTMLResponse(f"<h2>Topic code {code} not found in current page results.</h2><a href='/?term={term}&page={page}'>Back</a>")
        
        uid = topic_detail.get("topicId")
        if not uid:
            return HTMLResponse(f"<h2>UID not found for topic code {code}.</h2><a href='/?term={term}&page={page}'>Back</a>")

        pdf_url = PDF_API_TEMPLATE.format(topic_uid=uid)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(pdf_url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{code}.pdf"'}
            )

    # For multiple files, create a ZIP
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for code in selected:
                topic_detail = topic_map.get(code)
                if not topic_detail:
                    continue
                
                uid = topic_detail.get("topicId")
                if not uid:
                    continue

                pdf_url = PDF_API_TEMPLATE.format(topic_uid=uid)
                
                try:
                    response = await client.get(pdf_url, headers=headers, follow_redirects=True)
                    response.raise_for_status()
                    zf.writestr(f"{code}.pdf", response.content)
                except Exception as e:
                    print(f"Error downloading {code}: {e}")
                    continue

    memory_file.seek(0)
    return StreamingResponse(
        memory_file,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="selected_pdfs.zip"'}
    )

# For running with uvicorn:
# uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    # This is for development only. For production, use a proper ASGI server like Uvicorn/Hypercorn directly.
    uvicorn.run(app, host="0.0.0.0", port=8000)