"""Synthetic paired instruction-adherence benchmark, not coding-quality proof."""

import json
import tempfile

from .router import prompt_for, route
from .util import AicoError, digest


def fixture():
    rules = [
        {
            "id": "format",
            "kind": "global",
            "status": "approved",
            "project": "",
            "name": "",
            "text": "For this benchmark, respond only with a JSON object, without Markdown fences.",
            "key": "",
            "value": "",
            "triggers": [],
        }
    ]
    cases = []
    for keyword, value in [
        ("python", "pytest -q"),
        ("javascript", "npm test"),
        ("rust", "cargo test"),
    ]:
        rules.append(
            {
                "id": keyword,
                "kind": "skill",
                "status": "approved",
                "project": "",
                "name": keyword,
                "text": "When asked for the "
                + keyword
                + " test command, return exactly "
                + json.dumps({"command": value})
                + ".",
                "key": "",
                "value": "",
                "triggers": [keyword],
            }
        )
        cases.append(
            {
                "task": "What is the " + keyword + " test command?",
                "expected": {"command": value},
            }
        )
    for i in range(24):
        rules.append(
            {
                "id": "unused-%02d" % i,
                "kind": "skill",
                "status": "approved",
                "project": "",
                "name": "archive-%02d" % i,
                "text": "For archive-format-%02d tasks only: inspect the schema version, verify checksums, retain original timestamps, record missing metadata, and report validation issues before suggesting any changes. Never invent validation evidence."
                % i,
                "key": "",
                "value": "",
                "triggers": ["archive-format-%02d" % i],
            }
        )
    return rules, cases


def benchmark(provider=None, model="", repeats=1, timeout=180):
    if not 1 <= repeats <= 10:
        raise AicoError("repeats must be 1..10")
    rules, cases = fixture()
    records = []
    with tempfile.TemporaryDirectory(prefix="aico-benchmark-") as tmp:
        for repeat in range(repeats):
            for case in cases:
                modes = ("full", "routed") if repeat % 2 == 0 else ("routed", "full")
                for mode in modes:
                    report = route(
                        rules, case["task"], tmp, max_bytes=100000, full=mode == "full"
                    )
                    prompt = prompt_for(case["task"], report)
                    record = {
                        "repeat": repeat,
                        "task": case["task"],
                        "mode": mode,
                        "prompt_sha256": digest(prompt.encode()),
                        "context_bytes": report["context_bytes"],
                        "passed": None,
                        "usage": None,
                    }
                    if provider is not None:
                        try:
                            result = provider.execute(prompt, tmp, model, timeout)
                        except AicoError as exc:
                            result = {
                                "ok": False,
                                "response": "",
                                "usage": None,
                                "errors": [str(exc)],
                            }
                        try:
                            passed = json.loads(result["response"]) == case["expected"]
                        except ValueError:
                            passed = False
                        record.update(result)
                        record["passed"] = bool(result["ok"] and passed)
                    records.append(record)
    summaries = {}
    for mode in ("full", "routed"):
        rows = [r for r in records if r["mode"] == mode]
        measured = [r for r in rows if r["usage"] is not None]
        summaries[mode] = {
            "runs": len(rows),
            "measured_runs": len(measured),
            "passed": sum(r["passed"] is True for r in rows) if provider else None,
            "input_tokens": sum(r["usage"]["input_tokens"] for r in measured)
            if measured
            else None,
            "output_tokens": sum(r["usage"]["output_tokens"] for r in measured)
            if measured
            else None,
            "cached_input_tokens": sum(
                r["usage"]["cached_input_tokens"] for r in measured
            )
            if measured
            and all(r["usage"].get("cached_input_tokens") is not None for r in measured)
            else None,
        }
    return {
        "schema": 1,
        "live": provider is not None,
        "suite": "synthetic-instruction-adherence-v1",
        "method": "Full approved AICO context versus keyword-routed AICO context; paired synthetic tasks.",
        "limitations": [
            "Three simple exact-JSON tasks do not establish coding success or general token savings.",
            "Codex native rules, skills, provider config and prompt caching may affect both arms.",
            "Byte counts are not tokens. Missing usage is null. No price/cost is inferred.",
            "Order alternates by repeat; use multiple repeats and a pinned model for comparisons.",
        ],
        "summary": summaries,
        "records": records,
    }
