# Third-party components and licenses

The distributed AICO Python package has **zero third-party runtime dependencies** and contains no vendored third-party implementation. It uses Python's standard library (including SQLite and ElementTree). Python and SQLite are provided by the user's Python distribution; their own terms remain applicable. The original project code and examples are MIT licensed.

Build/development tools are installed separately and are not bundled in the wheel:

| Direct tool | Pinned development version | Distribution license |
| --- | --- | --- |
| pip | 26.2.2 | MIT |
| setuptools | 84.2.1 | MIT |
| build | 1.6.1 | MIT |
| wheel | 0.48.0 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| Ruff | 0.17.3 | MIT |
| coverage.py | 7.17.0 | Apache-2.0 |
| pip-audit | 2.10.1 | Apache-2.0 |

A machine-readable inventory of the actual development environment (including transitive dependencies, versions and declared license metadata) is in `docs/development-licenses.json`. It describes the release build environment, not a runtime dependency lock. Transitive tool requirements may resolve differently across Python versions; their distributions retain their own license texts. No tool source is redistributed here. Recheck before changing or bundling dependencies.

GitHub Actions uses `actions/checkout` and `actions/setup-python` (MIT) by pinned commit references. They execute on GitHub-hosted runners and are not included in AICO's wheel. Codex CLI is an external optional program, not bundled or relicensed by this project. OpenAI product names identify integration compatibility; no affiliation is claimed.
