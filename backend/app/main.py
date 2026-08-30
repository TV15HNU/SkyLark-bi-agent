import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.monday_client import monday_client
from app.agent import agent
from app.tools import (
    get_deals,
    get_work_orders,
    join_deals_and_work_orders,
    get_data_quality_summary,
    draft_leadership_update,
)

logger = logging.getLogger("main")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.APP_NAME,
    description="Founder-level Business Intelligence Agent over Monday.com Boards for Skylark Drones",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = None
    stream: bool = True

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs_url": "/docs",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """
    Health check verifying Monday.com connection, Groq API configuration, and cache state.
    """
    monday_status = await monday_client.test_connection()
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "monday_integration": monday_status,
        "llm_provider": {
            "model": settings.GROQ_MODEL,
            "configured": bool(settings.GROQ_API_KEY),
            "mode": "groq_live_inference" if bool(settings.GROQ_API_KEY) else "deterministic_planner_fallback"
        },
        "cache": {
            "ttl_seconds": settings.CACHE_TTL_SECONDS,
            "active_cached_keys": list(monday_client._cache.keys())
        }
    }

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Conversational BI endpoint. Supports streaming SSE (default) and standard JSON.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if request.stream:
        async def event_generator():
            try:
                async for event in agent.stream_chat(request.query, request.history):
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Error in stream_chat: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # Non-streaming JSON mode
        result = await agent.run_deterministic_query(request.query)
        return JSONResponse(content=result)

@app.get("/api/data-quality")
async def data_quality_endpoint(board: Optional[str] = Query(None, description="Board to inspect: deals, work_orders, or all")):
    return await get_data_quality_summary(board=board)

@app.get("/api/tools/deals")
async def query_deals_endpoint(
    sector: Optional[List[str]] = Query(None),
    status: Optional[List[str]] = Query(None),
    stage: Optional[List[str]] = Query(None),
    owner: Optional[List[str]] = Query(None),
    force_refresh: bool = Query(False)
):
    return await get_deals(sectors=sector, statuses=status, stages=stage, owners=owner, force_refresh=force_refresh)

@app.get("/api/tools/work-orders")
async def query_work_orders_endpoint(
    sector: Optional[List[str]] = Query(None),
    execution_status: Optional[List[str]] = Query(None),
    billing_status: Optional[List[str]] = Query(None),
    force_refresh: bool = Query(False)
):
    return await get_work_orders(
        sectors=sector, execution_statuses=execution_status, billing_statuses=billing_status, force_refresh=force_refresh
    )

@app.get("/api/tools/join")
async def query_join_endpoint():
    return await join_deals_and_work_orders()

@app.get("/api/tools/leadership-update")
async def leadership_update_endpoint(
    scope: str = Query("overall", description="Scope of report (e.g. 'overall', 'Mining', 'Renewables')"),
    period: str = Query("Current Quarter", description="Report period")
):
    return await draft_leadership_update(scope=scope, period=period)

@app.post("/api/cache/refresh")
async def refresh_cache_endpoint():
    monday_client.clear_cache()
    return {"message": "Cache cleared successfully. Next queries will fetch fresh data."}
