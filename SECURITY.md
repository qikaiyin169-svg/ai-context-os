# Security and privacy

## Data flow

- Basic parsing, registry operations, review, routing, export and installation are local and do not call a model.
- There is no telemetry or update check. Package installation/build tools may contact your configured package index.
- Imported source bytes are not copied. Extracted rule text and filename/hash/position are stored; these can still contain personal information.
- `enhance`, `run` and live `benchmark` invoke Codex only with `--send`. The AICO payload is previewable. Your Codex configuration can add context/tools and determines destination, authentication and charges.
- The package never opens or exports Codex authentication files. Do not commit local databases, plans, run logs, backups, private documents or secrets.

Registry directories are created with POSIX mode 0700 and private data files 0600 where supported. Existing directory permissions and Windows ACLs remain the user's responsibility. SQLite data is not encrypted. Backups and run records have no automatic retention/deletion policy. Use OS disk encryption and private locations when needed.

## Trust boundaries

Imported documents and AI proposals are untrusted candidates. Approval is per rule; edits require fresh review. Restore can restore a historical approved state. Review instructions for prompt injection and unwanted disclosure before approval. Prompts are not a security boundary; read-only Codex execution is not network isolation, and configured integrations may have additional permissions.

The parser accepts UTF-8 text and bounded main-document XML from DOCX without extracting ZIP paths. It rejects DTD/entity/UTF-16 XML. It does not execute macros or embedded files. Parsing is deliberately incomplete, including no OCR or tracked-change interpretation.

Installer paths are explicit, symlink targets/ancestors are refused, existing unmanaged skills are refused, and AGENTS text is merged in a reserved block. Plans are hash-confirmed; targets and backups are hash-checked. Write failures are compensated; power loss and malicious same-user filesystem races are outside the transaction guarantee. Do not install into attacker-controlled directories. Local registry/plan/backup tampering by the same OS account is outside the threat model.

## Reporting

Before public release, report issues privately to the repository owner through an available private contact channel. After release, use GitHub private vulnerability reporting if enabled. Do not post secrets, personal documents or sensitive logs in public issues. Include version, OS, minimal synthetic reproduction and expected/observed behavior. No response-time or audit certification is claimed.
