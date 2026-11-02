import contextlib
import io
import json
import os
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from aico import native
from aico.benchmark import benchmark
from aico.cli import main
from aico.parser import MAX_BYTES, extract
from aico.providers import CodexProvider, parse_events
from aico.router import prompt_for, route
from aico.store import Store
from aico.util import AicoError, digest


class TempCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            dir=os.path.realpath(tempfile.gettempdir())
        )
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def source(self, text, name="rules.md"):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path


class ParserTests(TempCase):
    def test_markdown_requires_structure(self):
        path = self.source(
            "# Heading\nParagraph of commentary\n- Always test changes\nRULE: Keep secrets local\n规则: 谨慎核实\n1. Report evidence\n```\n- not a rule\n```\n"
        )
        rows = extract(path)
        self.assertEqual(
            [r["text"] for r in rows],
            [
                "Always test changes",
                "Keep secrets local",
                "谨慎核实",
                "Report evidence",
            ],
        )
        self.assertEqual(rows[0]["source"]["section"], "Heading")
        self.assertEqual(rows[0]["source"]["position"], 3)
        self.assertNotIn(str(self.root), json.dumps(rows))
        self.assertEqual(rows[0]["source"]["sha256"], digest(path.read_bytes()))

    def test_prose_opt_in_and_utf8_bom(self):
        path = self.source("\ufeffPlain paragraph", "rules.txt")
        self.assertEqual(extract(path), [])
        self.assertEqual(extract(path, True)[0]["text"], "Plain paragraph")

    def docx(self, xml):
        path = self.root / "synthetic.docx"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", xml)
        return path

    def test_docx_paragraphs_and_table(self):
        xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Safety</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:pPr><w:numPr/></w:pPr><w:r><w:t>Keep </w:t></w:r><w:r><w:t>backups</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
        rows = extract(self.docx(xml))
        self.assertEqual(rows[0]["text"], "Keep backups")
        self.assertEqual(rows[0]["source"]["section"], "Safety")

    def test_docx_entities_rejected(self):
        with self.assertRaises(AicoError):
            extract(self.docx('<!DOCTYPE a [<!ENTITY x "secret">]><a>&x;</a>'))

    def test_docx_expansion_limit(self):
        with self.assertRaises(AicoError):
            extract(self.docx("x" * (MAX_BYTES + 1)))

    def test_plain_limit_and_unsupported(self):
        with self.assertRaises(AicoError):
            extract(self.source("x" * (MAX_BYTES + 1)))
        with self.assertRaises(AicoError):
            extract(self.source("test", "file.pdf"))


class StoreTests(TempCase):
    def setUp(self):
        super().setUp()
        self.store = Store(self.root / "home")
        self.addCleanup(self.store.close)

    def add(self, text="Run tests", **kwargs):
        return self.store.add_many([{"text": text}], **kwargs)[0]

    def test_pending_review_history_restore(self):
        rule = self.add()
        self.assertEqual(rule["status"], "pending")
        self.store.update(rule["id"], status="approved")
        self.store.update(rule["id"], text="Changed")
        restored = self.store.restore(rule["id"], 1)
        self.assertEqual(restored["version"], 4)
        self.assertEqual(restored["text"], "Run tests")
        self.assertEqual(restored["status"], "pending")
        self.assertEqual(len(self.store.history(rule["id"])), 4)

    def test_persistence(self):
        rule = self.add()
        other = Store(self.root / "home")
        try:
            self.assertEqual(other.get(rule["id"]), rule)
        finally:
            other.close()

    def test_import_all_or_nothing(self):
        with self.assertRaises(AicoError):
            self.store.add_many([{"text": "ok"}, {"text": ""}])
        self.assertEqual(self.store.list(), [])

    def test_invalid_scopes_and_skill_names(self):
        for kwargs in (
            {"kind": "project"},
            {"kind": "skill", "name": "../../bad", "triggers": ["x"]},
            {"kind": "skill", "name": "good"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(AicoError):
                self.add(**kwargs)

    def test_invalid_updates_do_not_create_revision(self):
        rule = self.add()
        with self.assertRaises(AicoError):
            self.store.update(rule["id"], status="unknown")
        self.assertEqual(len(self.store.history(rule["id"])), 1)
        with self.assertRaises(AicoError):
            self.store.restore(rule["id"], 999)

    def test_unknown_and_metadata(self):
        with self.assertRaises(AicoError):
            self.store.get("missing")
        with self.assertRaises(AicoError):
            self.add(tags="bad")
        with self.assertRaises(AicoError):
            self.store.update(self.add()["id"], project="bad")

    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_private_database(self):
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)

    def test_future_schema_rejected(self):
        db = sqlite3.connect(self.root / "future.sqlite3")
        db.execute("PRAGMA user_version=99")
        db.close()
        folder = self.root / "future"
        folder.mkdir()
        (self.root / "future.sqlite3").rename(folder / "registry.sqlite3")
        with self.assertRaises(AicoError):
            Store(folder)


class RoutingTests(TempCase):
    def rule(self, rid, text="Rule", **kwargs):
        item = dict(
            id=rid,
            text=text,
            kind="global",
            status="approved",
            project="",
            triggers=[],
            name="",
            key="",
            value="",
        )
        item.update(kwargs)
        return item

    def test_review_scope_trigger_and_duplicates(self):
        rows = [
            self.rule("a", "Always test"),
            self.rule("b", " Always   test "),
            self.rule("c", "Pending", status="pending"),
            self.rule("d", "Other project", project="/other"),
            self.rule("e", "Check API", kind="skill", triggers=["api"]),
        ]
        result = route(rows, "review API", self.root)
        self.assertEqual(result["selected_ids"], ["a", "e"])
        self.assertEqual(result["context_bytes"], len(result["context"].encode()))
        self.assertFalse(result["blocked"])

    def test_same_scope_conflict_blocks(self):
        rows = [
            self.rule("a", key="language", value="en"),
            self.rule("b", key="language", value="zh"),
        ]
        result = route(rows, "task", self.root)
        self.assertTrue(result["blocked"])
        with self.assertRaises(AicoError):
            prompt_for("task", result)

    def test_project_conflict_precedence(self):
        rows = [
            self.rule("a", "English", key="language", value="en"),
            self.rule(
                "b",
                "中文",
                kind="project",
                project=str(self.root),
                key="language",
                value="zh",
            ),
        ]
        result = route(rows, "task", self.root)
        self.assertFalse(result["blocked"])
        self.assertEqual(result["selected_ids"], ["b"])
        self.assertEqual(result["conflicts"][0]["resolution"], "project precedence")

    def test_mandatory_never_silently_dropped(self):
        result = route([self.rule("a", "x" * 100)], "t", self.root, 10)
        self.assertTrue(result["blocked"])
        self.assertIn("a", result["selected_ids"])
        with self.assertRaises(AicoError):
            route([], "t", self.root, -1)

    def test_optional_budget_and_full(self):
        rows = [self.rule("s", "x" * 100, kind="skill", triggers=["review"])]
        self.assertEqual(route(rows, "review", self.root, 10)["selected_ids"], [])
        self.assertEqual(route(rows, "other", self.root, 1000)["selected_ids"], [])
        self.assertEqual(
            route(rows, "other", self.root, 1000, full=True)["selected_ids"], ["s"]
        )

    def test_utf8_budget(self):
        result = route([self.rule("a", "中文")], "t", self.root)
        self.assertGreater(result["context_bytes"], len(result["context"]))


class NativeTests(TempCase):
    def setUp(self):
        super().setUp()
        self.agents = self.root / "project/AGENTS.md"
        self.skills = self.root / "project/.agents/skills"
        self.home = self.root / "home"
        self.files = {
            "AGENTS.md": native.START + "\nRules\n" + native.END + "\n",
            ".agents/skills/test/SKILL.md": "---\nname: test\ndescription: test\n---\n"
            + native.SKILL_MARKER
            + "\nTest",
        }

    def plan(self):
        return native.plan(self.files, self.agents, self.skills)

    def apply(self, plan=None):
        plan = plan or self.plan()
        return native.apply(plan, self.home, native.confirmation(plan))

    def test_preview_does_not_write_target(self):
        plan = self.plan()
        self.assertFalse(self.agents.exists())
        self.assertEqual(len(plan["changes"]), 2)
        self.assertIn("+Rules", str(plan))

    def test_apply_and_rollback_exact_bytes(self):
        self.agents.parent.mkdir()
        original = b"Existing instructions\r\nKeep this."
        self.agents.write_bytes(original)
        result = self.apply()
        self.assertTrue(self.agents.read_bytes().startswith(original))
        self.assertTrue((self.skills / "test/SKILL.md").exists())
        native.rollback(self.home, result["install_id"])
        self.assertEqual(self.agents.read_bytes(), original)
        self.assertFalse((self.skills / "test/SKILL.md").exists())

    def test_idempotent_and_update(self):
        self.apply()
        self.assertEqual(self.plan()["changes"], [])
        self.files["AGENTS.md"] = self.files["AGENTS.md"].replace("Rules", "Updated")
        self.apply()
        self.assertEqual(self.agents.read_text().count(native.START), 1)
        self.assertIn("Updated", self.agents.read_text())

    def test_hash_and_stale_plan(self):
        plan = self.plan()
        with self.assertRaises(AicoError):
            native.apply(plan, self.home, "bad")
        self.agents.parent.mkdir()
        self.agents.write_text("User edit")
        with self.assertRaises(AicoError):
            self.apply(plan)
        self.assertEqual(self.agents.read_text(), "User edit")

    def test_unmanaged_skill_refused(self):
        skill = self.skills / "test/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("Original skill")
        with self.assertRaises(AicoError):
            self.plan()
        self.assertFalse(self.agents.exists())

    def test_shadowing_and_malformed_markers_refused(self):
        self.agents.parent.mkdir()
        override = self.agents.with_name("AGENTS.override.md")
        override.write_text("Higher precedence")
        with self.assertRaises(AicoError):
            self.plan()
        override.unlink()
        self.agents.write_text(native.START)
        with self.assertRaises(AicoError):
            self.plan()

    @unittest.skipIf(os.name == "nt", "Symlink creation permission differs on Windows")
    def test_symlink_target_and_parent_refused(self):
        self.agents.parent.mkdir()
        other = self.source("Unchanged", "other.md")
        self.agents.symlink_to(other)
        with self.assertRaises(AicoError):
            self.plan()
        self.assertEqual(other.read_text(), "Unchanged")

    def test_modified_installed_file_refuses_rollback(self):
        result = self.apply()
        self.agents.write_text("User edit")
        with self.assertRaises(AicoError):
            native.rollback(self.home, result["install_id"])
        self.assertTrue((self.skills / "test/SKILL.md").exists())

    def test_corrupted_backup_refuses_all_rollback(self):
        self.agents.parent.mkdir()
        self.agents.write_text("Before")
        result = self.apply()
        for path in (self.home / "backups" / result["install_id"]).glob("*.bak"):
            path.write_text("Corrupt")
        with self.assertRaises(AicoError):
            native.rollback(self.home, result["install_id"])
        self.assertIn("Rules", self.agents.read_text())

    def test_apply_failure_restores_prior_writes(self):
        real_write = native.atomic_write

        def fail(path, data, mode=0o600):
            if str(path).endswith("SKILL.md"):
                raise OSError("simulated disk failure")
            return real_write(path, data, mode)

        plan = self.plan()
        # AGENTS must be first to exercise restoration of an earlier write.
        plan["changes"].sort(key=lambda c: not c["path"].endswith("AGENTS.md"))
        with (
            patch("aico.native.atomic_write", side_effect=fail),
            self.assertRaises(OSError),
        ):
            self.apply(plan)
        self.assertFalse(self.agents.exists())

    def test_render_scope_and_safe_yaml(self):
        rows = [
            dict(
                id="a",
                text="Rule",
                kind="global",
                status="approved",
                project="",
                name="",
                key="",
                value="",
                triggers=[],
            ),
            dict(
                id="s",
                text="Skill",
                kind="skill",
                status="approved",
                project="",
                name="test",
                description='A: "quoted"\nline',
                key="",
                value="",
                triggers=["test"],
            ),
        ]
        result = native.render(rows, "global", self.root)
        self.assertIn('description: "A:', result[".agents/skills/test/SKILL.md"])
        self.assertEqual(set(native.render(rows, "project", self.root)), {"AGENTS.md"})
        rows.append(dict(rows[1], id="other"))
        with self.assertRaises(AicoError):
            native.render(rows, "global", self.root)


class ProviderTests(TempCase):
    def test_real_usage_and_message(self):
        events = "\n".join(
            [
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "OK"},
                    }
                ),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 123,
                            "output_tokens": 4,
                            "cached_input_tokens": 100,
                        },
                    }
                ),
            ]
        )
        result = parse_events(events)
        self.assertTrue(result["ok"])
        self.assertEqual(result["response"], "OK")
        self.assertEqual(result["usage"]["input_tokens"], 123)

    def test_missing_or_invalid_usage_never_fabricated(self):
        for text in (
            '{"type":"turn.completed"}',
            '{"type":"turn.completed","usage":{"input_tokens":true,"output_tokens":1}}',
            "garbage\n[]\nnull",
        ):
            self.assertIsNone(parse_events(text)["usage"])

    def test_multiple_turns_aggregate(self):
        event = (
            '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":2}}'
        )
        self.assertEqual(
            parse_events(event + "\n" + event)["usage"]["input_tokens"], 20
        )

    def test_failed_turn(self):
        self.assertFalse(
            parse_events('{"type":"turn.failed","error":{"message":"failed"}}')["ok"]
        )

    def test_missing_executable(self):
        with self.assertRaises(AicoError):
            CodexProvider("aico-no-such-executable").execute("task", str(self.root))

    def test_invocation_keeps_prompt_out_of_arguments(self):
        class Result:
            returncode = 0

        def run(cmd, **kwargs):
            self.assertEqual(cmd[-1], "-")
            self.assertNotIn("private prompt", " ".join(cmd))
            self.assertIn("read-only", cmd)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", cmd)
            kwargs["stdout"].write(
                b'{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}\n'
            )
            return Result()

        with (
            patch("aico.providers.shutil.which", return_value="codex"),
            patch("aico.providers.subprocess.run", side_effect=run),
        ):
            self.assertTrue(
                CodexProvider().execute("private prompt", str(self.root))["ok"]
            )


class CLITests(TempCase):
    def call(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["--home", str(self.root / "home"), *args])
        return (
            code,
            json.loads(stdout.getvalue()) if stdout.getvalue() else None,
            stderr.getvalue(),
        )

    def test_end_to_end_review_export_explain(self):
        source = self.source("# Rules\n- Always test changes\n")
        code, rows, _ = self.call("import", str(source))
        self.assertEqual(code, 0)
        rid = rows[0]["id"]
        self.assertEqual(self.call("explain", "work")[1]["selected_ids"], [])
        self.call("rules", "review", rid, "approved")
        self.assertEqual(self.call("explain", "work")[1]["selected_ids"], [rid])
        self.assertEqual(self.call("export", "--out", str(self.root / "bundle"))[0], 0)
        self.assertIn("Always test", (self.root / "bundle/AGENTS.md").read_text())
        self.call("rules", "edit", rid, "--text", "Changed")
        self.assertEqual(self.call("rules", "list")[1][0]["status"], "pending")
        self.assertEqual(len(self.call("rules", "history", rid)[1]), 3)

    def test_run_and_enhance_preview_never_call_provider(self):
        with patch(
            "aico.cli.CodexProvider.execute", side_effect=AssertionError("network call")
        ):
            self.assertFalse(self.call("run", "task")[1]["sent"])
            path = self.source("- Keep local")
            self.assertFalse(self.call("enhance", str(path))[1]["sent"])

    def test_enhancement_requires_new_review(self):
        result = {
            "ok": True,
            "response": '{"rules":["Do tests"]}',
            "usage": {"input_tokens": 8},
        }
        with patch("aico.cli.CodexProvider.execute", return_value=result):
            code, data, _ = self.call(
                "enhance", str(self.source("- Proposal")), "--send"
            )
        self.assertEqual(code, 0)
        self.assertEqual(data["rules"][0]["status"], "pending")

    def test_failed_run_exit_status(self):
        with patch(
            "aico.cli.CodexProvider.execute",
            return_value={"ok": False, "response": "", "usage": None},
        ):
            self.assertEqual(self.call("run", "task", "--send")[0], 1)

    def test_usage_errors(self):
        self.assertEqual(self.call("import", str(self.root / "missing.txt"))[0], 2)
        self.assertEqual(self.call("rules", "add", "", "--kind", "global")[0], 2)
        self.assertEqual(self.call("run", "t", "--timeout", "0")[0], 2)

    def test_native_cli_roundtrip(self):
        code, preview, _ = self.call(
            "native",
            "plan",
            "--agents-file",
            str(self.root / "project/AGENTS.md"),
            "--skills-dir",
            str(self.root / "project/.agents/skills"),
            "--out",
            str(self.root / "plan.json"),
        )
        self.assertEqual(code, 0)
        result = self.call(
            "native",
            "apply",
            str(self.root / "plan.json"),
            "--confirm",
            preview["confirm"],
        )[1]
        self.assertEqual(self.call("native", "rollback", result["install_id"])[0], 0)
        self.assertFalse((self.root / "project/AGENTS.md").exists())


class BenchmarkTests(unittest.TestCase):
    def test_offline_does_not_invent_tokens(self):
        report = benchmark()
        self.assertFalse(report["live"])
        self.assertEqual(report["summary"]["full"]["input_tokens"], None)
        self.assertTrue(all(r["usage"] is None for r in report["records"]))
        self.assertGreater(
            report["records"][0]["context_bytes"], report["records"][1]["context_bytes"]
        )

    def test_live_aggregation_and_quality(self):
        class Fake:
            def execute(self, prompt, project, model, timeout):
                return {
                    "ok": True,
                    "response": '{"command":"pytest -q"}',
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 5,
                        "cached_input_tokens": 0,
                    },
                }

        report = benchmark(Fake(), repeats=2)
        self.assertEqual(report["summary"]["full"]["input_tokens"], 600)
        self.assertEqual(report["summary"]["full"]["passed"], 2)
        self.assertEqual(report["records"][6]["mode"], "routed")

    def test_invalid_repeats(self):
        with self.assertRaises(AicoError):
            benchmark(repeats=0)


if __name__ == "__main__":
    unittest.main()
