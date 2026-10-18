"""Attribute each saved market source to the query that admitted it.

Reads only the validated_sources.json files of a finished benchmark batch; it
never searches. Each market source is attributed to the first audited market
query that accepted it, and the query is classed by its template. A class is a
template family, not a claim about the page: "market-size titled" is a title
pattern, counted as a lower bound in the 2026-10-18 diagnosis.

    uv run python -m scripts.audits.market_query_origin outputs/benchmark-runs/<batch>
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

SIZE_TITLE = re.compile(
    r"market (size|report|share|trends|forecast|analysis|outlook|research)|research report|"
    r"CAGR|billion|市场规模|市场报告|行业报告|研究报告|市场分析|市场前景",
    re.I,
)
_AUTHORITY_SITES = ("site:fda.gov", "site:ema.europa.eu", "site:clinicaltrials.gov")
# Template wording, matched after the topic phrase. The topic part is not
# compared: short and full topic forms coincide for topics of six words or less.
_TEMPLATES = (
    ("market size revenue commercial manufacturer", "market-size"),
    ("market report investment startup", "market-size"),
    ("company commercial deployment industry news", "topic-deployment"),
    ("product manufacturer revenue commercial sales", "topic-revenue"),
    ("industry company deployment commercial scale", "topic-industry"),
)


def query_class(query: str, components: list[str], display_topic: str) -> str:
    """The template family a recorded market query came from."""
    if query.startswith("["):
        return "pipeline-pass"
    if any(site in query for site in _AUTHORITY_SITES):
        return "authority"
    if any(query.startswith(f"{c} company product commercial deployment") for c in components):
        return "component"
    if query == display_topic:
        return "native"
    for wording, cls in _TEMPLATES:
        if wording in query:
            return cls
    return "topic-other"


def audit_run(collection: dict) -> tuple[list[tuple[str, str]], list[str]]:
    """(query class, title) per market source, and the class of every query run."""
    components = collection.get("search_components") or []
    first_owner: dict[str, str] = {}
    executed: list[str] = []
    for audit in collection["audit"]:
        if audit["domain"] != "market":
            continue
        executed.append(query_class(audit["query"], components, collection["display_topic"]))
        for source_id in audit["accepted_source_ids"]:
            first_owner.setdefault(source_id, query_class(
                audit["query"], components, collection["display_topic"]))
    sources = [(first_owner.get(source["source_id"], "unattributed"), source["title"])
               for source in collection["market_sources"]]
    return sources, executed


def summarise(batch: Path) -> dict:
    slots: Counter[str] = Counter()
    size_titled: Counter[str] = Counter()
    queries_run: Counter[str] = Counter()
    runs = 0
    for path in sorted(batch.glob("*/validated_sources.json")):
        runs += 1
        sources, executed = audit_run(json.loads(path.read_text(encoding="utf-8")))
        queries_run.update(executed)
        for cls, title in sources:
            slots[cls] += 1
            size_titled[cls] += bool(SIZE_TITLE.search(title))
    return {
        "runs": runs,
        "market_sources": sum(slots.values()),
        "by_query_class": {
            cls: {"queries_run": queries_run[cls], "sources": slots[cls],
                  "market_size_titled": size_titled[cls]}
            for cls in sorted(set(slots) | set(queries_run), key=lambda c: -slots[c])
        },
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("batch", type=Path, help="a benchmark batch directory")
    args = parser.parse_args(argv)
    print(json.dumps(summarise(args.batch), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
