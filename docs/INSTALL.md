# Installation / 安装

Requires Python 3.11 or newer. macOS, Linux and Windows are CI targets; see release evidence for platforms actually exercised. Offline registry features need no Codex installation.

From a reviewed source checkout (or unpacked source archive):

```sh
python -m venv .venv
# macOS/Linux:
. .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
python -m pip install .
aico --version
```

For the release wheel, use `python -m pip install /path/to/ai_context_os-0.1.0-py3-none-any.whl`. The wheel contains no runtime dependencies. Source builds need setuptools (MIT); pip may fetch build dependencies from its configured package index. In a prepared build environment, `python -m pip install --no-build-isolation .` avoids that fetch. No PyPI publication is implied by a GitHub release.

For Enhanced Mode, install and authenticate Codex CLI following the [official CLI documentation](https://developers.openai.com/codex/cli). Ensure `codex` is on PATH. `codex login status` checks authentication. Tested CLI versions are recorded in release evidence. The adapter requires `exec`, `--json`, `--ephemeral`, `--sandbox read-only`, `--skip-git-repo-check`, `-C`, and stdin prompts. An incompatible CLI fails without inventing usage.

Do not import private experience files into the project checkout. Put `AICO_HOME`, generated plans, bundles, benchmarks and run records in a private directory outside Git. Source names and extracted text can themselves be private. AICO's default registry is outside the checkout; use a private separate `--home` for experiments.

Uninstall the package with `python -m pip uninstall ai-context-os`. This leaves private registry/history/backups intact. Before removing local data, roll back installed native files in reverse installation order. No uninstaller deletes personal data automatically. To relocate a project, retain a backup and re-import/review its project-scoped rules using the new absolute path.

中文：先创建独立 Python 环境并安装本项目；本地功能无需模型。启用 `--send` 前，需安装并登录 Codex CLI。请将规则库、备份和评测结果放在公开源码目录之外。卸载软件不会自动删除个人规则，也不会自动撤销原生安装，应先按安装顺序倒序回滚。
