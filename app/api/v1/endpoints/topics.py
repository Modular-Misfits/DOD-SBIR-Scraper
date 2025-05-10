from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import StreamingResponse
import io
import zipfile
from typing import List

from app.api.v1.schemas import (
    SearchRequest, SearchResponse, DownloadRequest, ErrorResponse, Topic
)
from app.core.clients.dod_sbir_client import DoDSBIRClient, get_dod_sbir_client, DoDSBIRAPIError

router = APIRouter()

@router.post("/search", 
    response_model=SearchResponse,
    summary="Search SBIR Topics",
    description="Search for SBIR topics based on various criteria.",
    responses={
        400: {"model": ErrorResponse, "description": "Bad request / Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": ErrorResponse, "description": "Error communicating with DoD SBIR API"}
    }
)
async def search_topics_endpoint(
    request: SearchRequest = Body(...),
    client: DoDSBIRClient = Depends(get_dod_sbir_client)
):
    try:
        topics, total, has_more = await client.search_topics(request)
        return SearchResponse(
            topics=topics,
            total=total,
            page=request.page,
            page_size=request.page_size,
            has_more=has_more
        )
    except DoDSBIRAPIError as e:
        # If the client raised an error with a specific status code from the external API
        status_code = e.status_code if e.status_code else 502 # Bad Gateway for upstream errors
        raise HTTPException(
            status_code=status_code,
            detail=ErrorResponse(detail=str(e), code="DOD_API_ERROR").model_dump()
        )
    except Exception as e:
        # Log e
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(detail=f"An unexpected error occurred: {str(e)}", code="INTERNAL_ERROR").model_dump()
        )

@router.post("/download",
    summary="Download Topic PDFs",
    description="Download PDFs for selected topics. Provide topic codes and original search parameters to locate them.",
    responses={
        200: {
            "description": "PDF file or ZIP archive",
            "content": {
                "application/pdf": {},
                "application/zip": {}
            }
        },
        404: {"model": ErrorResponse, "description": "One or more topics not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": ErrorResponse, "description": "Error communicating with DoD SBIR API"}
    }
)
async def download_pdfs_endpoint(
    request: DownloadRequest = Body(...),
    client: DoDSBIRClient = Depends(get_dod_sbir_client)
):
    try:
        # Re-construct search request to find topic IDs for the given topic codes
        # This part is kept from the original logic. A more optimized flow might involve
        # the client sending topic IDs directly, or having a dedicated endpoint in the
        # external API to fetch topic details (including ID) by topic code.
        search_req_for_ids = SearchRequest(
            term=request.search_term,
            page=request.page,
            page_size=request.page_size # Use the original page_size
        )
        # It might be better to fetch ALL results if selected_topics could be from different pages.
        # Or, fetch by topic code if external API supports it.
        # For simplicity, let's assume selected_topics are from the specific page.
        # A more robust solution would fetch ALL topics for the search_term (if not too many)
        # or require client to send topic_ids.
        
        # Fetching a potentially larger set to find the topics if page_size was small
        # This is a heuristic. The best would be if client sent Topic objects (with IDs)
        # or if we could query external API by list of topic codes.
        all_found_topics, _, _ = await client.search_topics(
            SearchRequest(term=request.search_term, page=0, page_size=1000) # Try to get all
        )

        topic_map: dict[str, str] = {topic.topicCode: topic.topicId for topic in all_found_topics}
        
        topics_to_download: List[tuple[str, str]] = [] # (topicCode, topicId)
        not_found_codes: List[str] = []

        for code in request.selected_topics:
            topic_id = topic_map.get(code)
            if topic_id:
                topics_to_download.append((code, topic_id))
            else:
                not_found_codes.append(code)
        
        if not_found_codes:
            # Partial success or complete failure? For now, let's proceed with found ones if any,
            # but raise 404 if ALL requested are not found. If some are found, some not, it's debatable.
            # Original code continued on error, this is similar.
            # A production system might log this or return partial success info.
            if len(topics_to_download) == 0: # All requested topics were not found
                 raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        detail=f"None of the requested topic codes found with the given search parameters: {', '.join(not_found_codes)}",
                        code="TOPIC_NOT_FOUND"
                    ).model_dump()
                )
            # Log or somehow indicate that some topics were not found if needed

        if not topics_to_download: # Should be caught by above, but as a safeguard
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(detail="No valid topics found for download.", code="NO_TOPICS_FOR_DOWNLOAD").model_dump()
            )


        if len(topics_to_download) == 1:
            code, topic_id = topics_to_download[0]
            pdf_content = await client.download_pdf_content(topic_id)
            return StreamingResponse(
                io.BytesIO(pdf_content),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{code}.pdf"'}
            )

        # For multiple files, create a ZIP
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for code, topic_id in topics_to_download:
                try:
                    pdf_content = await client.download_pdf_content(topic_id)
                    zf.writestr(f"{code}.pdf", pdf_content)
                except DoDSBIRAPIError as e:
                    # Log this error, e.g., "Failed to download PDF for topic {code}: {e}"
                    # Decide if one failed download should abort the whole zip or continue
                    print(f"Error downloading PDF for topic {code} (ID: {topic_id}): {e}") # Replace with proper logging
                    # Optionally, add a text file to the zip indicating which files failed
                    zf.writestr(f"ERROR_{code}.txt", f"Failed to download PDF for topic {code}.\nError: {e}")
                    continue 
                except Exception as e:
                    print(f"Unexpected error downloading PDF for topic {code} (ID: {topic_id}): {e}")
                    zf.writestr(f"ERROR_{code}.txt", f"Unexpected error downloading PDF for topic {code}.\nError: {e}")
                    continue


        memory_file.seek(0)
        if not zf.namelist(): # if all downloads failed and zip is empty
             raise HTTPException(
                status_code=500, # Or 502 if all DoDSBIRAPIError
                detail=ErrorResponse(
                    detail="All selected PDF downloads failed. Check individual error logs if available.",
                    code="ALL_DOWNLOADS_FAILED"
                ).model_dump()
            )
        
        return StreamingResponse(
            memory_file,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="selected_pdfs.zip"'}
        )

    except DoDSBIRAPIError as e:
        status_code = e.status_code if e.status_code else 502
        raise HTTPException(
            status_code=status_code,
            detail=ErrorResponse(detail=str(e), code="DOD_API_DOWNLOAD_ERROR").model_dump()
        )
    except HTTPException: # Re-raise HTTPExceptions (like 404 from above)
        raise
    except Exception as e:
        # Log e
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(detail=f"An unexpected error occurred during download: {str(e)}", code="DOWNLOAD_ERROR").model_dump()
        )