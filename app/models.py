from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: str | None = None
    content: str | None = None
    distance: float


class QueryResponse(BaseModel):
    query: str = Field(..., description="The original query string")
    embedding: list[float] = Field(..., description="Embedding vector generated for the query")
    results: list[SearchResult] = Field(default_factory=list)
