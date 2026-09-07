from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: str | None = None
    content: str | None = None
    distance: float


class QueryResponse(BaseModel):
    query: str = Field(..., description="The original query string")
    response: str = Field(..., description="Answer generated from the matching chunks")
    document_ids: list[str] = Field(
        default_factory=list,
        description="Document IDs for the chunks used to generate the answer",
    )
