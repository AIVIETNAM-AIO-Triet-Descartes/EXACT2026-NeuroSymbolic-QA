from fastapi import FastAPI, HTTPException
from api.schemas import QueryRequest, QueryResponse
from api.logger import get_logger

logger = get_logger(__name__)
app = FastAPI(title="EXACT 2026 QA API", version="0.1.0")


@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    try:
        # TODO: wire up pipeline
        raise NotImplementedError("Pipeline not yet implemented")
    except NotImplementedError:
        raise
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
