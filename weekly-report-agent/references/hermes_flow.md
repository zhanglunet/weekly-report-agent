# Hermes Flow

## Step 1: Authorize Lark

Action: `authorize_lark()`

Expected state:

```json
{
  "auth": {
    "status": "not_started|pending|authorized|permission_missing|failed",
    "missing_scopes": []
  }
}
```

The UI should show a single authorization button, current status, and any missing scopes.

## Step 2: Select Report History

Actions:

- `select_report_history(input)`
- `analyze_report_profile()`

Accepted inputs:

- Local report file.
- Local report folder.
- Lark doc URL or token.
- Lark folder or Wiki URL.

Outputs:

- `report_profile.json`
- `last_week_tasks.json`

## Step 3: Generate Weekly Report

Actions:

- `collect_week_context(time_range, sources)`
- `generate_weekly_report(options)`
- `revise_report(feedback)`
- `export_report(format)`
- `publish_to_lark_doc(folder_or_doc)`

The UI should show collection progress per data source and allow the user to disable noisy sources.

## Recommended Work Directory

Use `.weekly-report-work` under the active project or a Hermes session work directory.

Expected files:

```text
.weekly-report-work/
├── report_profile.json
├── last_week_tasks.json
├── evidence.jsonl
├── collection_meta.json
├── task_timeline.json
├── weekly_report.md
├── report_meta.json
├── validation.json
└── raw/
```

