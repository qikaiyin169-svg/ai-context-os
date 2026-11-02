# Release validation · v0.1.0

Date: 2026-11-02 (Asia/Shanghai). Local validation used macOS arm64 and Python 3.12.14; Codex CLI 0.166.0-alpha.5.1.

| Check | Observed result |
| --- | --- |
| Offline unit/integration suite | 55 tests passed |
| Statement coverage | 95% (671/706 statements at this checkpoint) |
| Static lint | Passed, Ruff 0.17.3 |
| Offline demo | Import → approve → explain → install → exact rollback passed |
| Package build | Source distribution and universal Python wheel built |
| Isolated wheel install | No-index, no-dependency install passed; final wheel suite and demo verified in a clean environment |
| Runtime requirements | Empty; wheel metadata MIT, Python >=3.11 |
| Development vulnerability audit | 36 packages, no known vulnerabilities reported by pip-audit 2.10.1 at this date |
| Third-party licenses | Distribution metadata inventoried; no vendored implementation |
| Source privacy/manifest checks | Passed; no private DOCX, database, credential, local account path or unexpected binary in source |
| Live model evaluation | Six successful calls; exact JSON 3/3 per arm; actual usage retained in sanitized evidence |

The test suite includes synthetic DOCX fixtures, per-rule review, project scoping, explicit conflicts, mandatory/optional budgets, missing usage, recovered transport errors, stale installation plans, symlink refusal, unmanaged skill protection, backup corruption and exact rollback. All actual installation tests used temporary targets. Existing user Codex files were not installed over or changed.

The first model attempt timed out; it is not treated as a zero-token success. The final benchmark reports 59,634 versus 52,828 input tokens in one repeat, with different caching and one pair increasing after routing. It does not establish general savings, coding success or costs. See [method](BENCHMARK.md), [synthetic live evidence](benchmark-live.json) and [audit summary](development-audit.json).

GitHub CI completed successfully before publication: [run 41433886408](https://github.com/qikaiyin169-svg/ai-context-os/actions/runs/41433886408) validated code commit `4cc3525e733e31d06777a125b8d67ff181eae440`. All 10 jobs passed: nine combinations of Linux/macOS/Windows and Python 3.11/3.12/3.14, plus lint/coverage/build/dependency audit. Windows appropriately skips the two POSIX-specific permission/symlink checks. Subsequent release-record edits change documentation only. Publication history uses GitHub noreply author/committer addresses.

Known design limits: explicit-only conflict detection, keyword skill routing, byte rather than token budgets, inherited Codex context, no write-enabled Enhanced Mode, version-dependent transport hints, no automatic obsolete-skill removal and no crash-atomic multi-file installation. See the architecture, usage and security documents.
