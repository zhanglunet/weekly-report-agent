#!/usr/bin/env python3
"""Parse prior weekly reports and extract report profile plus last-week tasks."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from common import (
    DATE_RE,
    ACTION_WORDS,
    clean_text,
    ensure_dir,
    extract_headings,
    extract_keywords,
    find_report_files,
    read_text_file,
    write_json,
)


DEFAULT_SECTIONS = ["本周概览", "重点进展", "上周计划跟踪", "风险与阻塞", "下周计划", "需确认事项"]


def score_report_file(path: Path, text: str) -> int:
    name = path.name
    score = int(path.stat().st_mtime // 86400)
    if "周报" in name:
        score += 1000
    if DATE_RE.search(name):
        score += 200
    if "下周" in text or "计划" in text:
        score += 100
    return score


def choose_recent_reports(input_path: str, limit: int = 5) -> list[tuple[Path, str]]:
    files = find_report_files(input_path)
    scored: list[tuple[int, Path, str]] = []
    for path in files:
        text = read_text_file(path)
        if text.strip():
            scored.append((score_report_file(path, text), path, text))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [(path, text) for _, path, text in scored[:limit]]


def infer_sections(reports: list[tuple[Path, str]]) -> list[str]:
    counts: dict[str, int] = {}
    for _, text in reports:
        for heading in extract_headings(text):
            normalized = heading.strip()
            if 1 <= len(normalized) <= 30:
                counts[normalized] = counts.get(normalized, 0) + 1
    if not counts:
        return DEFAULT_SECTIONS
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    sections = [name for name, _ in ranked[:8]]
    return sections or DEFAULT_SECTIONS


def extract_section(text: str, names: tuple[str, ...]) -> str:
    lines = text.splitlines()
    blocks: list[str] = []
    active = False
    for line in lines:
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if heading:
            title = heading.group(1)
            active = any(name in title for name in names)
            continue
        if active:
            blocks.append(line)
    return "\n".join(blocks)


def extract_tasks(text: str) -> list[dict[str, Any]]:
    candidate_text = extract_section(text, ("下周", "计划", "待办", "风险", "阻塞")) or text
    tasks: list[dict[str, Any]] = []
    for line in candidate_text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        is_bullet = bool(re.match(r"^[-*+\d.、\s]+", raw))
        has_action = any(word in raw for word in ACTION_WORDS)
        if not is_bullet and not has_action:
            continue
        task = re.sub(r"^[-*+\d.、\s]+", "", raw)
        task = re.sub(r"\|", " ", task)
        task = clean_text(task)
        if 4 <= len(task) <= 160:
            tasks.append(
                {
                    "task": task,
                    "expected_next_step": task,
                    "owner": "",
                    "status_last_week": "planned",
                    "keywords": extract_keywords(task, limit=8),
                }
            )
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for task in tasks:
        key = task["task"]
        if key not in seen:
            seen.add(key)
            unique.append(task)
    return unique[:80]


def infer_tone(text: str) -> str:
    if "|" in text and "状态" in text:
        return "表格化、结果导向"
    if len(text.splitlines()) > 80:
        return "详尽、证据导向"
    return "简洁、结果导向"


def parse_history(input_path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    reports = choose_recent_reports(input_path)
    if not reports:
        raise SystemExit(f"No readable report files found: {input_path}")
    latest_path, latest_text = reports[0]
    all_text = "\n\n".join(text for _, text in reports)
    sections = infer_sections(reports)
    tasks = extract_tasks(latest_text)
    profile = {
        "source": str(latest_path),
        "recent_sources": [str(path) for path, _ in reports],
        "sections": sections,
        "tone": infer_tone(latest_text),
        "task_patterns": ["事项 - 本周进展 - 状态 - 下一步"],
        "owner_style": "姓名/团队",
        "keywords": extract_keywords(all_text, limit=80),
    }
    return profile, tasks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Prior report file or folder")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    out = ensure_dir(args.out)
    profile, tasks = parse_history(args.input)
    write_json(out / "report_profile.json", profile)
    write_json(out / "last_week_tasks.json", tasks)
    print(f"Wrote {out / 'report_profile.json'}")
    print(f"Wrote {out / 'last_week_tasks.json'}")


if __name__ == "__main__":
    main()

