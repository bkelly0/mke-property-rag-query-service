from google.genai.types import GenerateContentConfig
from typing import Any

from app.models import RetrievalPlan
from app.config import get_settings
from app.genai_client import get_genai_client


_RETRIEVAL_PLAN_SYSTEM_INSTRUCTIONS = """
You are a retrieval planner for a municipal-property research service.

Choose every retrieval method needed to answer the user's question. Retrieval
methods are independent and may be combined.

Available methods:

- use_provided_data: Use the supplied property records.
- structured_query: Query the property database for filters, counts, aggregates,
  comparisons, or bounded property lists.
- vector_search: Search zoning, building-code, planning, permit, and municipal
  policy documents.
- use_hyde: Generate a hypothetical document-style query before vector search.
  Use this when property-specific context would improve the document search.

Rules:

1. Set use_provided_data to true when the supplied property records contain
   relevant information needed to answer the question.
2. Set structured_query to true when the answer requires property-table data,
   filtering, counts, aggregates, comparisons, or bounded lists.
3. Set vector_search to true when the answer requires municipal, zoning,
   building-code, planning, permit, or policy documents.
4. Set use_hyde to true only when vector_search is true and property context
   would improve the search query.
5. Set all retrieval methods to false for greetings or questions unrelated to
   property and municipal research.
6. You may select multiple methods.
7. Return JSON only.

Return this shape:

{
  "use_provided_data": boolean,
  "structured_query": boolean,
  "vector_search": boolean,
  "use_hyde": boolean,
  "reasoning": string
}
"""

def generate_retrieval_plan(
    user_prompt: str,
    property_data: list[dict[str, Any]] | None = None,
) -> RetrievalPlan:
    prompt = f"""
<property_data>
{property_data or "None"}
</property_data>

<user_question>
{user_prompt}
</user_question>
    """

    settings = get_settings()
    response = get_genai_client().models.generate_content(
        model=settings.generation_model,
        contents=prompt,
        config=GenerateContentConfig(
            system_instruction=_RETRIEVAL_PLAN_SYSTEM_INSTRUCTIONS,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=RetrievalPlan,
        ),
    )

    if not response.parsed:
        raise RuntimeError("Answer or Hyde generation failed.")

    return response.parsed