# Architecture and v0.1 boundaries

The product is a local personal context registry with two Codex delivery paths. SQLite is the single source of truth; generated files are reviewed delivery artifacts. No daemon, remote database, telemetry, automatic memory capture or credential store is included.

| Module | Responsibility |
| --- | --- |
| `parser.py` | Bounded DOCX/Markdown/TXT structure extraction with source filename/hash/position |
| `store.py` | Pending/approved/rejected/disabled rules and append-only revisions in SQLite |
| `router.py` | Project matching, exact-text deduplication, explicit conflicts, substring skill triggers, UTF-8 byte budgets |
| `native.py` | Managed AGENTS blocks, safe skill front matter, diffs, hash confirmation, backups and guarded rollback |
| `providers.py` | Provider protocol and authenticated Codex CLI subprocess adapter |
| `benchmark.py` | Paired full/routed synthetic instruction-adherence measurements |
| `cli.py` | User review, local workflows and explicit sending boundaries |

A rule contains an ID, version, kind, status, text, project path, name/description, triggers/tags, optional conflict key/value and source provenance. Source provenance is descriptive evidence, never execution permission. Skills are instruction-only; the generator does not copy scripts or binaries from documents.

The registry stores latest JSON plus immutable revisions. Mutations use SQLite transactions and a reserved write lock. Unknown future schema versions are refused; v0.1 does not migrate them. Version restoration appends a new revision. Concurrent imports get independent IDs. Identical imports are not deduplicated in storage so provenance remains inspectable; delivery deduplicates normalized text.

Task routing cannot alter Codex's own instruction hierarchy or higher-priority rules. Native Mode lets Codex select local skills itself. Enhanced Mode assembles a user prompt and can duplicate previously installed native guidance. `aico explain` describes AICO's decisions only. No desktop-specific plugin or UI integration is required or claimed.

The Provider protocol accepts `(prompt, project, model, timeout)` and returns `ok`, `response`, `usage` or `None`, `elapsed_seconds` and errors. New adapters must preserve preview/consent boundaries, never auto-approve proposals, and report provider usage without substitution by byte estimates. No HTTP API adapter is shipped in v0.1.

V0.1 intentionally defers automatic long-term memory, semantic relevance and contradiction detection, third-party compression services, graphical management, universal AI-platform exports, write-enabled Enhanced tasks and production-scale effectiveness claims. These are roadmap items, not implemented features.
