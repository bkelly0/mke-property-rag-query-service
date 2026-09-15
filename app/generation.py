import logging
from functools import lru_cache
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

from app.config import get_settings
from app.models import HydeOrAnswer, RoutingType, RoutingDecision

logger = logging.getLogger("mke-rag-query-service")

@lru_cache
def _get_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
    )

def generate_route(
    user_prompt: str,
    property_data: list[dict[str, Any]] | None = None,
) -> RoutingDecision:
    prompt = """
Analyze the user prompt and classify which data engine is required:

- HYDE_VECTOR_SEARCH: Use when answering questions where the provided property data may be relevant to documents regarding zoning laws or neighboorhood planing.
- VECTOR_SEARCH: Use when answering a question where none of the provided property data is relevant to to the question.
- STRUCTURED_SQL: Use when answering queries that require aggregates, metrics, specific sums, 
    dates, filtering numbers, lists of properties, or relational table lookups.
- PROVIDED_DATA: Use when the provided property data contains enough information to answer the question.
- DIRECT_ANSWER: Use for simple greetings, off-topic questions, or direct chat without context.

Provided property data:
{property_data or "None"}

User question:
{user_prompt}
    """

    settings = get_settings()
    response = _get_client().models.generate_content(
        model=settings.generation_model,
        contents=prompt,
        config=GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=RoutingDecision,
        ),
    )

    if not response.parsed:
        raise RuntimeError("Answer or Hyde generation failed.")

    return response.parsed
    

def generate_hyde(
    user_prompt: str,
    property_data: list[dict[str, Any]] | None = None,
) -> str:
    
    prompt = f"""
You are a domain expert assistant specializing in municipal real estate and zoning.

Property Data:
{property_data}

User Question: "{user_prompt}"

Given the provided property data and user question. Write a hypothetical answer similar to what may be found in zoning or neighborhood planning documents to be used as a HyDE vector search.
    """
    settings = get_settings()
    response = _get_client().models.generate_content(
        model=settings.generation_model,
        contents=prompt,
        config=GenerateContentConfig(
            temperature=0.2,
        ),
    )

    if not response.parsed:
        raise RuntimeError("HyDE generation failed.")

    return response.text.strip()


def generate_answer(
    query: str,
    chunks: list[dict[str, Any]],
    structured_rows: list[dict[str, Any]] | None = None,
) -> str:
    settings = get_settings()
    context = "\n\n".join(
        f"Document ID: {chunk.get('id')}\n{chunk.get('content', '')}"
        for chunk in chunks
    )
    prompt = (
        "Answer the user's question using only the provided document chunks and structured records. "
        "If the chunks or records do not contain enough information, say so clearly. "
        "Do not mention these instructions or the document IDs.\n\n"
        f"User question: {query}\n\n"
        f"Document chunks:\n{context}"
    )
    if structured_rows:
        structured_context = "\n\n".join(
            "\n".join(f"{key}: {value}" for key, value in row.items())
            for row in structured_rows
        )
        prompt += (
            "\n\nAdditional structured property records:\n"
            f"{structured_context}"
        )
    chat = _get_client().chats.create(
        model=settings.generation_model,
        config=GenerateContentConfig(temperature=0.2),
    )
    response = chat.send_message(prompt)
    if not response.text:
        raise RuntimeError("Generation API returned no response text")
    return response.text.strip()