#!/usr/bin/env python3
"""Generate a Markdown weekly report from profile and task timeline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import current_week_range, ensure_dir, read_json, write_json


STATUS_LABELS = {
    "done": "已完成",
    "in_progress": "推进中",
    "blocked": "阻塞",
    "deferred": "延期",
    "dropped": "取消",
    "unknown": "待确认",
    "new": "新增",
}


def bullet(items: list[str], empty: str = "暂无") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        safe = [str(cell).replace("\n", " ").replace("|", " / ") for cell in row]
        lines.append("| " + " | ".join(safe) + " |")
    return "\n".join(lines)


def evidence_ref(ids: list[str]) -> str:
    if not ids:
        return "需确认"
    return ", ".join(ids[:3])


def generate(profile: dict[str, Any], timeline: dict[str, Any], start: str, end: str) -> str:
    tasks = timeline.get("tasks", [])
    done = [task for task in tasks if task.get("status") == "done"]
    active = [task for task in tasks if task.get("status") in {"in_progress", "new"}]
    risks = [task for task in tasks if task.get("status") in {"blocked", "deferred"}]
    unknown = [task for task in tasks if task.get("status") == "unknown" or task.get("confidence", 0) < 0.45]

    overview_items = [
        f"本周共归并 {len(tasks)} 个任务/事项，其中已完成 {len(done)} 个，推进中或新增 {len(active)} 个，风险/延期 {len(risks)} 个。",
        f"周报结构参考：{profile.get('source', '默认模板')}。",
    ]
    if done[:1]:
        overview_items.append(f"主要完成项：{done[0]['task']}。")

    progress_rows = [
        [
            task.get("task", ""),
            task.get("progress_summary", ""),
            STATUS_LABELS.get(task.get("status"), task.get("status", "")),
            evidence_ref(task.get("evidence_ids", [])),
        ]
        for task in tasks
        if task.get("status") in {"done", "in_progress", "new"}
    ]
    tracking_rows = [
        [
            task.get("task", ""),
            STATUS_LABELS.get(task.get("status"), task.get("status", "")),
            task.get("next_step", ""),
        ]
        for task in tasks
        if task.get("origin") == "last_week"
    ]
    risk_items = [
        f"{task.get('task')}: {task.get('progress_summary')}；下一步：{task.get('next_step')}"
        for task in risks
    ]
    next_week_items = []
    for task in tasks:
        if task.get("status") in {"in_progress", "blocked", "deferred", "unknown", "new"}:
            next_week_items.append(f"{task.get('task')}: {task.get('next_step')}")
    confirmation_items = [
        f"{task.get('task')}: 当前证据不足或置信度较低，请确认实际进展。"
        for task in unknown
    ]

    return "\n\n".join(
        [
            f"# 本周周报（{start[:10]} - {end[:10]}）",
            "## 本周概览\n\n" + bullet(overview_items),
            "## 重点进展\n\n" + (table(["事项", "本周进展", "状态", "证据"], progress_rows) if progress_rows else "- 暂无明确重点进展"),
            "## 上周计划跟踪\n\n" + (table(["上周事项", "本周结果", "下一步"], tracking_rows) if tracking_rows else "- 未识别到上周计划项"),
            "## 风险与阻塞\n\n" + bullet(risk_items),
            "## 下周计划\n\n" + bullet(next_week_items),
            "## 需确认事项\n\n" + bullet(confirmation_items),
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    args = parser.parse_args()

    start, end = (args.start, args.end) if args.start and args.end else current_week_range(args.timezone)
    profile = read_json(args.profile, {})
    timeline = read_json(args.timeline, {"tasks": []})
    report = generate(profile, timeline, start, end)
    out = Path(args.out)
    ensure_dir(out.parent)
    out.write_text(report, encoding="utf-8")
    write_json(
        out.with_name("report_meta.json"),
        {
            "range_start": start,
            "range_end": end,
            "task_count": len(timeline.get("tasks", [])),
            "profile_source": profile.get("source"),
        },
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

