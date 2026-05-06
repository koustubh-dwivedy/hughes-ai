"""Pure unit tests for api.service.data_model_service."""

from datetime import datetime

from api.repo.data_model import aggregate_nl_counts
from api.service.data_model_service import compose_graph, compose_node_detail


def _model_node(uid: str, name: str, layer: str, parents: list[str]) -> dict:
    return {
        "unique_id": uid,
        "name": name,
        "resource_type": "model",
        "fqn": ["hughes_ai", layer, name],
        "description": "Manifest description.",
        "config": {"materialized": "table" if layer == "marts" else "view"},
        "depends_on": {"nodes": list(parents)},
        "columns": {
            "as_of_month": {
                "name": "as_of_month",
                "description": "Month start.",
                "data_type": "DATE",
            },
        },
        "raw_code": "SELECT 1",
        "original_file_path": f"models/{layer}/{name}.sql",
    }


def _source_node(uid: str, name: str) -> dict:
    return {
        "unique_id": uid,
        "name": name,
        "resource_type": "source",
        "fqn": ["hughes_ai", "staging", "raw", name],
        "description": "",
        "source_name": "raw",
        "original_file_path": "models/staging/sources.yml",
    }


def _manifest() -> dict:
    stg = _model_node(
        "model.hughes_ai.stg_symitar_loans",
        "stg_symitar_loans",
        "staging",
        ["source.hughes_ai.raw.booked_loans"],
    )
    mart = _model_node(
        "model.hughes_ai.fct_loans_monthly",
        "fct_loans_monthly",
        "marts",
        ["model.hughes_ai.stg_symitar_loans"],
    )
    test_node = {
        "unique_id": "test.hughes_ai.some_test",
        "name": "some_test",
        "resource_type": "test",
        "fqn": ["hughes_ai", "test", "some_test"],
    }
    return {
        "nodes": {
            stg["unique_id"]: stg,
            mart["unique_id"]: mart,
            test_node["unique_id"]: test_node,
        },
        "sources": {
            "source.hughes_ai.raw.booked_loans": _source_node(
                "source.hughes_ai.raw.booked_loans", "booked_loans"
            ),
        },
    }


def _dashboard_map() -> list[dict]:
    return [
        {
            "id": "dashboard.executive",
            "name": "Executive Summary",
            "route": "/dashboards/executive",
            "backed_by": ["fct_loans_monthly"],
        },
    ]


def test_compose_graph_buckets_by_layer() -> None:
    resp = compose_graph(
        manifest=_manifest(),
        dashboard_map=_dashboard_map(),
        nl_counts={},
        audit_id="aid",
    )
    layers = {n.id: n.layer for n in resp.nodes}
    assert layers["source.hughes_ai.raw.booked_loans"] == "Sources"
    assert layers["model.hughes_ai.stg_symitar_loans"] == "Staging"
    assert layers["model.hughes_ai.fct_loans_monthly"] == "Marts"
    assert layers["dashboard.executive"] == "Dashboards"
    # Test node skipped.
    assert "test.hughes_ai.some_test" not in layers


def test_compose_graph_includes_dashboard_edges() -> None:
    resp = compose_graph(
        manifest=_manifest(),
        dashboard_map=_dashboard_map(),
        nl_counts={},
        audit_id="aid",
    )
    edges = {(e.source, e.target) for e in resp.edges}
    src = "source.hughes_ai.raw.booked_loans"
    stg = "model.hughes_ai.stg_symitar_loans"
    mart = "model.hughes_ai.fct_loans_monthly"
    assert (src, stg) in edges
    assert (stg, mart) in edges
    assert (mart, "dashboard.executive") in edges


def test_compose_graph_uses_manifest_description() -> None:
    """HUG-193: Surface 1's prose grounding YAMLs are gone, so node
    descriptions come exclusively from the dbt manifest."""
    resp = compose_graph(
        manifest=_manifest(),
        dashboard_map=[],
        nl_counts={},
        audit_id="aid",
    )
    fct = next(n for n in resp.nodes if n.name == "fct_loans_monthly")
    assert fct.description == "Manifest description."


def test_compose_graph_stamps_nl_counts() -> None:
    resp = compose_graph(
        manifest=_manifest(),
        dashboard_map=[],
        nl_counts={"fct_loans_monthly": 4, "booked_loans": 1},
        audit_id="aid",
    )
    by_name = {n.name: n for n in resp.nodes}
    assert by_name["fct_loans_monthly"].nl_query_count_30d == 4
    assert by_name["booked_loans"].nl_query_count_30d == 1
    assert by_name["stg_symitar_loans"].nl_query_count_30d == 0


def test_compose_node_detail_pulls_columns_from_manifest() -> None:
    detail = compose_node_detail(
        node_id="model.hughes_ai.fct_loans_monthly",
        manifest=_manifest(),
        dashboard_map=_dashboard_map(),
        nl_counts={},
        run_results={},
    )
    assert detail is not None
    assert [c.name for c in detail.columns] == ["as_of_month"]
    assert detail.columns[0].description == "Month start."
    assert detail.dashboards[0].route == "/dashboards/executive"
    assert detail.parents == ["model.hughes_ai.stg_symitar_loans"]
    assert detail.children == []
    assert detail.sql == "SELECT 1"
    assert detail.last_run_at is None


def test_compose_node_detail_returns_none_for_unknown() -> None:
    assert (
        compose_node_detail(
            node_id="model.hughes_ai.nope",
            manifest=_manifest(),
            dashboard_map=_dashboard_map(),
            nl_counts={},
            run_results={},
        )
        is None
    )


def test_compose_node_detail_dashboard_node() -> None:
    detail = compose_node_detail(
        node_id="dashboard.executive",
        manifest=_manifest(),
        dashboard_map=_dashboard_map(),
        nl_counts={},
        run_results={},
    )
    assert detail is not None
    assert detail.kind == "dashboard"
    assert detail.parents == ["model.hughes_ai.fct_loans_monthly"]


def test_compose_node_detail_attaches_last_run_at() -> None:
    ts = datetime(2026, 5, 1, 12, 0, 0)
    detail = compose_node_detail(
        node_id="model.hughes_ai.fct_loans_monthly",
        manifest=_manifest(),
        dashboard_map=_dashboard_map(),
        nl_counts={},
        run_results={"model.hughes_ai.fct_loans_monthly": ts},
    )
    assert detail is not None
    assert detail.last_run_at == ts


def test_aggregate_nl_counts_dedupes_within_query() -> None:
    counts = aggregate_nl_counts(
        [
            ["fct_loans_monthly", "fct_loans_monthly", "dim_loan"],
            ["fct_loans_monthly"],
            [],
        ]
    )
    assert counts == {"fct_loans_monthly": 2, "dim_loan": 1}
