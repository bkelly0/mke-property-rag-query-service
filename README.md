# MKE RAG Query Service

FastAPI service that embeds a query string with the Vertex AI embeddings API and runs a
BigQuery `VECTOR_SEARCH` against a table of pre-embedded documents.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then edit values
gcloud auth application-default login
```

## Run

```powershell
uvicorn app.main:app --reload
```

## Endpoint

`GET /query?q=<text>&top_k=5&include_embedding=false`

Returns a Gemini-generated answer grounded in the matching chunks and a `document_ids`
list identifying the chunks used. `GET /health` is a liveness probe.

## Expected BigQuery table

The configured table needs an `ARRAY<FLOAT64>` embedding column whose dimensionality matches
`EMBEDDING_DIMENSIONALITY`, plus id and content columns. A vector index is optional but
recommended for large tables.
