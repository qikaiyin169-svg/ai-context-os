"""SQLite registry: every mutation appends a recoverable immutable revision."""

import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from .util import AicoError, no_links, private_dir

STATES = ("pending", "approved", "rejected", "disabled")
KINDS = ("global", "project", "skill")


def validate(rule):
    if rule.get("kind") not in KINDS or rule.get("status") not in STATES:
        raise AicoError("Invalid kind or review status")
    if (
        not isinstance(rule.get("text"), str)
        or not 1 <= len(rule["text"].strip()) <= 8000
    ):
        raise AicoError("Rule text must have 1..8000 characters")
    if rule["kind"] == "project" and not rule.get("project"):
        raise AicoError("Project rules require --project")
    if rule["kind"] == "skill" and not re.fullmatch(
        r"[a-z][a-z0-9-]{0,63}", rule.get("name", "")
    ):
        raise AicoError("Skill name must be a safe lowercase slug (max 64)")
    if rule["kind"] == "skill" and not rule.get("triggers"):
        raise AicoError("Skills require one or more explicit triggers")
    for field in ("triggers", "tags"):
        value = rule.get(field, [])
        if (
            not isinstance(value, list)
            or len(value) > 32
            or any(not isinstance(t, str) or not 1 <= len(t) <= 100 for t in value)
        ):
            raise AicoError(field + " must be a list of 1..100 character strings")
    for field in ("key", "value", "name", "description"):
        if not isinstance(rule.get(field, ""), str) or len(rule.get(field, "")) > 500:
            raise AicoError("Invalid field: " + field)


class Store:
    def __init__(self, home):
        self.home = private_dir(home)
        self.path = no_links(self.home / "registry.sqlite3")
        self.db = sqlite3.connect(self.path)
        if self.db.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
            self.db.close()
            raise AicoError("Unsupported registry schema version")
        os.chmod(self.path, 0o600)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS rules (id TEXT PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS revisions (
          rule_id TEXT NOT NULL REFERENCES rules(id), version INTEGER NOT NULL,
          data TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(rule_id, version));
        PRAGMA user_version=1;
        """)

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            yield

    def _save(self, rule):
        validate(rule)
        data = json.dumps(rule, ensure_ascii=False, sort_keys=True)
        self.db.execute(
            "INSERT INTO rules VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
            (rule["id"], data),
        )
        self.db.execute(
            "INSERT INTO revisions(rule_id,version,data) VALUES (?,?,?)",
            (rule["id"], rule["version"], data),
        )
        return rule

    def add_many(self, candidates, kind="global", project="", **metadata):
        result = []
        with self.transaction():
            for candidate in candidates:
                rule = dict(
                    id=uuid.uuid4().hex[:12],
                    version=1,
                    kind=kind,
                    status="pending",
                    project=str(Path(project).resolve()) if project else "",
                    name="",
                    description="",
                    triggers=[],
                    tags=[],
                    key="",
                    value="",
                    source={},
                )
                rule.update(metadata)
                rule.update(candidate)
                # Importers may supply text/source only, never approval/identity.
                rule["status"] = "pending"
                rule["version"] = 1
                result.append(self._save(rule))
        return result

    def list(self, status=None):
        rows = [
            json.loads(r[0])
            for r in self.db.execute("SELECT data FROM rules ORDER BY id")
        ]
        return [r for r in rows if status is None or r["status"] == status]

    def get(self, rule_id):
        row = self.db.execute(
            "SELECT data FROM rules WHERE id=?", (rule_id,)
        ).fetchone()
        if row is None:
            raise AicoError("Unknown rule: " + rule_id)
        return json.loads(row[0])

    def update(self, rule_id, **changes):
        allowed = {
            "text",
            "status",
            "tags",
            "triggers",
            "key",
            "value",
            "description",
            "name",
        }
        if not set(changes) <= allowed:
            raise AicoError("Unsupported rule update")
        with self.transaction():
            rule = self.get(rule_id)
            rule.update(changes)
            rule["version"] += 1
            return self._save(rule)

    def history(self, rule_id):
        self.get(rule_id)
        return [
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT data FROM revisions WHERE rule_id=? ORDER BY version",
                (rule_id,),
            )
        ]

    def restore(self, rule_id, version):
        with self.transaction():
            current = self.get(rule_id)
            row = self.db.execute(
                "SELECT data FROM revisions WHERE rule_id=? AND version=?",
                (rule_id, version),
            ).fetchone()
            if row is None:
                raise AicoError("Unknown revision")
            rule = json.loads(row[0])
            rule["version"] = current["version"] + 1
            return self._save(rule)
