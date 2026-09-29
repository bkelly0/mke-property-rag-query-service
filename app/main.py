import json
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from google.api_core.exceptions import GoogleAPIError
from google.genai.errors import APIError
from pydantic import StringConstraints

from app.bigquery_search import execute_property_query, search_address, structured_mprop_search, vector_search
from app.config import get_settings
from app.embeddings import embed_query
from app.generation import generate_route, generate_answer, generate_hyde
from app.models import AddressSearchResult, QueryResponse
from app.generation_sql import generate_property_query;
from app.generation_routing import generate_retrieval_plan
from app.logger import logger
from app.jwt import verify_token

http_bearer = HTTPBearer()

def _authorize(credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)]) -> None:
    if not verify_token(credentials.credentials, get_settings().jwt_secret_key):
                raise HTTPException(status_code=401, detail="Invalid or expired token")
    

def _parse_cors_value(value: str | None, default: list[str]) -> list[str]:
    if value is None or value == "":
        return default

    candidate = value.strip()
    if not candidate:
        return default

    if candidate.startswith("["):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]

    return [item.strip() for item in candidate.split(",") if item.strip()]


settings = get_settings()
app = FastAPI(
    title="MKE RAG Query Service",
    description="Embeds a query with Vertex AI and runs a BigQuery vector search.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_value(
        settings.cors_origins,
        ["http://localhost:5173", "http://127.0.0.1:5173"],
    ),
    allow_credentials=True,
    allow_methods=_parse_cors_value(settings.cors_methods, ["*"]),
    allow_headers=_parse_cors_value(settings.cors_headers, ["*"]),
)

TaxKey = Annotated[str, StringConstraints(pattern=r"^\d+$", max_length=10)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/search", response_model=list[AddressSearchResult], dependencies=[Depends(_authorize)])
def search(
    q: str = Query(..., min_length=1, max_length=40, description="Address to search for"),
) -> list[AddressSearchResult]:
    try:
        return search_address(q)
    except GoogleAPIError:
        logger.exception("BigQuery address search failed")
        raise HTTPException(status_code=502, detail="Address search failed")


@app.get("/api/v1/rag", response_model=QueryResponse, dependencies=[Depends(_authorize)])
def query(
    q: str = Query(..., min_length=1, max_length=250, description="Question to submit to the RAG"),
    taxkeys: list[TaxKey] | None = Query(None, max_length=100, description="Tax keys to include in reference to the question"),
) -> QueryResponse:
    settings = get_settings()
    limit = settings.default_top_k

    selected_properties = []
    if taxkeys:
        try:
            selected_properties = structured_mprop_search(taxkeys)
        except GoogleAPIError:
            logger.exception("BigQuery structured mprop search failed")
            raise HTTPException(status_code=502, detail="Structured property search failed")

    try:
        plan = generate_retrieval_plan(q, selected_properties)
    except (APIError, RuntimeError):
        logger.exception("Could not generate retrieval plan from user query")
        raise HTTPException(status_code=502, detail="HyDE generation failed")

    query = params = None
    structured_rows = selected_properties
    if plan.structured_query:
            try:
                query, params = generate_property_query(q, selected_properties)
            except (APIError, RuntimeError, ValueError):
                logger.exception("Failed to generate structured property query")
                raise HTTPException(status_code=502, detail="Query generation failed")

            try:
                structured_rows = execute_property_query(query, params)
            except (GoogleAPIError, ValueError):
                logger.exception("Failed to execute structured property query")
                raise HTTPException(status_code=502, detail="Query execution failed")

    vector_search_rows = []
    if plan.vector_search:
        try:
            vector_query = (
                generate_hyde(q, selected_properties)
                if plan.use_hyde
                else q
            )
        except (APIError, RuntimeError):
            logger.exception("Failed to generate HyDE document")
            raise HTTPException(status_code=502, detail="HyDE generation failed")

        try:
            vector = embed_query(vector_query)
        except (APIError, RuntimeError):
            logger.exception("Failed to generate query embedding")
            raise HTTPException(status_code=502, detail="Embedding generation failed")

        try:
            vector_search_rows = vector_search(vector, limit)
        except GoogleAPIError:
            logger.exception("BigQuery vector search failed")
            raise HTTPException(status_code=502, detail="Vector search failed")

    try:
        answer = generate_answer(
            q,
            vector_search_rows,
            structured_rows,
            structured_query=query,
            structured_parameters=params,
        )
    except (APIError, RuntimeError, ValueError):
        logger.exception("Failed to generate answer")
        raise HTTPException(status_code=502, detail="Answer generation failed")


    return QueryResponse(
        query=q,
        response=answer,
        document_ids=set([str(row["id"]) for row in vector_search_rows if row.get("id") is not None]),
        plan=plan,
    )