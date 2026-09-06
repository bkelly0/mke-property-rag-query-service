import logging

from fastapi import FastAPI, HTTPException, Query
from google.api_core.exceptions import GoogleAPIError
from google.genai.errors import APIError
from google.cloud.logging_v2.handlers import StructuredLogHandler

from app.bigquery_search import vector_search
from app.config import get_settings
from app.embeddings import embed_query
from app.models import QueryResponse, SearchResult


def build_logger() -> logging.Logger:
    logger = logging.getLogger("rag-event-handler")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        # Structured JSON to stdout; Cloud Run/GCP ingests this automatically.
        handler = StructuredLogHandler()
        logger.addHandler(handler)

    return logger

logger = build_logger();
app = FastAPI(
    title="MKE RAG Query Service",
    description="Embeds a query with Vertex AI and runs a BigQuery vector search.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/query", response_model=QueryResponse)
def query(
    q: str = Query(..., min_length=1, max_length=8192, description="Query string to search for"),
    top_k: int | None = Query(None, ge=1, le=100, description="Number of results to return"),
) -> QueryResponse:
    settings = get_settings()
    limit = top_k or settings.default_top_k

    try:
        vector = embed_query(q)
    except (APIError, RuntimeError):
        logger.exception("Failed to generate query embedding")
        raise HTTPException(status_code=502, detail="Embedding generation failed")

    try:
        rows = vector_search(vector, limit)
    except GoogleAPIError:
        logger.exception("BigQuery vector search failed")
        raise HTTPException(status_code=502, detail="Vector search failed")

    return QueryResponse(
        query=q,
        results=[SearchResult(**row) for row in rows],
    )
