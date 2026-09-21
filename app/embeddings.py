from functools import lru_cache

from google import genai
from google.genai.types import EmbedContentConfig

from app.config import get_settings


@lru_cache
def _get_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
    )


def embed_query(query: str) -> list[float]:
    """Embed a search query with the RETRIEVAL_QUERY task type."""
    settings = get_settings()
    response = _get_client().models.embed_content(
        model=settings.embedding_model,
        contents=query,
        config=EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=settings.embedding_dimensionality,
        ),
    )
    if not response.embeddings or not response.embeddings[0].values:
        raise RuntimeError("Embedding API returned no vector")
    return list(response.embeddings[0].values)
