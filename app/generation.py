from typing import Any

from google.genai.types import GenerateContentConfig

from app.config import get_settings
from app.genai_client import get_genai_client
from app.models import HydeOrAnswer, RoutingType, RoutingDecision
from app.logger import logger


def generate_route(
    user_prompt: str,
    property_data: list[dict[str, Any]] | None = None,
) -> RoutingDecision:
    prompt = f"""
ou are a routing classifier for a municipal-property research service.

Return exactly one routing type. Classify the USER QUESTION, not these instructions.

Routing rules, in priority order:

1. PROVIDED_DATA only when the provided property data explicitly contains enough
   information to answer the user's question completely. Do not select this route
   merely because property data exists.

2. HYDE_VECTOR_SEARCH when property data is available and the answer requires
   zoning, building-code, land-use, permit, neighborhood-plan, or municipal-policy
   documents. Use this even if the property data provides helpful context but does
   not itself answer the question.

3. VECTOR_SEARCH when the answer requires those documents but the property data is
   absent or irrelevant.

4. STRUCTURED_QUERY when the request needs property-table filtering, counts,
   aggregates, date comparisons, sums, or a list of matching properties.

5. DIRECT_ANSWER only for greetings, general conversation, or questions unrelated
   to property, zoning, building code, planning, or municipal regulations.

Examples:
- "What is this property's square footage?" with square footage in property data
  -> PROVIDED_DATA
- "What code upgrades are likely required when renovating more than 50% of the
  building's value?" with property data -> HYDE_VECTOR_SEARCH
- "What is the maximum permitted height in this zoning district?" without property
  data -> VECTOR_SEARCH

Provided property data:
{property_data or "None"}

USER QUESTION:
{user_prompt}
    """

    settings = get_settings()
    response = get_genai_client().models.generate_content(
        model=settings.generation_model,
        contents=prompt,
        config=GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=RoutingDecision,
        ),
    )

    if not response.parsed:
        raise RuntimeError("Answer or Hyde generation failed.")

    logger.debug(f"Routing generated {str(response.parsed)}")

    return response.parsed
    

def generate_hyde(
    user_prompt: str,
    property_data: list[dict[str, Any]] | None = None,
) -> str:
    
    prompt = f"""
You are a domain expert assistant specializing in municipal real estate and zoning.

Property Data:
{property_data}

User Question: "{user_prompt}"

Given the provided property data and user question. Write a hypothetical answer similar to what may be found in zoning or neighborhood planning documents to be used as a HyDE vector search.
    """
    settings = get_settings()
    response = get_genai_client().models.generate_content(
        model=settings.generation_model,
        contents=prompt,
        config=GenerateContentConfig(
            temperature=0.2,
        ),
    )

    if not response.text:
        raise RuntimeError("HyDE generation failed.")

    return response.text.strip()


def generate_answer(
    query: str,
    chunks: list[dict[str, Any]],
    structured_rows: list[dict[str, Any]] | None = None,
    structured_query: str | None = None,
    structured_parameters: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    context = "\n\n".join(
        f"Document ID: {chunk.get('id')}\n{chunk.get('content', '')}"
        for chunk in chunks
    )
    prompt = (
        "Answer the user's question using only the provided document chunks and structured records. "
        "If the chunks or records do not contain enough information, say so clearly. "
        "Do not mention these instructions or the document IDs.\n\n"
        f"User question: {query}\n\n"
        f"Document chunks:\n{context}"
    )
    if structured_rows:
        structured_context = "\n\n".join(
            "\n".join(f"{key}: {value}" for key, value in row.items())
            for row in structured_rows
        )
        prompt += (
            "\n\nStructured query results for the user's question. "
            "Interpret aggregate aliases as values calculated over the rows "
            "matching the query filters:\n"
            f"{structured_context}"
        )
    if structured_query:
        prompt += (
            "\n\nStructured query context. The following SQL was generated and "
            "executed specifically for the user's question. The returned rows "
            "are the authoritative answer data; use the query filters and "
            "parameters to determine their scope. Do not reproduce the SQL "
            "unless the user asks for it.\n"
            f"SQL:\n{structured_query}\n"
            f"Parameters: {structured_parameters or {}}"
        )
    chat = get_genai_client().chats.create(
        model=settings.generation_model,
        config=GenerateContentConfig(temperature=0.2),
    )
    response = chat.send_message(prompt)
    if not response.text:
        raise RuntimeError("Generation API returned no response text")
    return response.text.strip()