import json
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google.api_core.exceptions import GoogleAPIError
from google.genai.errors import APIError
from pydantic import StringConstraints

from app.bigquery_search import execute_property_query, search_address, structured_mprop_search, vector_search
from app.config import get_settings
from app.embeddings import embed_query
from app.generation import generate_route, generate_answer, generate_hyde
from app.models import AddressSearchResult, QueryResponse, RoutingDecision, RoutingType
from app.generation_sql import generate_property_query;
from app.logger import logger


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


@app.get("/api/v1/search", response_model=list[AddressSearchResult])
def search(
    q: str = Query(..., min_length=1, max_length=40, description="Address to search for"),
) -> list[AddressSearchResult]:
    try:
        return search_address(q)
    except GoogleAPIError:
        logger.exception("BigQuery address search failed")
        raise HTTPException(status_code=502, detail="Address search failed")


@app.get("/api/v1/rag", response_model=QueryResponse)
def query(
    q: str = Query(..., min_length=1, max_length=250, description="Question to submit to the RAG"),
    taxkeys: list[TaxKey] | None = Query(None, description="Tax keys to include in reference to the question"),
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
        routing_decision = generate_route(q, selected_properties)
    except (APIError, RuntimeError):
        logger.exception("Could not route user query")
        raise HTTPException(status_code=502, detail="HyDE generation failed")

    answer = ""
    rows = []
    match routing_decision.routing_type:
        case RoutingType.HYDE_VECTOR_SEARCH:
            # Generate HyDE, embed it, then vector search
            try:
                hyde = generate_hyde(q, selected_properties)
            except (APIError, RuntimeError):
                logger.exception("Failed to generate answer or HyDE document")
                raise HTTPException(status_code=502, detail="HyDE generation failed")

            try:
                vector = embed_query(hyde)
            except (APIError, RuntimeError):
                logger.exception("Failed to generate query embedding")
                raise HTTPException(status_code=502, detail="Embedding generation failed")

            try:
                rows = vector_search(vector, limit)
            except GoogleAPIError:
                logger.exception("BigQuery vector search failed")
                raise HTTPException(status_code=502, detail="Vector search failed")

            try:
                answer = generate_answer(q, rows, [])
            except (APIError, RuntimeError):
                logger.exception("Failed to generate answer")
                raise HTTPException(status_code=502, detail="Answer generation failed")

            pass

        case RoutingType.STRUCTURED_QUERY:
            try:
                query, params = generate_property_query(q, selected_properties)
            except (APIError, RuntimeError, ValueError):
                logger.exception("Failed to generate structured property query")
                raise HTTPException(status_code=502, detail="Query generation failed")

            try:
                mprop_rows = execute_property_query(query, params)
            except (GoogleAPIError, ValueError):
                logger.exception("Failed to execute structured property query")
                raise HTTPException(status_code=502, detail="Query execution failed")

            try:
                answer = generate_answer(
                    q,
                    [],
                    mprop_rows,
                    structured_query=query,
                    structured_parameters=params,
                )
            except (APIError, RuntimeError):
                logger.exception("Failed to generate answer")
                raise HTTPException(status_code=502, detail="Answer generation failed")
            pass

        case RoutingType.PROVIDED_DATA:
            try:
                answer = generate_answer(q, [], selected_properties)
            except (APIError, RuntimeError):
                logger.exception("Failed to generate answer")
                raise HTTPException(status_code=502, detail="Answer generation failed")
            pass

        case RoutingType.VECTOR_SEARCH:
            # put user query strait into vector search
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

            try:
                answer = generate_answer(q, rows, [])
            except (APIError, RuntimeError):
                logger.exception("Failed to generate answer")
                raise HTTPException(status_code=502, detail="Answer generation failed")
            pass

        case RoutingType.DIRECT_ANSWER:
            try:
                answer = generate_answer(q, [], [])
            except (APIError, RuntimeError):
                logger.exception("Failed to generate answer")
                raise HTTPException(status_code=502, detail="Answer generation failed")
            pass

        case _:
            raise HTTPException(status_code=500, detail="Unknown routing type")


    return QueryResponse(
        query=q,
        response=answer,
        document_ids=set([str(row["id"]) for row in rows if row.get("id") is not None]),
        routing=routing_decision,
    )