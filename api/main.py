"""
API Server - EXACT 2026 Neuro-Symbolic QA System.

FastAPI app expose 2 endpoints:
    POST /query  — nhận question + premises, trả answer + explanation
    GET  /health — health check

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

# [CHANGED] Xóa toàn bộ dead imports (src.*), loguru, tqdm, json, argparse,
# signal, pathlib, dataclasses — tất cả chỉ dùng trong batch runner đã tách
# sang scripts/run_pipeline.py.
# Chỉ giữ imports cần thiết cho FastAPI app.
from fastapi import FastAPI, HTTPException
from api.router import classify_query
from api.schemas import QueryRequest, QueryResponse
from api.logger import get_logger

logger = get_logger(__name__)
app = FastAPI(title="EXACT 2026 QA API", version="0.1.0")


@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    try:
        query_type = classify_query(request.question, request.premises)
        # ❌ MOCK — luôn trả answer="A", không nối với pipeline thật.
        # TODO: Thay bằng:
        #   if query_type == "type1": result = type1_pipeline.run(request)
        #   else:                     result = type2_pipeline.run(request)
        return QueryResponse(
            answer="A",
            explanation=f"[MOCK - {query_type}] Pipeline not yet connected.",
        )
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
