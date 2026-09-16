from typing import Any

from google.genai.types import GenerateContentConfig

from app.config import get_settings
from app.genai_client import get_genai_client
from app.models import PropertyQueryPlan

from app.logger import log_model_usage, logger


PROPERTY_QUERY_PROMPT = """
Base table: mprop_master (alias: m)

Available fields:

- house_number_low: low/start house number
- house_number_high: high/end house number; use when the address represents a range
- house_number_suffix: house-number suffix, such as A or 1/2
- street_direction: street directional prefix, such as N, S, E, or W
- street_name: street name
- street_type: street type or suffix, such as St, Ave, Rd, or Blvd
- building_type_desc: building type description
- convey_type_desc: conveyance type description
- num_stories: number of stories
- has_basement: whether the property has a basement
- has_attic: whether the property has an attic
- has_fireplace: whether the property has a fireplace
- num_rooms: total number of rooms
- num_bedrooms: number of bedrooms
- num_baths: number of full bathrooms
- num_half_bath: number of half bathrooms
- year_built: year the building was built
- building_area: building area
- lot_area: lot area
- historic_code: historic designation code
- historic_desc: historic designation description
- zoning: zoning code
- zip: ZIP code
- taxkey: unique property tax key
- assessment_class: assessment class code
- assessment_class_desc: assessment class description
- assessed_total: current total assessed value
- assessed_land: current assessed land value
- assessed_improvement: current assessed improvement value
- prev_assessed_total: previous total assessed value
- prev_assessed_land: previous assessed land value
- prev_assessed_improvement: previous assessed improvement value
- assessment_year: assessment year
- land_use_description: land-use description
- land_use_category_description: land-use category description
- zoning_district_name: zoning district name
- owner_name_1: primary owner name
- owner_name_2: secondary owner name
- owner_name_3: tertiary owner name
- owner_address: owner mailing address
- last_ownership_change: most recent ownership-change date
- neighborhood: neighborhood name
- current_excemption_code: current exemption code
- current_excemption_type_desc: current exemption type description
- alderman_dist: aldermanic district
- police_dist: police district
- fire_dist: fire district
- num_units: number of dwelling units

Available relationships:
- building_type: building type descriptions
- conveyance_type: conveyance type descriptions
- assessment_class: assessment class descriptions
- land_use: land-use descriptions and categories
- zoning_district: zoning district names
- property_location: neighborhood names
- exemption_type: exemption type descriptions

Field-to-relationship rules:

- neighborhood requires the property_location relationship and must use field
  "neighborhood".
- building_type_desc requires building_type.
- convey_type_desc requires conveyance_type.
- assessment_class_desc requires assessment_class.
- land_use_description and land_use_category_description require land_use.
- zoning_district_name requires zoning_district.
- current_excemption_type_desc requires exemption_type.

When a question mentions a neighborhood, use a filter like:
{"field": "neighborhood", "operator": "contains", "value": "Avenues West"}

Do not use "property_location" as a field name. It is a relationship name.

Choose required_relationships only when a requested field requires it.

Return a JSON PropertyQueryPlan. Use only the available field names. Use filters
with field, operator, and value keys. Allowed operators are =, !=, <, <=, >, >=,
and contains. Do not generate SQL.
Avoid returning more than 100 rows.

Use aggregates for one or more aggregate expressions. Each aggregate must contain
function, field, and alias. The function must be count, min, max, avg, or sum.
For count, omit field or set it to null to count rows. For all other functions,
field must be an allowed field name. Every alias must be unique, descriptive,
snake_case, and different from generic names such as count, value, result, or f0.
The same function may be used on different fields; create a separate aggregate
entry and alias for each field. If select fields and aggregates are both present,
the select fields are grouping fields.

Questions asking "how many", "what number of", or otherwise requesting a count
must use a count aggregate with field set to null. Do not select individual rows
for the application to count. Leave select empty unless the user requests counts
grouped by a field.

Use the provided property data to resolve references such as "this property".
For example, "the same neighborhood as this property" means filtering neighborhood
by the neighborhood value in the provided property data.

Example:
{"select": ["zoning"], "aggregates": [
    {"function": "count", "field": null, "alias": "property_count"},
    {"function": "avg", "field": "building_area", "alias": "average_building_area"},
    {"function": "avg", "field": "lot_area", "alias": "average_lot_area"}
]}
"""

ALLOWED_FIELDS = {
    "house_number_low": "m.house_nr_lo",
    "house_number_high": "m.house_nr_hi",
    "house_number_suffix": "m.house_nr_sfx",
    "street_direction": "m.sdir",
    "street_name": "m.street",
    "street_type": "m.sttype",
    "building_type_desc": "bt.description",
    "convey_type_desc": "ct.description",
    "num_stories": "ROUND(m.nr_stories, 2)",
    "has_basement": "m.basement = 'Y'",
    "has_attic": "m.attic = 'Y'",
    "has_fireplace": "m.fireplace = '1'",
    "num_rooms": "m.nr_rooms",
    "num_bedrooms": "m.bedrooms",
    "num_baths": "m.baths",
    "num_half_bath": "m.powder_rooms",
    "year_built": "m.yr_built",
    "building_area": "ROUND(m.bldg_area, 3)",
    "lot_area": "ROUND(m.lot_area, 3)",
    "historic_code": "m.hist_code",
    "historic_desc": """CASE
        WHEN m.hist_code = "1" THEN "National Register of Historic Places and locally designated."
        WHEN m.hist_code = "2" THEN "National Register of Historic Places, but no local designation."
        WHEN m.hist_code = "3" THEN "Eligible for National Register of Historic Places and locally designated."
        WHEN m.hist_code = "4" THEN "Eligible for National Register of Historic Places, but no designation."
        WHEN m.hist_code = "5" THEN "Not on National Register of Historic Places, but locally designated."
        WHEN m.hist_code = "7" THEN "On National Register of Historic Places, and Historic Local Easement."
        ELSE ""
    END""",
    "zoning": "m.zoning",
    "zip": "m.geo_zip_code",
    "taxkey": "m.taxkey",
    "assessment_class": "m.c_a_class",
    "assessment_class_desc": 'IFNULL(ac1.description, "unknown")',
    "assessed_total": "m.c_a_total",
    "assessed_land": "m.c_a_land",
    "assessed_improvement": "m.c_a_imprv",
    "prev_assessed_total": "m.p_a_total",
    "prev_assessed_land": "m.p_a_land",
    "prev_assessed_improvement": "m.p_a_imprv",
    "assessment_year": "m.yr_assmt",
    "land_use_description": "lu.land_use_description",
    "land_use_category_description": "lu.land_use_category_description",
    "zoning_district_name": "zc.district_name",
    "owner_name_1": "m.owner_name_1",
    "owner_name_2": "m.owner_name_2",
    "owner_name_3": "m.owner_name_3",
    "owner_address": """TRIM(CONCAT(
        IFNULL(m.owner_mail_addr, ""), " ",
        IFNULL(m.owner_city_state, ""), " ",
        IFNULL(SUBSTRING(m.owner_zip, 0, 5), "")
    ))""",
    "last_ownership_change": "m.last_name_chg",
    "neighborhood": "loc.neighborhood_name",
    "current_excemption_code": "m.c_a_exm_type",
    "current_excemption_type_desc": "ex.description",
    "alderman_dist": "m.geo_alder",
    "police_dist": "m.geo_police",
    "fire_dist": "m.geo_fire",
    "num_units": "m.nr_units",
}

ALLOWED_JOINS = {
    "building_type": (
        "LEFT OUTER JOIN `mke_rag_demo.building_types` bt "
        "ON bt.code = m.bldg_type"
    ),
    "conveyance_type": (
        "LEFT OUTER JOIN `mke_rag_demo.conveyance_types` ct "
        "ON ct.code = m.convey_type"
    ),
    "assessment_class": (
        "LEFT OUTER JOIN `mke_rag_demo.assessment_classes` ac1 "
        "ON ac1.code = m.c_a_class"
    ),
    "land_use": (
        "LEFT OUTER JOIN `mke_rag_demo.land_use` lu "
        "ON lu.land_use_code = m.land_use"
    ),
    "zoning_district": (
        "LEFT OUTER JOIN `mke_rag_demo.zoning_codes` zc "
        "ON zc.map_indicator_value = m.zoning"
    ),
    "property_location": (
        "LEFT OUTER JOIN `mke_rag_demo.property_locations` loc "
        "ON loc.taxkey = m.taxkey"
    ),
    "exemption_type": (
        "LEFT OUTER JOIN `mke_rag_demo.exemption_types` ex "
        "ON ex.code = m.c_a_exm_type"
    ),
}

_JOIN_BY_ALIAS = {
    "ac1": "assessment_class",
    "bt": "building_type",
    "ct": "conveyance_type",
    "ex": "exemption_type",
    "loc": "property_location",
    "lu": "land_use",
    "zc": "zoning_district",
}
_ALLOWED_OPERATORS = {"=", "!=", "<", "<=", ">", ">=", "contains"}
_ALLOWED_AGGREGATES = {"count", "min", "max", "avg", "sum"}
_BASE_TABLE = "`mke_rag_demo.mprop_master` m"


def generate_property_query_plan(
    user_prompt: str,
    property_data: list[dict[str, Any]] | None = None,
) -> PropertyQueryPlan:
    settings = get_settings()
    response = get_genai_client().models.generate_content(
        model=settings.generation_model,
        contents=(
            f"{PROPERTY_QUERY_PROMPT}\n\n"
            f"Provided property data:\n{property_data or 'None'}\n\n"
            f"User question:\n{user_prompt}"
        ),
        config=GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=PropertyQueryPlan,
        ),
    )
    log_model_usage(response, "property_query_plan", settings.generation_model)
    if not response.parsed:
        raise RuntimeError("Property query generation failed.")

    return response.parsed


def build_property_query(plan: PropertyQueryPlan) -> tuple[str, dict[str, Any]]:
    """Validate a model-produced plan and compile it into parameterized BigQuery SQL."""

    if not plan.aggregates and not plan.select:
        raise ValueError("A query must select at least one field or aggregate")

    aliases = [aggregate.alias for aggregate in plan.aggregates]
    if len(aliases) != len(set(aliases)):
        raise ValueError("Aggregate aliases must be unique")

    for filter_ in plan.filters:
        if filter_.field not in ALLOWED_FIELDS:
            raise ValueError(f"Unsupported filter field: {filter_.field!r}")

    aggregate_fields = [
        aggregate.field
        for aggregate in plan.aggregates
        if aggregate.field is not None
    ]
    referenced_fields = [
        *plan.select,
        *aggregate_fields,
        *(filter_.field for filter_ in plan.filters),
    ]
    if plan.order_by:
        referenced_fields.append(plan.order_by)

    unknown_fields = set(referenced_fields) - ALLOWED_FIELDS.keys()
    if unknown_fields:
        raise ValueError(f"Unsupported fields: {', '.join(sorted(unknown_fields))}")

    joins = {
        _JOIN_BY_ALIAS[expression.split(".", 1)[0]]
        for field in referenced_fields
        if (expression := ALLOWED_FIELDS[field]).split(".", 1)[0] in _JOIN_BY_ALIAS
    }

    select_expressions = [f"{ALLOWED_FIELDS[field]} AS {field}" for field in plan.select]
    for aggregate in plan.aggregates:
        if aggregate.function == "count":
            if aggregate.field is None:
                expression = "*"
            else:
                expression = ALLOWED_FIELDS[aggregate.field]
        elif aggregate.field is None:
            raise ValueError(f"{aggregate.function} requires a field")
        else:
            expression = ALLOWED_FIELDS[aggregate.field]
        select_expressions.append(
            f"{aggregate.function.upper()}({expression}) AS {aggregate.alias}"
        )

    parameters: dict[str, Any] = {}
    where_clauses = []
    for index, filter_ in enumerate(plan.filters):
        field = filter_.field
        operator = filter_.operator
        value = filter_.value

        parameter_name = f"filter_{index}"
        expression = ALLOWED_FIELDS[field]
        if operator == "contains":
            where_clauses.append(
                f"LOWER({expression}) LIKE LOWER(@{parameter_name})"
            )
            parameters[parameter_name] = f"%{value}%"
        else:
            where_clauses.append(f"{expression} {operator} @{parameter_name}")
            parameters[parameter_name] = value

    sql = f"SELECT {', '.join(select_expressions)}\nFROM {_BASE_TABLE}"
    if joins:
        sql += "\n" + "\n".join(ALLOWED_JOINS[join] for join in sorted(joins))
    if where_clauses:
        sql += "\nWHERE " + " AND ".join(where_clauses)
    if plan.order_by:
        direction = plan.order_direction or "ASC"
        sql += f"\nORDER BY {ALLOWED_FIELDS[plan.order_by]} {direction}"
    if plan.aggregates and plan.select:
        sql += "\nGROUP BY " + ", ".join(ALLOWED_FIELDS[field] for field in plan.select)
    if not plan.aggregates:
        sql += "\nLIMIT @limit"
        parameters["limit"] = plan.limit

    return sql, parameters


def generate_property_query(
    user_prompt: str,
    property_data: list[dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any]]:
    return build_property_query(generate_property_query_plan(user_prompt, property_data))