import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from google.cloud import bigquery

from app.config import get_settings

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_ALLOWED_DISTANCE_TYPES = {"COSINE", "EUCLIDEAN", "DOT_PRODUCT"}
_STRUCTURED_MPROP_SQL = Path(__file__).parent / "sql" / "select_structured_mprop.sql"


def _validate_identifier(value: str, field: str) -> str:
    if not _IDENTIFIER_RE.match(value):
        raise ValueError(f"Invalid BigQuery identifier for {field}: {value!r}")
    return value


@lru_cache
def _get_client() -> bigquery.Client:
    settings = get_settings()
    return bigquery.Client(project=settings.gcp_project_id)


def vector_search(query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
    settings = get_settings()

    project = settings.gcp_project_id
    if not _PROJECT_ID_RE.match(project):
        raise ValueError(f"Invalid GCP project id: {project!r}")
    dataset = _validate_identifier(settings.bq_dataset, "dataset")
    table = _validate_identifier(settings.bq_table, "table")
    embedding_column = _validate_identifier(settings.bq_embedding_column, "embedding_column")
    content_column = _validate_identifier(settings.bq_content_column, "content_column")
    id_column = _validate_identifier(settings.bq_id_column, "id_column")

    distance_type = settings.bq_distance_type.upper()
    if distance_type not in _ALLOWED_DISTANCE_TYPES:
        raise ValueError(f"Unsupported distance type: {distance_type}")

    table_ref = f"`{project}.{dataset}.{table}`"

    sql = f"""
        SELECT
          base.{id_column} AS id,
          base.{content_column} AS content,
          distance
        FROM VECTOR_SEARCH(
          TABLE {table_ref},
          '{embedding_column}',
          (SELECT @query_vector AS {embedding_column}),
          top_k => @top_k,
          distance_type => '{distance_type}'
        )
        ORDER BY distance
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("query_vector", "FLOAT64", query_vector),
            bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
        ]
    )

    rows = _get_client().query(sql, job_config=job_config).result()
    return [dict(row.items()) for row in rows]


def structured_mprop_search(taxkeys: list[str]) -> list[dict[str, Any]]:
    if not all(re.fullmatch(r"\d{1,10}", taxkey) for taxkey in taxkeys):
        raise ValueError("Each taxkey must contain only digits and be at most 10 characters")

    sql = _STRUCTURED_MPROP_SQL.read_text(encoding="utf-8")
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("taxkeys", "STRING", taxkeys)]
    )

    rows = _get_client().query(sql, job_config=job_config).result()
    return [dict(row.items()) for row in rows]
