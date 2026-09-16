from typing import Literal

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

class AggregateSpec(BaseModel):
    function: Literal["count", "min", "max", "avg", "sum"]
    field: str | None = Field(
        default=None,
        description="Allowed field ID; omit for count, which counts rows.",
    )
    alias: str = Field(
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
        description="Unique descriptive snake_case alias for the result column.",
    )


class FilterSpec(BaseModel):
    field: str
    operator: Literal["=", "!=", "<", "<=", ">", ">=", "contains"]
    value: str | int | float | bool


class PropertyQueryPlan(BaseModel):
    select: list[str] = Field(
        default_factory=list,
        description="Allowed field IDs to return, such as address or building_area"
    )
    filters: list[FilterSpec] = Field(
        default_factory=list,
        description="Filters using only approved field IDs and operators",
    )
    aggregates: list[AggregateSpec] = Field(
        default_factory=list,
        description="One or more aggregate expressions with independent aliases.",
    )
    order_by: str | None = None
    order_direction: str | None = Field(default=None, pattern="^(ASC|DESC)$")
    limit: int = Field(default=100, ge=1, le=100)