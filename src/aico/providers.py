"""Provider extension boundary. Only Codex CLI is implemented in v0.1."""

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Protocol

from .util import AicoError


class Provider(Protocol):
    def execute(
        self, prompt: str, project: str, model: str = "", timeout: int = 180
    ) -> dict:
        """Return ok, response, usage (real or None), elapsed_seconds, errors."""
        ...


def parse_events(output):
    usage = None
    messages, errors, notices = [], [], []
    completed = False
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "turn.completed":
            completed = True
            raw = event.get("usage")
            if isinstance(raw, dict) and all(
                type(raw.get(k)) is int and raw[k] >= 0
                for k in ("input_tokens", "output_tokens")
            ):
                if usage is None:
                    usage = {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cached_input_tokens": 0,
                    }
                for key in usage:
                    value = raw.get(key)
                    if type(value) is int and value >= 0 and usage[key] is not None:
                        usage[key] += value
                    elif key == "cached_input_tokens":
                        usage[key] = None
        item = event.get("item", {})
        if (
            event.get("type") == "item.completed"
            and isinstance(item, dict)
            and item.get("type") == "agent_message"
        ):
            messages.append(str(item.get("text", "")))
        if event.get("type") == "turn.failed":
            errors.append(event.get("error", "Codex turn failed"))
        elif event.get("type") == "error":
            notices.append(event.get("message", "Codex diagnostic"))
    if not completed:
        errors.extend(notices)
    return {
        "ok": completed and not errors,
        "response": messages[-1] if messages else "",
        "usage": usage,
        "errors": errors,
        "warnings": notices if completed else [],
    }


class CodexProvider:
    def __init__(self, executable="codex", http=False):
        self.executable = executable
        self.http = http

    def execute(self, prompt, project, model="", timeout=180):
        executable = shutil.which(self.executable)
        if not executable:
            raise AicoError("Codex CLI not found; install/authenticate it first")
        project = str(Path(project).resolve(strict=True))
        command = [
            executable,
            "exec",
            "--json",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "-C",
            project,
        ]
        if self.http:
            command.extend(["-c", "model_providers.openai.supports_websockets=false"])
        if model:
            command.extend(["--model", model])
        command.append("-")
        start = time.monotonic()
        # Spool to disk rather than retaining unbounded tool output in memory.
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            try:
                process = subprocess.run(
                    command,
                    input=prompt.encode(),
                    stdout=stdout,
                    stderr=stderr,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return {
                    "ok": False,
                    "response": "",
                    "usage": None,
                    "errors": ["Codex timed out; no successful run recorded"],
                    "elapsed_seconds": round(time.monotonic() - start, 3),
                    "provider": "codex-cli",
                    "requested_model": model or "configured default",
                    "exit_code": None,
                }
            if stdout.tell() > 8_000_000:
                raise AicoError("Codex event output exceeded 8 MB")
            stdout.seek(0)
            result = parse_events(stdout.read().decode("utf-8", errors="replace"))
            stderr.seek(0)
            diagnostic = stderr.read(4000).decode("utf-8", errors="replace")
        result.update(
            elapsed_seconds=round(time.monotonic() - start, 3),
            exit_code=process.returncode,
            provider="codex-cli",
            requested_model=model or "configured default",
            command=command,
        )
        result["ok"] = result["ok"] and process.returncode == 0
        if not result["ok"]:
            result["diagnostic"] = diagnostic
        return result
