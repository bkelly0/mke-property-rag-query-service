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

`GET /query?q=<text>&taxkeys=1234567890&taxkeys=9876543210`

Each `taxkeys` value must contain only digits and be no longer than 10 characters.

Returns a Gemini-generated answer grounded in the matching chunks and a `document_ids`
list identifying the chunks used. `GET /health` is a liveness probe.

## Expected BigQuery table

The configured table needs an `ARRAY<FLOAT64>` embedding column whose dimensionality matches
`EMBEDDING_DIMENSIONALITY`, plus id and content columns. A vector index is optional but
recommended for large tables.

## Example questions

- What is the current zoning designation for 123 Main Street, and what uses are permitted there?
- Can I convert this property from a retail storefront into residential apartments?
- What are the maximum building height, lot coverage, and setback requirements for this parcel?
- Does the property lie within a historic district, floodplain, overlay district, or other special zoning area?
- What permits are required to add an accessory dwelling unit (ADU) to this lot?
- Is the existing building compliant with current fire, accessibility, and occupancy code requirements for a change of use?
- Can the building's basement legally be used as habitable living space under applicable building and flood codes?
- What parking spaces are required if I expand the building or change it to a restaurant?
- Can I add a second-story addition, and would it trigger sprinkler, elevator, or accessibility upgrades?
- Is the current use grandfathered, or would a rebuild or major renovation require compliance with today's zoning and building code?
- What variances, special-use permits, or zoning-board approvals would be needed for this proposed project?
- What code upgrades are likely required when renovating more than 50% of the building's value?