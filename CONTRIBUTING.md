# Contributing / 参与贡献

Use small, reviewable changes with a concrete behavior and validation. Discuss large changes in an issue first. Be respectful, focus on evidence, and do not include private data in issues or pull requests.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m unittest discover -s tests -v
ruff check src tests scripts examples
python scripts/release_check.py
python examples/demo.py
python -m build --no-isolation
```

Tests must run offline without Codex or credentials. Cover boundaries rather than echoing implementation: review state, scope leaks, budgets, real versus missing usage, non-destructive installation, changed targets and rollback. Live evaluation is opt-in, never part of public PR CI. Do not add tests that call live providers implicitly.

New dependencies need a reason, license review and vulnerability review. Keep the offline core usable without model/API packages. Do not vendor third-party source without its notices. Original contributions are submitted under the project's MIT license; confirm you have rights to contribute them.

中文：提交前运行离线测试、格式检查和发布检查。不得提交个人文档、密钥、真实用户规则库或运行日志。新增依赖需说明用途并核对许可。线上模型测试必须显式授权；公开 PR 的 CI 不依赖账号凭据。贡献代码按本项目 MIT 许可证提供。
