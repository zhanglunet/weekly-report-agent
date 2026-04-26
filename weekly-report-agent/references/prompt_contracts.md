# Prompt Contracts

## Task Extraction

Extract task-like items from prior reports. Prefer items in sections named 下周计划, 待办, 风险, 阻塞, Next Week, TODO.

Each extracted task should include:

- Task text.
- Expected next step.
- Owner if explicitly present.
- Keywords for retrieval.

## Evidence Summarization

Summaries must be grounded in evidence text. Do not mark a task done unless one of the evidence items has a completion signal such as 完成, 已完成, 上线, 发布, 交付, 修复完.

## Report Writing

Use concise, work-report style Chinese by default. Avoid dramatic wording.

Every high-confidence progress statement should be traceable to at least one evidence ID. Uncertain claims go under 需确认事项.

## Revision

When the user gives feedback, change only the affected section unless they ask for a full rewrite. Keep evidence IDs stable when possible.

