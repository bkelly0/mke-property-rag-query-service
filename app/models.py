from pydantic import BaseModel, Field
from enum import Enum


class RoutingType(str, Enum):
    HYDE_VECTOR_SEARCH = "hyde_vector_search"
    VECTOR_SEARCH = "vector_search"
    STRUCTURED_QUERY = "structured_query"
    PROVIDED_DATA = "provided_data"
    DIRECT_ANSWER = "direct_answer"


class RoutingDecision(BaseModel):
    routing_type: RoutingType = Field(
        ...,
        description="The best routing type determined by the user prompt",
    )
    reasoning: str = Field(
        ...,
        description="Explanation of why this route was selected.",
    )


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
    routing: RoutingDecision = Field(
        ...,
        description="Routing decision based on user prompt",
    )

class HydeOrAnswer(BaseModel):
    answer: str = Field(description="This field contains the generated answer if it can be answered only with the provided property data.")
    hyde: str = Field(description="A hypothetical excerpt (HyDE) to be used in vector search if additional documents are required to answer the question.")