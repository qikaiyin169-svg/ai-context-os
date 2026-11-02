"""Reproducible offline workflow. All writes stay in a temporary directory."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def call(home, *args):
    result = subprocess.run(
        [sys.executable, "-m", "aico", "--home", str(home), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(
        dir=os.path.realpath(tempfile.gettempdir())
    ) as tmp:
        root = Path(tmp)
        home = root / "private"
        rows = call(home, "import", str(Path(__file__).with_name("rules.md")))
        for row in rows:
            call(home, "rules", "review", row["id"], "approved")
        report = call(home, "explain", "review the API")
        preview = call(
            home,
            "native",
            "plan",
            "--agents-file",
            str(root / "project/AGENTS.md"),
            "--skills-dir",
            str(root / "project/.agents/skills"),
            "--out",
            str(root / "plan.json"),
        )
        install = call(
            home,
            "native",
            "apply",
            str(root / "plan.json"),
            "--confirm",
            preview["confirm"],
        )
        call(home, "native", "rollback", install["install_id"])
        assert not (root / "project/AGENTS.md").exists()
        print(
            json.dumps(
                {
                    "approved_rules": len(rows),
                    "selected_ids": report["selected_ids"],
                    "installation_and_rollback": "passed",
                    "model_calls": 0,
                },
                indent=2,
            )
        )
