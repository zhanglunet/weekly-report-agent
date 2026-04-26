#!/usr/bin/env python3
"""Build task progress timeline from prior tasks and current evidence."""

from __future__ import annotations

import argparse
import difflib
from typing import Any

from common import extract_keywords, infer_signals, read_json, read_jsonl, write_json


STATUS_PRIORITY = {
    "blocked": 5,
    "done": 4,
    "deferred": 3,
    "in_progress": 2,
    "unknown": 1,
}


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def evidence_score(task: dict[str, Any], evidence: dict[str, Any]) -> float:
    task_text = task.get("task", "")
    evidence_text = " ".join([evidence.get("title", ""), evidence.get("text", "")])
    score = similarity(task_text, evidence_text)
    for keyword in task.get("keywords") or extract_keywords(task_text, limit=8):
        if keyword and keyword in evidence_text:
            score += 0.25
    return min(score, 1.0)


def classify(signals: list[str], text: str) -> str:
    lowered = text.lower()
    if "blocked" in signals:
        return "blocked"
    if "done" in signals:
        return "done"
    if "deferred" in signals:
        return "deferred"
    if any(word in lowered for word in ("推进", "进行", "处理中", "接入", "联调", "完善", "补充")):
        return "in_progress"
    return "unknown"


def merge_status(current: str, candidate: str) -> str:
    return candidate if STATUS_PRIORITY.get(candidate, 0) > STATUS_PRIORITY.get(current, 0) else current


def summarize_evidence(matches: list[dict[str, Any]]) -> str:
    snippets: list[str] = []
    for item in matches[:3]:
        text = item.get("text") or item.get("title") or ""
        if text:
            snippets.append(text[:90])
    return "；".join(snippets) if snippets else "本周暂无明确证据"


def build_timeline(tasks: list[dict[str, Any]], evidence_rows: list[dict[str, Any]]) -> dict[str, Any]:
    timeline: list[dict[str, Any]] = []
    used_evidence: set[str] = set()

    for task in tasks:
        matches = []
        for evidence in evidence_rows:
            score = evidence_score(task, evidence)
            if score >= 0.28:
                item = dict(evidence)
                item["_match_score"] = score
                matches.append(item)
        matches.sort(key=lambda row: row.get("_match_score", 0), reverse=True)
        status = "unknown"
        for match in matches:
            status = merge_status(status, classify(match.get("signals", []), match.get("text", "")))
            used_evidence.add(match.get("id", ""))
        confidence = min(0.95, 0.35 + sum(match.get("_match_score", 0) for match in matches[:3]) / 3)
        timeline.append(
            {
                "task": task.get("task", ""),
                "status": status,
                "progress_summary": summarize_evidence(matches),
                "evidence_ids": [match.get("id") for match in matches[:5] if match.get("id")],
                "owners": [task.get("owner")] if task.get("owner") else [],
                "next_step": infer_next_step(status, task),
                "confidence": round(confidence if matches else 0.25, 2),
                "origin": "last_week",
            }
        )

    for evidence in evidence_rows:
        evidence_id = evidence.get("id", "")
        if evidence_id in used_evidence:
            continue
        text = evidence.get("text") or evidence.get("title") or ""
        signals = evidence.get("signals") or infer_signals(text)
        if not any(signal in signals for signal in ("done", "todo", "blocked", "decision")):
            continue
        timeline.append(
            {
                "task": evidence.get("title") or text[:60],
                "status": classify(signals, text) if "todo" not in signals else "new",
                "progress_summary": text[:160],
                "evidence_ids": [evidence_id],
                "owners": evidence.get("actors", []),
                "next_step": "继续跟进并在下周周报中更新",
                "confidence": evidence.get("confidence", 0.5),
                "origin": "new",
            }
        )

    return {"tasks": timeline, "evidence_count": len(evidence_rows)}


def infer_next_step(status: str, task: dict[str, Any]) -> str:
    if status == "done":
        return "沉淀结果，关注后续反馈"
    if status == "blocked":
        return "明确阻塞责任人与解除时间"
    if status == "deferred":
        return "重新确认排期和优先级"
    if status == "in_progress":
        return "下周继续推进到可交付状态"
    return task.get("expected_next_step") or "需要确认本周实际进展"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    tasks = read_json(args.tasks, [])
    evidence = read_jsonl(args.evidence)
    timeline = build_timeline(tasks, evidence)
    write_json(args.out, timeline)
    print(f"Wrote {args.out} ({len(timeline['tasks'])} tasks)")


if __name__ == "__main__":
    main()

