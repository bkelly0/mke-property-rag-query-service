import logging
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google.api_core.exceptions import GoogleAPIError
from google.genai.errors import APIError
from google.cloud.logging_v2.handlers import StructuredLogHandler
from pydantic import StringConstraints

from app.bigquery_search import structured_mprop_search, vector_search
from app.config import get_settings
from app.embeddings import embed_query
from app.generation import generate_answer, generate_answer_or_hyde
from app.models import QueryResponse


def build_logger() -> logging.Logger:
    logger = logging.getLogger("mke-rag-query-service")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        # Structured JSON to stdout; Cloud Run/GCP ingests this automatically.
        handler = StructuredLogHandler()
        logger.addHandler(handler)

    return logger

logger = build_logger()
app = FastAPI(
    title="MKE RAG Query Service",
    description="Embeds a query with Vertex AI and runs a BigQuery vector search.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TaxKey = Annotated[str, StringConstraints(pattern=r"^\d+$", max_length=10)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/query", response_model=QueryResponse)
def query(
    q: str = Query(..., min_length=1, max_length=8192, description="Query string to search for"),
    taxkeys: list[TaxKey] | None = Query(None, description="Tax keys to include in the search"),
) -> QueryResponse:
    settings = get_settings()
    limit = settings.default_top_k

    structured_rows = []
    if taxkeys:
        try:
            structured_rows = structured_mprop_search(taxkeys)
        except GoogleAPIError:
            logger.exception("BigQuery structured mprop search failed")
            raise HTTPException(status_code=502, detail="Structured property search failed")

    try:
        answer_or_hyde = generate_answer_or_hyde(q, structured_rows)
    except (APIError, RuntimeError):
        logger.exception("Failed to generate answer or HyDE document")
        raise HTTPException(status_code=502, detail="HyDE generation failed")

    if answer_or_hyde.answer:
        logger.info("The question can be answered using property data without vector search.")
        return QueryResponse(
            query=q,
            response=answer_or_hyde.answer,
            document_ids=[],
        )

    logger.info(f"Generated HyDE document {answer_or_hyde.hyde}")

    try:
        vector = embed_query(answer_or_hyde.hyde)
    except (APIError, RuntimeError):
        logger.exception("Failed to generate query embedding")
        raise HTTPException(status_code=502, detail="Embedding generation failed")

    try:
        rows = vector_search(vector, limit)
    except GoogleAPIError:
        logger.exception("BigQuery vector search failed")
        raise HTTPException(status_code=502, detail="Vector search failed")

    try:
        answer = generate_answer(q, rows, structured_rows)
    except (APIError, RuntimeError):
        logger.exception("Failed to generate answer")
        raise HTTPException(status_code=502, detail="Answer generation failed")

    return QueryResponse(
        query=q,
        response=answer,
        document_ids=set([str(row["id"]) for row in rows if row.get("id") is not None]),
    )
