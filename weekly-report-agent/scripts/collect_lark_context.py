#!/usr/bin/env python3
"""Collect this week's Lark context into normalized evidence JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from common import (
    EvidenceItem,
    clean_text,
    current_week_range,
    ensure_dir,
    infer_signals,
    iso_to_epoch_seconds,
    parse_json_maybe,
    read_json,
    redact_sensitive,
    run_command,
    safe_id,
    write_json,
    write_jsonl,
)


def item_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return safe_id(prefix, digest)


def load_keywords(profile_path: str | None, tasks_path: str | None) -> list[str]:
    keywords: list[str] = []
    profile = read_json(profile_path, {}) if profile_path else {}
    tasks = read_json(tasks_path, []) if tasks_path else []
    keywords.extend(profile.get("keywords", [])[:40])
    for task in tasks:
        keywords.extend(task.get("keywords", [])[:8])
        if task.get("task"):
            keywords.append(task["task"][:40])
    seen: set[str] = set()
    result: list[str] = []
    for keyword in keywords:
        keyword = str(keyword).strip()
        if len(keyword) < 2:
            continue
        key = keyword.lower()
        if key not in seen:
            seen.add(key)
            result.append(keyword)
    return result[:60]


def normalize_record(source_type: str, record: dict[str, Any], fallback_time: str) -> EvidenceItem:
    text_candidates = [
        record.get("text"),
        record.get("content"),
        record.get("summary"),
        record.get("description"),
        record.get("title"),
    ]
    text = clean_text(" ".join(str(v) for v in text_candidates if v))
    title = str(record.get("title") or record.get("name") or text[:40] or source_type)
    ref = str(record.get("message_id") or record.get("meeting_id") or record.get("doc_token") or record.get("id") or title)
    when = str(record.get("time") or record.get("send_time") or record.get("start_time") or record.get("updated_time") or fallback_time)
    actors = record.get("actors") or record.get("participants") or []
    if isinstance(actors, str):
        actors = [actors]
    url = str(record.get("url") or record.get("link") or "")
    return EvidenceItem(
        id=item_id(source_type, f"{source_type}:{ref}:{text}"),
        source_type=source_type,
        source_ref=ref,
        title=title,
        time=when,
        actors=actors,
        text=text,
        url=url,
        entities={"projects": [], "tasks": [], "people": actors, "dates": []},
        signals=infer_signals(text),
        confidence=0.7 if text else 0.3,
    )


def mock_evidence(start: str, end: str, keywords: list[str]) -> list[EvidenceItem]:
    focus = keywords[:3] or ["周报智能体", "飞书数据采集", "任务跟踪"]
    rows = [
        {
            "source_type": "meeting",
            "title": f"{focus[0]} 周会",
            "summary": f"确认本周继续推进 {focus[0]}，已完成基础方案，待补充 Hermes 前端联调。",
            "time": start,
            "participants": ["当前用户"],
        },
        {
            "source_type": "im",
            "title": f"{focus[-1]} 进展沟通",
            "text": f"{focus[-1]} 已完成初版，风险是权限授权范围需要继续确认，下周跟进真实账号验证。",
            "time": end,
            "actors": ["当前用户"],
        },
        {
            "source_type": "doc",
            "title": "本周知识库更新",
            "summary": f"文档补充了 {', '.join(focus)} 的实施记录和下一步计划。",
            "updated_time": end,
            "actors": ["当前用户"],
        },
    ]
    return [normalize_record(row.pop("source_type"), row, end) for row in rows]


def save_raw(out: Path, name: str, data: Any) -> str:
    raw_dir = ensure_dir(out / "raw")
    path = raw_dir / f"{name}.json"
    write_json(path, data)
    return str(path)


def collect_command_json(command: list[str], out: Path, raw_name: str) -> tuple[Any, str | None]:
    result = run_command(command)
    raw = {
        "command": command,
        "returncode": result.returncode,
        "stdout": redact_sensitive(result.stdout),
        "stderr": redact_sensitive(result.stderr),
    }
    raw_path = save_raw(out, raw_name, raw)
    if result.returncode != 0:
        return None, raw_path
    return parse_json_maybe(result.stdout), raw_path


def collect_lark(start: str, end: str, keywords: list[str], sources: set[str], out: Path) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    # lark-cli currently expects ISO timestamps for these high-level helpers.
    # Older drafts used epoch seconds with --start-time/--end-time, which now
    # fails with "unknown flag" or field validation errors.
    start_ts = start
    end_ts = end

    if "im" in sources:
        for idx, keyword in enumerate(keywords[:20]):
            command = [
                "lark-cli",
                "im",
                "+messages-search",
                "--query",
                keyword,
                "--start",
                start_ts,
                "--end",
                end_ts,
                "--format",
                "json",
            ]
            data, raw_path = collect_command_json(command, out, f"im_search_{idx}")
            records = data.get("items", data if isinstance(data, list) else []) if data else []
            for record in records:
                item = normalize_record("im", record, end)
                item.raw_path = raw_path or ""
                evidence.append(item)

    if "meeting" in sources:
        command = ["lark-cli", "vc", "+search", "--start", start_ts, "--end", end_ts, "--format", "json"]
        data, raw_path = collect_command_json(command, out, "vc_search")
        records = data.get("items", data if isinstance(data, list) else []) if data else []
        meeting_ids = []
        for record in records:
            item = normalize_record("meeting", record, end)
            item.raw_path = raw_path or ""
            evidence.append(item)
            if record.get("meeting_id"):
                meeting_ids.append(record["meeting_id"])
        if meeting_ids:
            command = ["lark-cli", "vc", "+notes", "--meeting-ids", ",".join(meeting_ids[:50]), "--format", "json"]
            notes, notes_path = collect_command_json(command, out, "vc_notes")
            note_records = notes.get("items", notes if isinstance(notes, list) else []) if notes else []
            for record in note_records:
                item = normalize_record("meeting", record, end)
                item.raw_path = notes_path or ""
                evidence.append(item)

    if "doc" in sources:
        for idx, keyword in enumerate(keywords[:20]):
            command = ["lark-cli", "docs", "+search", "--query", keyword, "--format", "json"]
            data, raw_path = collect_command_json(command, out, f"docs_search_{idx}")
            records = data.get("items", data if isinstance(data, list) else []) if data else []
            for record in records:
                item = normalize_record("doc", record, end)
                item.raw_path = raw_path or ""
                evidence.append(item)
    return dedupe_evidence(evidence)


def dedupe_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
    seen: set[str] = set()
    result: list[EvidenceItem] = []
    for item in items:
        key = item.source_ref or item.id
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", help="report_profile.json")
    parser.add_argument("--tasks", help="last_week_tasks.json")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--start", help="ISO start time")
    parser.add_argument("--end", help="ISO end time")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--sources", default="im,meeting,doc")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    out = ensure_dir(args.out)
    start, end = (args.start, args.end) if args.start and args.end else current_week_range(args.timezone)
    keywords = load_keywords(args.profile, args.tasks)
    sources = {item.strip() for item in args.sources.split(",") if item.strip()}
    evidence = mock_evidence(start, end, keywords) if args.dry_run else collect_lark(start, end, keywords, sources, out)
    rows = [item.to_json() for item in evidence]
    write_jsonl(out / "evidence.jsonl", rows)
    write_json(
        out / "collection_meta.json",
        {
            "range_start": start,
            "range_end": end,
            "sources": sorted(sources),
            "dry_run": args.dry_run,
            "keywords": keywords,
            "evidence_count": len(rows),
        },
    )
    print(f"Wrote {out / 'evidence.jsonl'} ({len(rows)} items)")


if __name__ == "__main__":
    main()

