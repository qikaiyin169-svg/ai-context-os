"""Deterministic routing with explicit limits and inspectable decisions."""

import re
from pathlib import Path

from .util import AicoError, digest


def normalized(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def applicable(rule, project):
    return not rule["project"] or rule["project"] == str(Path(project).resolve())


def conflicts(rules):
    groups = {}
    for rule in rules:
        if rule.get("key"):
            groups.setdefault(rule["key"], []).append(rule)
    result = []
    for key, group in sorted(groups.items()):
        if len({r["value"] for r in group}) > 1:
            highest = max(1 if r["project"] else 0 for r in group)
            top = [r for r in group if bool(r["project"]) == bool(highest)]
            resolved = len({r["value"] for r in top}) == 1
            result.append(
                {
                    "key": key,
                    "ids": [r["id"] for r in group],
                    "resolution": "project precedence"
                    if resolved
                    else "review required",
                    "winners": [r["id"] for r in top] if resolved else [],
                }
            )
    return result


def render_rule(rule):
    return (
        "\n## "
        + (rule["name"] or rule["kind"])
        + " ["
        + rule["id"]
        + "]\n"
        + rule["text"].strip()
        + "\n"
    )


def route(rules, task, project, max_bytes=16384, full=False):
    if max_bytes < 0:
        raise AicoError("max-bytes must be non-negative")
    eligible = [
        r for r in rules if r["status"] == "approved" and applicable(r, project)
    ]
    collisions = conflicts(eligible)
    excluded = {}
    for conflict in collisions:
        for rid in conflict["ids"]:
            if rid not in conflict["winners"]:
                excluded[rid] = "conflict: " + conflict["key"]
    selected, decisions, seen = [], [], set()
    used = 0
    ordered = sorted(
        rules, key=lambda r: (r["kind"] == "skill", not bool(r["project"]), r["id"])
    )
    for rule in ordered:
        rid = rule["id"]
        reason = ""
        if rule["status"] != "approved":
            reason = "not approved"
        elif not applicable(rule, project):
            reason = "different project"
        elif rid in excluded:
            reason = excluded[rid]
        elif normalized(rule["text"]) in seen:
            reason = "duplicate text"
        elif (
            rule["kind"] == "skill"
            and not full
            and not any(t.casefold() in task.casefold() for t in rule["triggers"])
        ):
            reason = "no explicit trigger match"
        size = len(render_rule(rule).encode("utf-8"))
        if not reason and rule["kind"] == "skill" and used + size > max_bytes:
            reason = "optional skill exceeds byte budget"
        if reason:
            decisions.append({"id": rid, "selected": False, "reason": reason})
            continue
        selected.append(rule)
        seen.add(normalized(rule["text"]))
        used += size
        decisions.append(
            {
                "id": rid,
                "selected": True,
                "reason": "explicit skill trigger/full baseline"
                if rule["kind"] == "skill"
                else "mandatory approved rule",
            }
        )
    blocked = any(c["resolution"] == "review required" for c in collisions)
    if used > max_bytes:
        blocked = True
    context = "".join(render_rule(r) for r in selected)
    return {
        "selected_ids": [r["id"] for r in selected],
        "decisions": decisions,
        "conflicts": collisions,
        "blocked": blocked,
        "context": context,
        "context_bytes": used,
        "max_bytes": max_bytes,
        "budget_error": "Mandatory rules exceed budget; increase --max-bytes"
        if used > max_bytes
        else None,
        "context_sha256": digest(context.encode()),
        "measurement": "UTF-8 bytes; not model tokens",
    }


def prompt_for(task, report):
    if report["blocked"]:
        raise AicoError(
            "Routing blocked: review conflicts or increase byte budget; use aico explain"
        )
    return (
        "Apply the following user-reviewed AICO context within the host's instruction hierarchy.\n"
        "<aico-context>\n" + report["context"] + "</aico-context>\n\nTask:\n" + task
    )
