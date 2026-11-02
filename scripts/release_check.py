"""Conservative source-manifest/privacy checks; not a full secret-detection audit."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {
    ".git",
    "__pycache__",
    ".venv",
    "build",
    "dist",
    ".aico",
    ".ruff_cache",
    ".coverage",
    "coverage.xml",
}
REQUIRED = [
    "LICENSE",
    "README.md",
    "README.zh-CN.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/INSTALL.md",
    "docs/USAGE.md",
    "docs/ARCHITECTURE.md",
    "docs/BENCHMARK.md",
    "docs/VALIDATION.md",
    ".github/workflows/ci.yml",
]
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{30,})\b"
    ),
    "local account path": re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/"),
    "private experience filename": re.compile("AI使用经验\\.docx"),
}


def main():
    failures, count = [], 0
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            failures.append("Missing required file: " + name)
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(p in SKIP or p.endswith(".egg-info") for p in rel.parts):
            continue
        if path.is_symlink():
            failures.append("Symlink in source: " + str(rel))
            continue
        if not path.is_file():
            continue
        count += 1
        if path.suffix.lower() in {
            ".docx",
            ".sqlite",
            ".sqlite3",
            ".pem",
            ".key",
        } or path.name.startswith(".env"):
            failures.append("Private/binary source type: " + str(rel))
            continue
        if path.stat().st_size > 1_000_000:
            failures.append("Unexpected large source file: " + str(rel))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            failures.append("Unexpected binary source: " + str(rel))
            continue
        # Documentation can name the excluded private filename, without including it.
        for label, pattern in PATTERNS.items():
            if label == "private experience filename" and path.suffix == ".md":
                continue
            if pattern.search(text):
                failures.append(label + ": " + str(rel))
        if path.suffix == ".md":
            for link in re.findall(r"\]\(([^\s)]+)\)", text):
                if "://" in link or link.startswith("#"):
                    continue
                target = path.parent / link.split("#")[0]
                if not target.exists():
                    failures.append("Broken local link: " + str(rel) + " -> " + link)
    report = {
        "passed": not failures,
        "source_files_checked": count,
        "failures": failures,
        "limitation": "Pattern and manifest checks do not prove absence of every secret or private fact.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
