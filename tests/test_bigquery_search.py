import os

os.environ.setdefault("PROJECT_ID", "test-project")

from app import bigquery_search
from app.models import AddressSearchResult


def test_search_address_returns_address_search_models(monkeypatch) -> None:
    captured_parameters = {}

    def execute_property_query(sql, parameters):
        captured_parameters.update(parameters)
        assert "property_address_search" in sql
        return [
            {
                "taxkey": "1234567890",
                "formatted_address": "123 N WATER ST",
                "distance": 1,
            }
        ]

    monkeypatch.setattr(bigquery_search, "execute_property_query", execute_property_query)

    results = bigquery_search.search_address("123 North Water Street Milwaukee WI")

    assert results == [
        AddressSearchResult(
            taxkey="1234567890",
            formatted_address="123 N WATER ST",
            distance=1,
        )
    ]
    assert captured_parameters == {"search_string": "123 N WATER ST"}