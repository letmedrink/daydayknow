import json

import pytest

from benchmarks.dataset import load_dataset, validate_dataset
from benchmarks.report import compare_reports, render_markdown, write_report
from benchmarks.runner import _judge_result, _provider_public, enforce_pass, run_benchmark


def test_benchmark_dataset_is_versioned_and_has_standard_distribution():
    dataset = load_dataset()
    assert dataset["datasetVersion"] == "1.0.0"
    assert [item["group"] for item in dataset["scenarios"]].count("ingest") == 7
    invalid = json.loads(json.dumps(dataset))
    invalid["scenarios"][1]["id"] = invalid["scenarios"][0]["id"]
    with pytest.raises(ValueError, match="duplicate scenario"):
        validate_dataset(invalid)


@pytest.mark.asyncio
async def test_offline_benchmark_is_deterministic_and_passes_hard_gates(tmp_path):
    first = await run_benchmark("offline")
    second = await run_benchmark("offline")
    assert first["aggregate"] == second["aggregate"]
    assert first["aggregate"]["hardPassed"] is True
    assert first["aggregate"]["scenariosPassed"] == 10
    assert first["aggregate"]["quality"]["requiredClaimRecall"] == 1.0
    assert first["aggregate"]["quality"]["sourceBindingRate"] == 1.0
    assert first["retrieval"]["recallAt3"] >= 0.9
    passed, failures = enforce_pass(first)
    assert passed is True
    assert failures == []

    json_path, markdown_path = write_report(first, tmp_path)
    assert json.loads(json_path.read_text())["datasetVersion"] == "1.0.0"
    markdown = markdown_path.read_text()
    assert "Hard safety invariants | PASS" in markdown
    assert "production SLA" in markdown


@pytest.mark.asyncio
async def test_live_benchmark_requires_an_explicit_configured_provider():
    with pytest.raises(ValueError, match="requires --provider-id"):
        await run_benchmark("live")


@pytest.mark.asyncio
async def test_malformed_judge_output_does_not_discard_deterministic_result(monkeypatch):
    async def malformed(*args, **kwargs):
        return "not-json"

    monkeypatch.setattr("benchmarks.runner.call_llm_with_config", malformed)
    result = await _judge_result(
        {"id": "sample", "source": "fact", "expected": {}},
        {"answer": "fact"},
        "judge",
        {"api_key": "secret", "model": "judge-model"},
        False,
    )
    assert result["providerId"] == "judge"
    assert "error" in result


def test_reports_compare_same_dataset_and_provider_metadata_is_redacted():
    base = {
        "datasetVersion": "1.0.0",
        "runId": "base",
        "aggregate": {"overall": 80, "groups": {"ingest": 80, "query": 80, "lint": 80}, "hardPassed": True},
        "retrieval": {"recallAt1": 0.8, "recallAt3": 1.0, "mrr": 0.9, "latencyP50Ms": 2.0, "latencyP95Ms": 3.0},
    }
    candidate = json.loads(json.dumps(base))
    candidate["runId"] = "candidate"
    candidate["aggregate"]["overall"] = 85
    comparison = compare_reports(base, candidate)
    assert comparison["overallDelta"] == 5

    public = _provider_public("private-provider", {
        "api_key": "must-not-leak",
        "base_url": "https://example.test/v1",
        "model": "candidate-model",
        "api_mode": "openai",
    })
    assert "api_key" not in public
    assert "must-not-leak" not in json.dumps(public)
    assert public["baseUrlHost"] == "example.test"


def test_markdown_report_contains_failed_assertions():
    report = {
        "runId": "failed",
        "mode": "offline",
        "datasetVersion": "1.0.0",
        "gitSha": "abc",
        "pipelineVersion": 3,
        "parserVersion": 1,
        "startedAt": 0,
        "repetitions": 1,
        "provider": {"id": "fake", "model": "fixture"},
        "aggregate": {"overall": 0, "groups": {"ingest": 0, "query": 0, "lint": 0}, "hardPassed": False, "scenariosPassed": 0, "scenariosTotal": 1},
        "retrieval": {"recallAt1": 0, "recallAt3": 0, "mrr": 0, "latencyP50Ms": 0, "latencyP95Ms": 0},
        "scenarios": [{"id": "bad", "group": "ingest", "score": 0, "hardPassed": False, "metrics": {"llmCalls": 0, "durationMs": 0}, "assertions": [{"name": "gate", "passed": False, "detail": "reason"}]}],
    }
    assert "`bad`: `gate` — reason" in render_markdown(report)
