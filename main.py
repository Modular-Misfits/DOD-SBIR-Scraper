import fastapi
from fastapi import Request, Form, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx
import os
import json
import urllib.parse
import io
import zipfile
from typing import List, Optional
from math import ceil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = fastapi.FastAPI()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "..", "static")), name="static")

SEARCH_API = "https://www.dodsbirsttr.mil/topics/api/public/topics/search"
PDF_API_TEMPLATE = "https://www.dodsbirsttr.mil/topics/api/public/topics/{topic_uid}/download/PDF"
QUESTIONS_API_TEMPLATE = "https://www.dodsbirsttr.mil/topics/api/public/topics/{topic_uid}/questions"

# Static option values
PROGRAMS = ["SBIR", "STTR"]
COMPONENTS = ["ARMY", "CBD", "DARPA", "DHA", "MDA", "DTRA", "DMEA", "DLA", "NAVY", "OSD", "SOCOM", "USAF"]
TECH_AREAS = ["TA1", "TA2", "TA3", "TA4", "TA5", "TA6", "TA7", "TA8", "TA9", "TA10", "TA11", "TA12", "TA13"]
MOD_PRIORITIES = ["AI", "Cyber", "Quantum", "Hypersonics", "5G", "Biotech"]  # Replace with real mappings if needed
SOLICITATIONS = ["AF 24.1", "Navy FY24", "Army Open 2024"]  # Stubbed – you'll need to map this from live data if needed
TOPIC_STATUSES = ["Pre-Release", "Open", "Closed"]

async def query_api(term: Optional[str], page: int, page_size: int) -> tuple:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.dodsbirsttr.mil/topics-app/",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    }
    payload = {
        "searchText": term if term else None,
        "components": None,
        "programYear": None,
        "solicitationCycleNames": ["openTopics"],
        "releaseNumbers": [],
        "topicReleaseStatus": [591, 592],
        "modernizationPriorities": [],
        "sortBy": "finalTopicCode,asc",
        "technologyAreaIds": [],
        "component": None,
        "program": None
    }

    encoded = urllib.parse.quote(json.dumps(payload))
    url = f"{SEARCH_API}?searchParam={encoded}&size={page_size}&page={page}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    total = data.get("total", 0)
    topics = data.get("data", [])
    has_more = (page + 1) * page_size < total
    total_pages = ceil(total / page_size) if page_size else 1
    return topics, total, has_more, total_pages

@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    term: Optional[str] = Query(None),
    page: int = Query(0, ge=0),
    page_size: int = Query(10, ge=1, le=100),
    program: Optional[str] = Query(None),
    component: Optional[str] = Query(None),
    technology_area: Optional[str] = Query(None),
    modernization_priority: Optional[str] = Query(None),
    solicitation: Optional[str] = Query(None),
    topic_status: Optional[str] = Query(None)
):
    topics = []
    total_pages = 1
    has_more_pages = False
    error_message = None

    try:
        topics, total, has_more_pages, total_pages = await query_api(term, page, page_size)
    except Exception as e:
        error_message = f"Error querying API: {e}"

    return templates.TemplateResponse("index.html", {
        "request": request,
        "topics": topics,
        "term": term,
        "page": page,
        "page_size": page_size,
        "has_more": has_more_pages,
        "total_pages": total_pages,
        "error": error_message,
        "programs": PROGRAMS,
        "components": COMPONENTS,
        "technology_areas": TECH_AREAS,
        "modernization_priorities": MOD_PRIORITIES,
        "solicitations": SOLICITATIONS,
        "topic_statuses": TOPIC_STATUSES,
        "selected_program": program,
        "selected_component": component,
        "selected_technology_area": technology_area,
        "selected_modernization_priority": modernization_priority,
        "selected_solicitation": solicitation,
        "selected_topic_status": topic_status
    })

@app.get("/questions/{topic_id}", response_class=HTMLResponse)
async def view_questions(request: Request, topic_id: str):
    questions_url = QUESTIONS_API_TEMPLATE.format(topic_uid=topic_id)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(questions_url)
            response.raise_for_status()
            questions = response.json()
    except Exception as e:
        return templates.TemplateResponse("questions.html", {
            "request": request,
            "topic_id": topic_id,
            "error": str(e),
            "questions": []
        })

    return templates.TemplateResponse("questions.html", {
        "request": request,
        "topic_id": topic_id,
        "questions": questions,
        "error": None
    })

@app.post("/download")
async def download_selected_pdfs(
    request: Request,
    term: str = Form(...),
    page: int = Form(...),
    selected: List[str] = Form(...)
):
    try:
        topics, _, _, _ = await query_api(term, page, 10)
        topic_map = {t['topicCode']: t for t in topics}
    except Exception as e:
        return HTMLResponse(f"<h2>Error fetching topic list for download: {e}</h2><a href='/?term={term}&page={page}'>Back</a>")

    headers = {"User-Agent": "Mozilla/5.0"}

    if len(selected) == 1:
        code = selected[0]
        topic = topic_map.get(code)
        if not topic:
            return HTMLResponse(f"<h2>Topic code {code} not found.</h2>")
        uid = topic.get("topicId")
        pdf_url = PDF_API_TEMPLATE.format(topic_uid=uid)
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(pdf_url, headers=headers)
            r.raise_for_status()
            return StreamingResponse(
                io.BytesIO(r.content),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{code}.pdf"'}
            )

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for code in selected:
                topic = topic_map.get(code)
                if not topic:
                    continue
                uid = topic.get("topicId")
                pdf_url = PDF_API_TEMPLATE.format(topic_uid=uid)
                try:
                    r = await client.get(pdf_url, headers=headers)
                    r.raise_for_status()
                    zf.writestr(f"{code}.pdf", r.content)
                except Exception:
                    continue

    memory_file.seek(0)
    return StreamingResponse(
        memory_file,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="selected_pdfs.zip"'}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
