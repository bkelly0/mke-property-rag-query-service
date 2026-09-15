import logging
from functools import lru_cache
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

from app.config import get_settings
from app.models import HydeOrAnswer



logger = logging.getLogger("mke-rag-query-service")



@lru_cache
def _get_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
    )

def generate_answer_or_hyde(
    user_prompt: str,
    property_data: list[dict[str, Any]] | None = None,
) -> HydeOrAnswer:
    
    prompt = f"""
You are a domain expert assistant specializing in municipal real estate and zoning.

Property Data:
{property_data}

User Question: "{user_prompt}"

Task:
1. Determine if the "Property Data" contains enough specific information to fully answer the user's question.
2. If the loaded property data IS SUFFICIENT, write an answer to the question in the "answer" field.
3. If the loaded property data IS NOT SUFFICIENT,  (e.g., the question requires broader municipal zoning codes, city ordinances, or general regulatory context), write a detailed, hypothetical passage that directly answers the question to be used for vector retrieval in the "hyde" field.
    """
    settings = get_settings()
    response = _get_client().models.generate_content(
        model=settings.generation_model,
        contents=prompt,
        config=GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=HydeOrAnswer,
        ),
    )

    if not response.parsed:
        raise RuntimeError("Answer or Hyde generation failed.")

    return response.parsed


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