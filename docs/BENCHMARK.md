# Benchmark method

The shipped benchmark is an inspectable evaluation harness, not a broad effectiveness claim. It compares **full approved AICO context** against **keyword-routed AICO context** on three synthetic exact-JSON instruction-adherence tasks (Python/JavaScript/Rust test-command selection). Both arms include the mandatory output-format rule. Twenty-four unrelated synthetic archive skills provide controlled distractors.

```sh
aico benchmark --out /private/offline.json
aico benchmark --send --http --repeats 2 --model YOUR_MODEL --out /private/live.json
```

Offline mode makes no provider call. It reports exact UTF-8 context bytes and prompt hashes; `usage` and `passed` remain `null`. No tokenizer estimate is labelled a real token count.

Live mode runs each pair sequentially in the same temporary workspace. Each invocation is ephemeral and read-only, using the same requested/default model and host configuration. Pair order reverses on alternate repeats. Exact JSON equality to the expected object measures instruction adherence. The report records real Codex `turn.completed.usage` input/output/cached-input tokens, elapsed wall time, execution errors and output. Invalid or missing usage remains `null`, and measured-run counts expose missing measurements. Failures do not count as zero-token successes. A timeout is a failed run without measured usage.

The comparison baseline is all AICO rules in the same adapter, **not** unmodified Codex with no AICO. Codex native rules, skills, tools, configuration and caching remain active and can dominate totals. The temporary workspace prevents incidental repository instructions; it does not remove user-global instructions. Cached tokens are part of input, not additive. The suite does not execute generated code or establish general coding success. No currency/cost calculation is performed. For meaningful comparisons, pin the model, collect multiple repeats, inspect caching, keep the environment fixed and add representative tasks with independent graders.

Release evidence is recorded in `VALIDATION.md` and any explicitly identified synthetic live report. Published reports exclude local paths, thread IDs, credentials and raw native context. Do not publish your own raw run logs without reviewing them for private content.

中文：评测是合成指令遵循实验，不代表一般编程能力或节省率。离线只统计字节；在线才记录提供商返回的真实 Token。基线是同一适配器中加载全部 AICO 规则，原生配置仍可能附加内容。失败或缺失用量保留为 `null`，不得当成零消耗成功。

## Observed release run (one repeat)

See [sanitized live evidence](benchmark-live.json). All three exact-JSON checks passed in each arm. Full context: 59,634 input / 117 output tokens; routed context: 52,828 input / 119 output tokens. Cached input differs (39,552 vs 26,368). One pair had **more** input tokens after routing (17,738 vs 19,750). These are real provider totals for this environment, not a guaranteed saving rate or cost reduction. The model was requested as `gpt-6.1-sol`; native context and provider-side behavior were not controlled.

An initial six-call attempt with a 90-second timeout produced no measured completions. The final run allowed 360 seconds per call; each completed in approximately 121–138 seconds after recovered connection warnings. Retry messages followed by successful completion are preserved as warnings. These transport conditions limit timing comparisons.
