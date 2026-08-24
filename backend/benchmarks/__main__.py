"""Command line interface for llmwiki benchmarks."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .report import compare_reports, load_report, write_report
from .runner import enforce_pass, run_benchmark


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run reproducible llmwiki benchmarks")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run = subcommands.add_parser("run", help="run the offline or live benchmark suite")
    run.add_argument("--mode", choices=("offline", "live"), required=True)
    run.add_argument("--provider-id", default="")
    run.add_argument("--judge-provider-id", default="")
    run.add_argument("--repetitions", type=int, default=1)
    run.add_argument("--dataset")
    run.add_argument("--output-dir")
    run.add_argument("--enforce", action="store_true", help="return non-zero when quality thresholds fail")

    compare = subcommands.add_parser("compare", help="compare two JSON reports")
    compare.add_argument("baseline")
    compare.add_argument("candidate")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "compare":
        comparison = compare_reports(load_report(args.baseline), load_report(args.candidate))
        print(json.dumps(comparison, ensure_ascii=False, indent=2))
        return 0

    try:
        report = asyncio.run(run_benchmark(
            args.mode,
            provider_id=args.provider_id,
            judge_provider_id=args.judge_provider_id,
            repetitions=args.repetitions,
            dataset_path=args.dataset,
        ))
        json_path, markdown_path = write_report(report, args.output_dir)
        passed, failures = enforce_pass(report)
        print(f"overall={report['aggregate']['overall']:.2f} hard_passed={report['aggregate']['hardPassed']}")
        print(f"json={json_path}")
        print(f"markdown={markdown_path}")
        if failures:
            print("thresholds: " + "; ".join(failures), file=sys.stderr)
        return 1 if (args.enforce or args.mode == "offline") and not passed else 0
    except Exception as exc:
        print(f"benchmark failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
