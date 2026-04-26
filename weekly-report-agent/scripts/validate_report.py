#!/usr/bin/env python3
"""Validate report coverage and evidence discipline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import read_json, read_jsonl, write_json


def validate(report: str, timeline: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_ids = {item.get("id") for item in evidence}
    issues: list[dict[str, Any]] = []
    tasks = timeline.get("tasks", [])

    for task in tasks:
        name = task.get("task", "")
        if name and name not in report:
            issues.append({"severity": "warning", "code": "task_missing_from_report", "message": name})
        if task.get("status") == "done" and not task.get("evidence_ids"):
            issues.append({"severity": "error", "code": "done_without_evidence", "message": name})
        for evidence_id in task.get("evidence_ids", []):
            if evidence_id not in evidence_ids:
                issues.append({"severity": "error", "code": "missing_evidence_ref", "message": f"{name}: {evidence_id}"})

    if "需确认事项" not in report:
        issues.append({"severity": "warning", "code": "missing_confirmation_section", "message": "Report should include confirmation items"})
    if "下周计划" not in report:
        issues.append({"severity": "warning", "code": "missing_next_week_section", "message": "Report should include next week plan"})

    errors = [issue for issue in issues if issue["severity"] == "error"]
    return {
        "ok": not errors,
        "issue_count": len(issues),
        "issues": issues,
        "task_count": len(tasks),
        "evidence_count": len(evidence),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report = Path(args.report).read_text(encoding="utf-8")
    timeline = read_json(args.timeline, {"tasks": []})
    evidence = read_jsonl(args.evidence)
    result = validate(report, timeline, evidence)
    write_json(args.out, result)
    print(f"Wrote {args.out} (ok={result['ok']}, issues={result['issue_count']})")


if __name__ == "__main__":
    main()

