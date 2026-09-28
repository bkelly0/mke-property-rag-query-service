import os
from types import SimpleNamespace

os.environ.setdefault("PROJECT_ID", "test-project")

from app import generation_sql
from app.models import AggregateSpec, FilterSpec, PropertyQueryPlan


def test_neighborhood_count_uses_selected_property_context(monkeypatch) -> None:
    captured_request = {}
    plan = PropertyQueryPlan(
        filters=[
            FilterSpec(
                field="neighborhood",
                operator="=",
                value="Avenues West",
            )
        ],
        aggregates=[
            AggregateSpec(
                function="count",
                field=None,
                alias="property_count",
            )
        ],
    )

    class Models:
        def generate_content(self, **kwargs):
            captured_request.update(kwargs)
            return SimpleNamespace(parsed=plan, usage_metadata=None)

    monkeypatch.setattr(
        generation_sql,
        "get_genai_client",
        lambda: SimpleNamespace(models=Models()),
    )

    sql, parameters = generation_sql.generate_property_query(
        "how many properties are in the same neighborhood as this property?",
        [{"taxkey": "123", "neighborhood": "Avenues West"}],
    )

    assert "Avenues West" in captured_request["contents"]
    assert (
        "must use a count aggregate"
        in captured_request["config"].system_instruction
    )
    assert "COUNT(*) AS property_count" in sql
    assert "LIMIT" not in sql
    assert parameters == {"filter_0": "Avenues West"}


def test_median_assessed_total_uses_approx_quantiles() -> None:
    plan = PropertyQueryPlan(
        filters=[
            FilterSpec(
                field="neighborhood",
                operator="contains",
                value="Avenues West",
            )
        ],
        aggregates=[
            AggregateSpec(
                function="approx_quantiles",
                field="assessed_total",
                alias="median_total_assessed_value",
            )
        ],
    )

    sql, parameters = generation_sql.build_property_query(plan)

    assert (
        "APPROX_QUANTILES(m.c_a_total, 2)[OFFSET(1)] "
        "AS median_total_assessed_value"
    ) in sql
    assert parameters == {"filter_0": "%Avenues West%"}


def test_street_count_prompt_and_sql_include_all_address_components(
    monkeypatch,
) -> None:
    captured_request = {}
    plan = PropertyQueryPlan(
        filters=[
            FilterSpec(field="street_direction", operator="=", value="N"),
            FilterSpec(field="street_name", operator="=", value="26th"),
            FilterSpec(field="street_type", operator="=", value="St"),
        ],
        aggregates=[
            AggregateSpec(function="count", field=None, alias="property_count")
        ],
    )

    class Models:
        def generate_content(self, **kwargs):
            captured_request.update(kwargs)
            return SimpleNamespace(parsed=plan, usage_metadata=None)

    monkeypatch.setattr(
        generation_sql,
        "get_genai_client",
        lambda: SimpleNamespace(models=Models()),
    )

    sql, parameters = generation_sql.generate_property_query(
        "How many properties are on N26th St?"
    )

    assert "street filters when the question specifies a street" in (
        captured_request["config"].system_instruction
    )
    assert "m.sdir = @filter_0" in sql
    assert "m.street = @filter_1" in sql
    assert "m.sttype = @filter_2" in sql
    assert parameters == {"filter_0": "N", "filter_1": "26th", "filter_2": "St"}