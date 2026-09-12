import json
import logging
from functools import lru_cache
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

from app.config import get_settings

logger = logging.getLogger("mke-rag-query-service")


@lru_cache
def _get_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
    )


def generate_hyde_document(
    user_prompt: str,
    property_data: list[dict[str, Any]] | None = None,
) -> str:
    """Generate a hypothetical municipal code/zoning/property excerpt (HyDE) to embed for retrieval."""
    settings = get_settings()
    hyde_prompt = f"""
Given this property profile:
{json.dumps(property_data or [], default=str)}

Write a hypothetical excerpt from the municipal code, zoning text, or property data that answers this question:
"{user_prompt}"
"""
    response = _get_client().models.generate_content(
        model=settings.generation_model,
        contents=hyde_prompt,
        config=GenerateContentConfig(temperature=0.2),
    )
    if not response.text:
        raise RuntimeError("HyDE generation API returned no response text")
    hyde_document = response.text.strip()
    logger.info("HyDE document generated: %s", hyde_document)    
    return hyde_document


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