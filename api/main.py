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
