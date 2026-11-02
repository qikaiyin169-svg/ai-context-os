# AI Context OS · v0.1

**Local-first, reviewable rules and task context for Codex.** Import your experience, approve explicit instructions, inspect routing, and export native guidance or run a task through Codex CLI.

[中文](README.zh-CN.md) · [Install](docs/INSTALL.md) · [CLI guide](docs/USAGE.md) · [Design](docs/ARCHITECTURE.md) · [Security](SECURITY.md) · [Contribute](CONTRIBUTING.md)

V0.1 is a developer-tool alpha. The long-term direction is portable personal AI rules, memory and context infrastructure. It does **not** implement automatic memory collection, a GUI, universal model API support, or semantic conflict detection.

## Quick start

Python 3.11+; no third-party runtime dependencies. From a checkout:

```sh
python -m venv .venv
# macOS/Linux
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install .
aico --version
aico init
aico import examples/rules.md
# Inspect each returned candidate, then approve its actual ID:
aico rules list --status pending
aico rules review RULE_ID approved
aico explain "review the API"
aico run "review the API"   # prints the payload; no model call
```

Add an on-demand skill (pending until reviewed):

```sh
aico rules add "Check API compatibility and add regression tests." \
  --kind skill --name api-review --trigger api \
  --description "Use when reviewing an API change."
aico rules review SKILL_ID approved
```

Every rule is local in `~/.aico/registry.sqlite3` (`AICO_HOME` or `--home` overrides). Source bytes are not copied, but extracted text, filename, hash and position are retained locally. Review before approving. `--home` precedes the subcommand. CLI output is JSON; expected errors go to stderr.

## Two modes, one registry

| Mode | Entry | Behavior |
| --- | --- | --- |
| Native | `aico native plan` → review → `native apply` | Adds a managed block to `AGENTS.md` and generates instruction-only `SKILL.md` files. Codex discovers them itself. |
| Enhanced | `aico explain TASK` / `aico run TASK --send` | Routes reviewed rules and keyword-triggered skills into an additional prompt; reads real usage from Codex JSONL. |

Global and project rules are mandatory for their matching project. Skills have explicit case-insensitive substring triggers. Duplicate text is removed; project precedence resolves explicit cross-scope key/value contradictions; unresolved contradictions block Enhanced Mode. Byte budgets never silently drop mandatory rules. `explain` shows exclusions, decisions and exact AICO context. It cannot inventory Codex's separately loaded native context.

Native mode uses [Codex's AGENTS.md hierarchy](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [local Skills locations](https://learn.chatgpt.com/docs/build-skills). Global rules target `${CODEX_HOME:-$HOME/.codex}/AGENTS.md`, global skills `$HOME/.agents/skills`; project files target `PROJECT/AGENTS.md` and `PROJECT/.agents/skills`. Paths are explicit. Desktop compatibility means these native files, not control of the desktop UI or its internal token accounting.

```sh
aico native plan --scope global \
  --agents-file "${CODEX_HOME:-$HOME/.codex}/AGENTS.md" \
  --skills-dir "$HOME/.agents/skills" --out /path/to/private/plan.json
# Read all diffs in the output/plan, then use the exact hash shown:
aico native apply /path/to/private/plan.json --confirm PLAN_SHA256
# The apply output supplies INSTALL_ID; rollback refuses subsequent user edits:
aico native rollback INSTALL_ID
```

`config.toml` is never edited. Existing text is preserved; unmanaged skills are refused. Every apply backs up existing bytes and records hashes. Native and Enhanced modes can coexist, but installed native guidance may duplicate the routed prompt. See [usage](docs/USAGE.md) for scope and removal limitations.

## Optional AI and measured evaluation

Local import, review, storage, history, conflict inspection and export work offline. Optional enhancement uses your already authenticated Codex CLI:

```sh
aico enhance examples/rules.md          # preview extracted-text payload
aico enhance examples/rules.md --send   # sends it; returned proposals stay pending
aico run "review this API" --project /path/to/repo --send
aico benchmark --out /path/to/private/offline.json
aico benchmark --send --repeats 2 --model YOUR_MODEL --out /path/to/private/live.json
```

`--send` is the authorization boundary. Codex can add native rules, skills, tools and provider configuration beyond the AICO payload. Read-only execution does not make those integrations private or isolate them. Usage, privacy and charges follow your Codex provider/account. The package never reads, copies or exports authentication files. General model providers can implement the [Provider protocol](src/aico/providers.py); v0.1 ships only Codex CLI.

The benchmark compares full AICO context and routed AICO context on three synthetic JSON instruction-adherence tasks. Offline mode reports bytes, with token/quality values `null`. Live mode reports actual `turn.completed.usage` and exact-JSON checks. It is **not** a general coding-success or cost-saving claim. See [benchmark method and evidence](docs/BENCHMARK.md).

## Development and license

```sh
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m unittest discover -s tests -v
ruff check src tests scripts
python scripts/release_check.py
python -m build --no-isolation
```

MIT licensed; see [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md). Only synthetic examples belong in this repository. Never commit personal experience documents, local registries, plans, backups, run logs or credentials. This project is independent and is not an official OpenAI product.
