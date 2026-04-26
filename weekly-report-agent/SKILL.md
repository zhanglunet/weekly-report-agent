---
name: weekly-report-agent
description: Generate a weekly report from the user's Lark/Feishu activity. Use when the user wants a Hermes/Codex skill that authorizes their Lark account, reads prior weekly reports, searches this week's Feishu chats, meeting notes, docs, Wiki/knowledge-base content, tracks last week's tasks, and produces a current weekly report with evidence and confirmation items.
metadata:
  requires:
    bins: ["lark-cli", "python3"]
---

# Weekly Report Agent

Use this skill to generate a weekly report from Feishu/Lark activity and prior reports.

## One-Sentence Use

After installation, the user can say:

```text
用 weekly-report-agent，授权我的飞书账号，读取我提供的上周周报或周报文件夹，生成本周周报。
```

## Required Flow

1. Authorize Lark as the end user.
   - Use user identity for personal chats, meetings, docs, and Wiki resources.
   - Start with read-only scopes. If a command reports missing scopes, show the missing scopes and ask the user to authorize them.
   - Never print secrets, access tokens, app secrets, or raw credential files.

2. Load prior report context.
   - Prefer the user-provided previous weekly report.
   - If the user provides a folder, identify the latest report and infer the stable report structure from recent reports.
   - Extract last week's planned items, unfinished items, risks, owners, and report style.

3. Collect current-week context.
   - Default time range is Monday 00:00 in the user's timezone through now.
   - Collect only resources visible to the authorized user.
   - Search chats, meeting records/notes, docs, and Wiki/docs knowledge sources.
   - Preserve source IDs, URLs, timestamps, and raw response paths where available.

4. Build task progress.
   - Match last week's tasks against this week's evidence.
   - Classify each task as `done`, `in_progress`, `blocked`, `deferred`, `dropped`, `unknown`, or `new`.
   - Keep evidence references for every certain conclusion.
   - Put low-confidence claims in confirmation items instead of the main report.

5. Generate and validate the report.
   - Reuse the previous report's section structure when possible.
   - Otherwise use `assets/default_report_template.md`.
   - Validate coverage of last week's tasks, evidence-backed status, and out-of-range sources.

## Script Pipeline

For the normal path, use the orchestrator:

```bash
python3 scripts/run_weekly_report.py --history <report-file-or-folder> --out .weekly-report-work --dry-run
```

For manual debugging, run the scripts in order:

```bash
python3 scripts/parse_report_history.py --input <report-file-or-folder> --out .weekly-report-work
python3 scripts/collect_lark_context.py --profile .weekly-report-work/report_profile.json --tasks .weekly-report-work/last_week_tasks.json --out .weekly-report-work
python3 scripts/build_task_timeline.py --evidence .weekly-report-work/evidence.jsonl --tasks .weekly-report-work/last_week_tasks.json --out .weekly-report-work/task_timeline.json
python3 scripts/generate_report.py --profile .weekly-report-work/report_profile.json --timeline .weekly-report-work/task_timeline.json --out .weekly-report-work/weekly_report.md
python3 scripts/validate_report.py --report .weekly-report-work/weekly_report.md --timeline .weekly-report-work/task_timeline.json --evidence .weekly-report-work/evidence.jsonl --out .weekly-report-work/validation.json
```

Use `--dry-run` on `collect_lark_context.py` when Lark is not authorized yet or while testing.

## Lark Collection Notes

- For chat search, prefer `lark-cli im +messages-search` with keywords from prior tasks and report profile. Use `+chat-messages-list` only when the user provides important chat IDs.
- For meetings, prefer `lark-cli vc +search` followed by `lark-cli vc +notes`.
- For docs, prefer `lark-cli docs +search` and `lark-cli docs +fetch`.
- For Wiki URLs, resolve the Wiki token to the underlying object token before fetching content.
- Always paginate when commands return a page token.

## Output Requirements

The final report should include:

- Weekly date range.
- Summary of key progress.
- Last-week plan tracking.
- New work discovered this week.
- Risks/blockers.
- Next-week plan.
- Confirmation items for uncertain or conflicting evidence.

Do not state a task is complete unless supporting evidence exists.
