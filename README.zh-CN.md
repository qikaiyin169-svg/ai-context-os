# AI Context OS · v0.1

**本地优先、可审核、可解释的 Codex 规则与上下文管理工具。** 将个人经验提取为候选规则，人工批准后按任务组装，或导出 Codex 原生规则文件。

[English](README.md) · [安装](docs/INSTALL.md) · [命令指南](docs/USAGE.md) · [架构](docs/ARCHITECTURE.md) · [安全](SECURITY.md) · [贡献](CONTRIBUTING.md)

V0.1 是面向开发者的 Alpha。长期方向是跨平台个人 AI 规则、记忆和上下文基础设施。本版没有自动记忆采集、图形界面、通用模型 API 实现或语义冲突检测，不承诺未经实测的 Token 节省比例。

## 快速开始

Python 3.11+，无第三方运行依赖。在源码目录执行：

```sh
python -m venv .venv
# macOS/Linux
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install .
aico init
aico import examples/rules.md
aico rules list --status pending
# 阅读候选内容，把 RULE_ID 换成实际 ID：
aico rules review RULE_ID approved
aico explain "review the API"
aico run "review the API"  # 仅预览，不调用模型
```

DOCX、Markdown、UTF-8 TXT 基础解析不需要模型。默认提取显式列表和 `RULE:` / `规则:`；`--include-prose` 可将普通段落也作为候选。程序不承诺理解自然语言的隐含含义。导入内容均为 `pending`，编辑后重新审核。

规则默认存于 `~/.aico/registry.sqlite3`，支持 `AICO_HOME` 或放在子命令之前的 `--home`。不复制原文件，但保留提取的规则文本、源文件名、哈希和位置，因此本地数据库仍可能含隐私。每次修改保留版本，恢复旧版本会新增历史记录。

## 三层规则与双模式

| 层级/模式 | 行为 |
| --- | --- |
| Global Rules | 所有项目的已批准必选规则 |
| Project Rules | 与明确项目绝对路径匹配的已批准必选规则 |
| Skills | 用户提供触发词，增强模式按不区分大小写的子串匹配选择 |
| Native Mode | 生成/安装 `AGENTS.md` 和 `.agents/skills/*/SKILL.md`，由 Codex 原生加载 |
| Enhanced Mode | `aico run` 组装额外上下文并调用 Codex CLI，记录真实可获得的用量 |

```sh
aico rules add "检查 API 兼容性并补回归测试。" --kind skill \
  --name api-review --trigger api --description "用于 API 变更审查。"
aico rules review SKILL_ID approved
aico rules add "使用 pytest 运行测试。" --kind project --project /path/to/repo
```

`aico explain` 展示已选规则、未选原因、显式冲突和实际附加上下文。冲突依据人工标注的 `--key` / `--value`；相同作用域冲突阻止运行，项目约束优先于全局偏好并记录原因。没有标注的自然语言矛盾需人工审核。预算使用 UTF-8 字节，不冒充模型 Token；必选规则超预算时停止，按需 Skills 可以被省略。

## 预览、备份与回滚

原生模式兼容 [Codex 官方 AGENTS.md 机制](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 和 [Skills 位置](https://learn.chatgpt.com/docs/build-skills)。桌面端兼容指这些原生文件，不表示能拦截桌面端每轮上下文或统计其内部 Token。

```sh
aico native plan --scope global \
  --agents-file "${CODEX_HOME:-$HOME/.codex}/AGENTS.md" \
  --skills-dir "$HOME/.agents/skills" --out /path/to/private/plan.json
# 逐项阅读 diff，使用输出中的准确哈希：
aico native apply /path/to/private/plan.json --confirm PLAN_SHA256
# 使用安装结果返回的 ID：
aico native rollback INSTALL_ID
```

项目安装使用 `--scope project --project /path/to/repo`，目标路径设为该项目的 `AGENTS.md` 和 `.agents/skills`。全局导出只含全局规则/Skills，项目导出只含绑定该项目的规则/Skills。已有正文保留，未受本工具管理的同名 Skill 拒绝覆盖。计划过期或安装后用户修改文件时，程序拒绝覆盖或回滚。不会改动 `config.toml`。历史安装的过时 Skill 不会自动删除；见命令指南。

## 可选 AI 增强与真实评测

```sh
aico enhance examples/rules.md          # 先看要发送的段落
aico enhance examples/rules.md --send   # 使用已认证 Codex CLI，生成待审核建议
aico run "review the API" --project /path/to/repo --send
aico benchmark --out /path/to/private/offline.json
aico benchmark --send --repeats 2 --model YOUR_MODEL --out /path/to/private/live.json
```

只有显式 `--send` 才调用模型。Codex 自身配置可能加载额外规则、Skills 和工具；AICO 的预览仅涵盖自己添加的提示内容。隐私和费用受 Codex 提供商、账号与本机配置影响。程序不读取、复制或导出登录凭据。通用模型扩展预留 Python `Provider` 协议，本版仅实现 Codex CLI。

评测比较“全部 AICO 上下文”和“路由后 AICO 上下文”，包含三项合成 JSON 指令遵循任务。离线只报字节，用量和效果字段为 `null`；在线才记录 Codex 返回的 Token 和确切输出校验。该小型评测不能代表一般编程成功率、费用或长期节省收益。参见[评测方法](docs/BENCHMARK.md)。

## 开发与开源

```sh
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m unittest discover -s tests -v
ruff check src tests scripts
python scripts/release_check.py
python -m build --no-isolation
```

采用 MIT 许可证。依赖与构建工具许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。仓库示例全部为合成内容，不包含个人《AI使用经验.docx》。数据库、备份、安装计划、运行记录和密钥都应留在公开仓库之外。本项目独立开发，并非 OpenAI 官方产品。
