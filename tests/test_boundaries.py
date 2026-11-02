import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aico import native
from aico.benchmark import benchmark
from aico.providers import CodexProvider, parse_events
from aico.util import AicoError


class ExecutionBoundaries(unittest.TestCase):
    def test_timeout_returns_failure_without_fake_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch("aico.providers.shutil.which", return_value="codex"),
                patch(
                    "aico.providers.subprocess.run",
                    side_effect=subprocess.TimeoutExpired("codex", 1),
                ),
            ):
                result = CodexProvider().execute("task", tmp, timeout=1)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["usage"])

    def test_http_override_is_per_invocation(self):
        class Result:
            returncode = 0

        def fake(command, **kwargs):
            self.assertIn("model_providers.openai.supports_websockets=false", command)
            kwargs["stdout"].write(b'{"type":"turn.completed"}\n')
            return Result()

        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch("aico.providers.shutil.which", return_value="codex"),
                patch("aico.providers.subprocess.run", side_effect=fake),
            ):
                result = CodexProvider(http=True).execute("task", tmp)
        self.assertTrue(result["ok"])
        self.assertIsNone(result["usage"])

    def test_benchmark_preserves_provider_failures(self):
        class Failed:
            def execute(self, *args):
                raise AicoError("Provider unavailable")

        report = benchmark(Failed())
        self.assertEqual(len(report["records"]), 6)
        self.assertEqual(report["summary"]["full"]["measured_runs"], 0)
        self.assertIsNone(report["summary"]["full"]["input_tokens"])
        self.assertEqual(report["summary"]["full"]["passed"], 0)
        self.assertTrue(all(not r["ok"] for r in report["records"]))

    def test_reversed_markers_refused(self):
        with self.assertRaises(AicoError):
            native.merge_agents(
                (native.END + "\n" + native.START).encode(), "replacement"
            )

    def test_changed_plan_hash_refuses_before_write(self):
        with tempfile.TemporaryDirectory(
            dir=os.path.realpath(tempfile.gettempdir())
        ) as tmp:
            root = Path(tmp)
            plan = native.plan(
                {"AGENTS.md": native.START + "\nA\n" + native.END},
                root / "AGENTS.md",
                root / "skills",
            )
            confirm = native.confirmation(plan)
            modified = json.loads(json.dumps(plan))
            modified["changes"][0]["after"] = "tampered"
            with self.assertRaises(AicoError):
                native.apply(modified, root / "home", confirm)
            self.assertFalse((root / "AGENTS.md").exists())


class RecoveredTransportTests(unittest.TestCase):
    def test_success_after_reconnect_is_not_failure(self):
        events = "\n".join(
            [
                '{"type":"error","message":"Reconnecting... 2/5 (request timed out)"}',
                '{"type":"item.completed","item":{"type":"agent_message","text":"READY"}}',
                '{"type":"turn.completed","usage":{"input_tokens":16466,"output_tokens":5,"cached_input_tokens":8064}}',
            ]
        )
        result = parse_events(events)
        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(result["warnings"]), 1)
        self.assertEqual(result["usage"]["input_tokens"], 16466)

    def test_reconnect_without_completion_remains_failed(self):
        result = parse_events('{"type":"error","message":"Reconnecting..."}')
        self.assertFalse(result["ok"])
        self.assertTrue(result["errors"])


class MissingCachedUsageTests(unittest.TestCase):
    def test_unknown_cached_usage_is_null(self):
        result = parse_events(
            '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":2}}'
        )
        self.assertIsNone(result["usage"]["cached_input_tokens"])


class BenchmarkUnknownCachedTests(unittest.TestCase):
    def test_aggregate_unknown_cached_usage_is_null(self):
        class NoCached:
            def execute(self, *args):
                return {
                    "ok": True,
                    "response": "{}",
                    "usage": {
                        "input_tokens": 1,
                        "output_tokens": 1,
                        "cached_input_tokens": None,
                    },
                }

        report = benchmark(NoCached())
        self.assertIsNone(report["summary"]["full"]["cached_input_tokens"])
