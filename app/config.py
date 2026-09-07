from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gcp_project_id: str = Field(validation_alias="PROJECT_ID")
    gcp_location: str = Field(default="us-central1", validation_alias="LOCATION")

    embedding_model: str = Field(default="text-embedding-005", validation_alias="EMBEDDING_MODEL")
    embedding_dimensionality: int = Field(default=768, validation_alias="EMBEDDING_DIMENSIONALITY")
    generation_model: str = Field(default="gemini-1.5-flash", validation_alias="GENERATION_MODEL")

    bq_dataset: str = Field(default="mke_rag_demo", validation_alias="BQ_DATASET")
    bq_table: str = Field(default="mke_rag_chunks", validation_alias="BQ_TABLE")
    bq_embedding_column: str = Field(default="embedding", validation_alias="BQ_EMBEDDING_COLUMN")
    bq_content_column: str = Field(default="content", validation_alias="BQ_CONTENT_COLUMN")
    bq_id_column: str = Field(default="doc_id", validation_alias="BQ_ID_COLUMN")
    bq_distance_type: str = Field(default="COSINE", validation_alias="BQ_DISTANCE_TYPE")

    default_top_k: int = Field(default=5, validation_alias="DEFAULT_TOP_K")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()