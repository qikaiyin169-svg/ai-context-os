# CLI workflow / 命令指南

All commands support JSON output. `--home PATH` is a global option and goes before the command. Exit codes: `0` successful local operation/provider run; `1` failed model execution or benchmark execution; `2` expected input, parsing, filesystem or routing error. A benchmark's exact-output score is separate from provider execution success.

## Import and review

```sh
aico --home /private/aico init
aico --home /private/aico import experience.docx
aico import notes.txt --include-prose
aico import project.md --kind project --project /work/repo
aico rules list --status pending
aico rules review ID approved
aico rules review ID rejected
aico rules review ID disabled
aico rules edit ID --text "Replacement instruction" --tag testing
aico rules history ID
aico rules restore ID 1
```

Review one rule ID at a time; there is no blanket auto-approval flag. Edit replaces supplied fields and resets status to pending. `--trigger` / `--tag` can repeat; edit replaces each supplied list. Restore appends the old content **and its historical approval state** as a new revision; inspect history before restoring an approved revision. Importing a source again creates fresh pending candidates; routing deduplicates identical approved text.

Default extraction recognizes Markdown/TXT bullets, numbered lists, `RULE:` and `规则:`. DOCX extracts main-document paragraphs including tables and numbered paragraphs. Headings provide provenance sections. Headers, footers, tracked-change semantics, embedded files, OCR and rich list continuation are not implemented. Code fences in Markdown are skipped. Ordinary prose requires `--include-prose`. Files/document XML are bounded at 2 MB; DTD/entities/UTF-16 XML are rejected; ZIP entries are never extracted to disk. Paragraphs longer than 8000 characters are skipped by the basic parser. It is structure extraction, not semantic interpretation.

## Explicit conflicts and scopes

```sh
aico rules add "Respond in English." --key response-language --value en
aico rules add "Respond in Chinese for this repo." --kind project \
  --project /work/repo --key response-language --value zh
aico conflicts --project /work/repo
aico explain "review API" --project /work/repo --max-bytes 16384
```

Only **approved** rules are active. Project identity is the resolved absolute path, not a remote URL or project name. Skills may be global or project-bound via `--project`. Contradictions with explicit matching keys and unequal values are visible. Same-scope contradictions block Enhanced Mode; a unique project value takes precedence over global preferences. Contradictions in unlabelled prose are not detected. For conservatism, conflicts in applicable skills are checked even if the current task does not trigger them. Review these conflicts explicitly.

Global/project instructions are mandatory. Optional skills match explicit substrings; no embedding or language-model routing occurs. Skills that exceed the remaining byte budget are excluded with an explanation. Mandatory overflow blocks sending. There is no model-token estimate masquerading as measured usage.

## Native mode

```sh
aico export --scope global --out /private/bundle
aico native plan --scope project --project /work/repo \
  --agents-file /work/repo/AGENTS.md --skills-dir /work/repo/.agents/skills \
  --out /private/project-plan.json
aico native apply /private/project-plan.json --confirm EXACT_HASH
aico native rollback INSTALL_ID
```

Global export includes only global rules and global skills. Project export includes only matching project rules and project-bound skills. Install global and project layers separately. Native export refuses explicit conflicts across all applicable approved rules, including project/global conflicts that Enhanced Mode can resolve, because Codex controls the actual native hierarchy.

Plans contain exact paths, diffs and new text; keep them private. Apply requires the SHA256 of the complete reviewed plan. Changed targets, symlinks, shadowing `AGENTS.override.md`, malformed managed blocks and unmanaged skills are refused. Existing `AGENTS.md` text is retained, with a single managed block added/updated. File modes are preserved where the OS supports them; backups preserve original bytes. No configuration file is edited.

Backups and manifests live under `AICO_HOME/backups/INSTALL_ID/`. Rollback preflights every target and backup hash before restoring, and refuses files edited since install. Roll back in reverse order. Ordinary write failures during apply restore earlier changed targets; abrupt termination/power loss can leave a prepared manifest and partial installation. Inspect its per-file hashes and backups before manual recovery. Filesystem operations across several files are not crash-atomic. Use directories you control; this is not a defense against a malicious same-user process racing path checks.

Empty directories can remain after rollback. Export/install does not automatically delete old skills after a rule is disabled/renamed. Roll back the previous installation first, then install a fresh reviewed plan. Global/project policy in an existing unmanaged instruction file can still contradict exported rules; AICO does not claim to parse the host's complete instruction hierarchy.

## Enhanced mode and AI extraction

```sh
aico run "Review the API" --project /work/repo  # preview
aico run "Review the API" --project /work/repo --send --timeout 180
aico enhance experience.docx                   # preview
aico enhance experience.docx --send
```

`run` passes the prompt through stdin, not process arguments. It calls `codex exec --json --ephemeral --sandbox read-only`; existing Codex authentication/configuration remain in charge. The default invocation intentionally does not authorize workspace writes. No dangerous bypass flags are used. For a coding task requiring writes, use exported Native Mode with your normal Codex permission workflow.

The preview shows exactly the **AICO-added** prompt. Codex may add system instructions, global/project AGENTS files, skill metadata, MCP tools and hooks. AICO does not intercept or fully explain those additions. Review your Codex configuration before `--send`, especially for private sources. Read-only file permissions do not prohibit network access or third-party tool activity.

Enhancement sends extracted paragraphs (no raw DOCX bytes) from a temporary workspace. Source headings are provenance, not themselves extracted instructions. JSON proposals are bounded, validated and imported as pending. No model result becomes active automatically. General model API adapters are an extension point only.

Run records retain routing text, response, real usage (when present), timing and command locally in `AICO_HOME/runs/`. They may be private. A nonzero exit, `turn.failed` or missing completion is a failed run. A completed run without usage keeps usage `null`. Token totals include native context as reported by Codex, not just AICO text. Cached input is reported separately and is a subset of input, not an extra token total. No money calculation is inferred.

中文：先导入、逐条审核，再导出或运行；修改后重新审核。冲突只支持显式键值，普通自然语言需人工判断。安装必须审阅计划并提供准确哈希；回滚会拒绝安装后发生的用户修改。在线操作显式添加 `--send`，但 Codex 自身仍可能附加原生上下文和工具。新增或更名 Skill 后，先回滚旧安装再重新安装，避免遗留文件。

If the built-in OpenAI provider encounters repeated WebSocket timeouts, try `--http` for this invocation. This passes `-c model_providers.openai.supports_websockets=false` without editing configuration, as documented in the [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference). It does not reconfigure custom providers. This is a version-dependent hint: the tested 0.166 alpha still emitted reconnect warnings before successful HTTP fallback. Increase `--timeout` when necessary; v0.1 does not guarantee transport selection.
