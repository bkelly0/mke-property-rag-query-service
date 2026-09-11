from functools import lru_cache
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

from app.config import get_settings


@lru_cache
def _get_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
    )


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