"""The market-query attribution audit over saved source collections."""

from __future__ import annotations

import json

from scripts.audits.market_query_origin import query_class, summarise

TOPIC = "fusion power"
COMPONENTS = ["tokamak reactors", "superconducting magnets"]


def _collection() -> dict:
    return {
        "topic": TOPIC,
        "display_topic": TOPIC,
        "search_components": COMPONENTS,
        "market_sources": [
            {"source_id": "M1", "title": "Tokamak Market Size Report 2026"},
            {"source_id": "M2", "title": "Helion signs power purchase agreement"},
            {"source_id": "M3", "title": "Fusion Energy Market CAGR 2026-2033"},
        ],
        "audit": [
            {"domain": "academic", "query": "fusion power review journal",
             "accepted_source_ids": ["M9"]},
            {"domain": "market", "query": "tokamak reactors company product commercial deployment 2025 2026",
             "accepted_source_ids": ["M1", "M2"]},
            {"domain": "market", "query": "fusion power market size revenue commercial manufacturer 2025 2026",
             "accepted_source_ids": ["M3"]},
            {"domain": "market", "query": "[Relevance-Filter]", "accepted_source_ids": []},
        ],
    }


def test_query_classes_follow_template_wording_not_topic_length():
    """A six-word topic's short form equals the full topic; wording decides."""
    assert query_class("fusion power market size revenue commercial manufacturer 2025 2026",
                       COMPONENTS, TOPIC) == "market-size"
    assert query_class("fusion power company commercial deployment industry news",
                       COMPONENTS, TOPIC) == "topic-deployment"
    assert query_class("superconducting magnets company product commercial deployment 2025 2026",
                       COMPONENTS, TOPIC) == "component"
    assert query_class("fusion power approval authorization site:fda.gov",
                       COMPONENTS, TOPIC) == "authority"
    assert query_class("[Deferred-Promotion]", COMPONENTS, TOPIC) == "pipeline-pass"


def test_summary_attributes_sources_and_counts_queries_that_ran(tmp_path):
    run = tmp_path / "H02-fusion-power"
    run.mkdir()
    (run / "validated_sources.json").write_text(json.dumps(_collection()), encoding="utf-8")

    summary = summarise(tmp_path)

    assert summary["runs"] == 1
    assert summary["market_sources"] == 3
    assert summary["by_query_class"]["component"] == {
        "queries_run": 1, "sources": 2, "market_size_titled": 1}
    assert summary["by_query_class"]["market-size"] == {
        "queries_run": 1, "sources": 1, "market_size_titled": 1}
    assert summary["by_query_class"]["pipeline-pass"]["sources"] == 0
    assert "topic-deployment" not in summary["by_query_class"]
