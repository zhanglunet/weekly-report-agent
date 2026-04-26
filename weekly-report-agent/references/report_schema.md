# Report Schemas

## EvidenceItem

```json
{
  "id": "string",
  "source_type": "im|meeting|doc|report_history",
  "source_ref": "string",
  "title": "string",
  "time": "ISO8601",
  "actors": ["string"],
  "text": "string",
  "url": "string",
  "entities": {
    "projects": ["string"],
    "tasks": ["string"],
    "people": ["string"],
    "dates": ["string"]
  },
  "signals": ["done", "blocked", "decision", "todo", "risk"],
  "confidence": 0.0,
  "raw_path": "string"
}
```

## Task Timeline Item

```json
{
  "task": "string",
  "status": "done|in_progress|blocked|deferred|dropped|unknown|new",
  "progress_summary": "string",
  "evidence_ids": ["string"],
  "owners": ["string"],
  "next_step": "string",
  "confidence": 0.0,
  "origin": "last_week|new"
}
```

## Validation Result

```json
{
  "ok": true,
  "issue_count": 0,
  "issues": [
    {
      "severity": "warning|error",
      "code": "string",
      "message": "string"
    }
  ],
  "task_count": 0,
  "evidence_count": 0
}
```

