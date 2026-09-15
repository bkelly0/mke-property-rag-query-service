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

class HydeOrAnswer(BaseModel):
    answer: str = Field(description="This field contains the generated answer if it can be answered only with the provided property data.")
    hyde: str = Field(description="A hypothetical excerpt (HyDE) to be used in vector search if additional documents are required to answer the question.")
