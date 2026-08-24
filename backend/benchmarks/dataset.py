"""Versioned benchmark dataset loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import DATASET_VERSION


DATASET_PATH = Path(__file__).parent / "fixtures" / "scenarios.json"
GROUPS = {"ingest", "query", "lint"}
ACTIONS = {"ingest", "query", "query_backfill", "lint"}


def load_dataset(path: str | Path | None = None) -> dict[str, Any]:
    dataset_path = Path(path) if path else DATASET_PATH
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    validate_dataset(data)
    return data


def validate_dataset(data: dict[str, Any]) -> None:
    if data.get("datasetVersion") != DATASET_VERSION:
        raise ValueError(
            f"datasetVersion must be {DATASET_VERSION}, got {data.get('datasetVersion')!r}"
        )
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 10:
        raise ValueError("the standard dataset must contain exactly 10 scenarios")
    ids: set[str] = set()
    groups = {"ingest": 0, "query": 0, "lint": 0}
    for scenario in scenarios:
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str) or not scenario_id:
            raise ValueError("every scenario requires a non-empty id")
        if scenario_id in ids:
            raise ValueError(f"duplicate scenario id: {scenario_id}")
        ids.add(scenario_id)
        group = scenario.get("group")
        action = scenario.get("action")
        if group not in GROUPS or action not in ACTIONS:
            raise ValueError(f"invalid group/action in scenario {scenario_id}")
        if not isinstance(scenario.get("expected"), dict):
            raise ValueError(f"scenario {scenario_id} requires expected assertions")
        groups[group] += 1
    if groups != {"ingest": 7, "query": 2, "lint": 1}:
        raise ValueError(f"scenario group distribution must be 7/2/1, got {groups}")
    retrieval = data.get("retrievalCases")
    if not isinstance(retrieval, list) or not retrieval:
        raise ValueError("retrievalCases must not be empty")
    for case in retrieval:
        if not all(isinstance(case.get(key), str) and case[key] for key in ("query", "goldPath", "title", "body")):
            raise ValueError("every retrieval case requires query, goldPath, title and body")


def expanded_source(scenario: dict[str, Any]) -> str:
    source = str(scenario.get("source", ""))
    padding = int(scenario.get("sourcePaddingChars", 0))
    if padding:
        filler = ("背景记录仅用于分块覆盖测试。" * ((padding // 14) + 1))[:padding]
        source = source.replace("{{PADDING}}", filler)
    return source
