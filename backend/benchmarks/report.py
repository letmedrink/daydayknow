"""Benchmark report persistence, rendering, and comparison."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_output_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "benchmark-results"


def write_report(report: dict[str, Any], output_dir: str | Path | None = None) -> tuple[Path, Path]:
    target = Path(output_dir) if output_dir else default_output_dir()
    target.mkdir(parents=True, exist_ok=True)
    stem = report["runId"]
    json_path = target / f"{stem}.json"
    markdown_path = target / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    retrieval = report["retrieval"]
    provider = report["provider"]
    started = datetime.fromtimestamp(report["startedAt"] / 1000, tz=timezone.utc).isoformat()
    lines = [
        f"# llmwiki Benchmark — {report['runId']}",
        "",
        f"- Mode: `{report['mode']}`",
        f"- Dataset: `{report['datasetVersion']}`",
        f"- Git SHA: `{report['gitSha']}`",
        f"- Pipeline / parser: `{report['pipelineVersion']}` / `{report['parserVersion']}`",
        f"- Provider: `{provider.get('id')}` / `{provider.get('model')}`",
        f"- Started (UTC): `{started}`",
        f"- Repetitions: `{report['repetitions']}`",
        "",
        "## Scorecard",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        f"| Overall | {aggregate['overall']:.2f} |",
        f"| Ingest | {aggregate['groups']['ingest']:.2f} |",
        f"| Query | {aggregate['groups']['query']:.2f} |",
        f"| Lint | {aggregate['groups']['lint']:.2f} |",
        f"| Hard safety invariants | {'PASS' if aggregate['hardPassed'] else 'FAIL'} |",
        f"| Scenarios | {aggregate['scenariosPassed']} / {aggregate['scenariosTotal']} |",
        "",
        "## Quality metrics",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
    ]
    for name, value in aggregate.get("quality", {}).items():
        rendered = "n/a" if value is None else f"{value:.4f}"
        lines.append(f"| {name} | {rendered} |")
    lines.extend([
        "",
        "## Retrieval",
        "",
        "| Recall@1 | Recall@3 | MRR | P50 | P95 |",
        "| ---: | ---: | ---: | ---: | ---: |",
        f"| {retrieval['recallAt1']:.4f} | {retrieval['recallAt3']:.4f} | {retrieval['mrr']:.4f} | {retrieval['latencyP50Ms']:.3f} ms | {retrieval['latencyP95Ms']:.3f} ms |",
        "",
        "## Scenarios",
        "",
        "| Scenario | Group | Score | Hard gates | Calls | Duration |",
        "| --- | --- | ---: | --- | ---: | ---: |",
    ])
    for scenario in report["scenarios"]:
        lines.append(
            f"| `{scenario['id']}` | {scenario['group']} | {scenario['score']:.2f} | "
            f"{'PASS' if scenario['hardPassed'] else 'FAIL'} | {scenario['metrics']['llmCalls']} | "
            f"{scenario['metrics']['durationMs']:.1f} ms |"
        )
    failures = [
        (scenario["id"], assertion)
        for scenario in report["scenarios"]
        for assertion in scenario["assertions"]
        if not assertion["passed"]
    ]
    if failures:
        lines.extend(["", "## Failed assertions", ""])
        for scenario_id, assertion in failures:
            suffix = f" — {assertion['detail']}" if assertion.get("detail") else ""
            lines.append(f"- `{scenario_id}`: `{assertion['name']}`{suffix}")
    lines.extend([
        "",
        "## Methodology note",
        "",
        "This is a single-process synthetic benchmark, not a production SLA. Latency depends on hardware, provider, network, model version, and load. Hard safety invariants are evaluated separately from weighted quality scores.",
        "",
    ])
    return "\n".join(lines)


def compare_reports(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    if baseline.get("datasetVersion") != candidate.get("datasetVersion"):
        raise ValueError("reports use different dataset versions")
    groups = {}
    for group in ("ingest", "query", "lint"):
        groups[group] = round(candidate["aggregate"]["groups"][group] - baseline["aggregate"]["groups"][group], 2)
    return {
        "datasetVersion": baseline["datasetVersion"],
        "baseline": baseline["runId"],
        "candidate": candidate["runId"],
        "overallDelta": round(candidate["aggregate"]["overall"] - baseline["aggregate"]["overall"], 2),
        "groupDeltas": groups,
        "retrieval": {
            key: round(candidate["retrieval"][key] - baseline["retrieval"][key], 4)
            for key in ("recallAt1", "recallAt3", "mrr", "latencyP50Ms", "latencyP95Ms")
        },
        "hardPassed": candidate["aggregate"]["hardPassed"],
    }


def load_report(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
