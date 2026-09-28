from functools import lru_cache

from google import genai

from app.config import get_settings


@lru_cache(maxsize=1)
def get_genai_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
    )