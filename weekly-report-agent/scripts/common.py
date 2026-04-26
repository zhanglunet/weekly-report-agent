#!/usr/bin/env python3
"""Shared helpers for the weekly report skill scripts."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


DATE_RE = re.compile(r"20\d{2}[-./年]\d{1,2}[-./月]\d{1,2}")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ACTION_WORDS = (
    "完成",
    "上线",
    "发布",
    "交付",
    "推进",
    "修复",
    "接入",
    "整理",
    "确认",
    "延期",
    "阻塞",
    "风险",
    "待办",
    "计划",
    "跟进",
)


@dataclass
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass
class EvidenceItem:
    id: str
    source_type: str
    source_ref: str
    title: str
    time: str
    actors: list[str]
    text: str
    url: str = ""
    entities: dict[str, list[str]] = field(default_factory=dict)
    signals: list[str] = field(default_factory=list)
    confidence: float = 0.5
    raw_path: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "title": self.title,
            "time": self.time,
            "actors": self.actors,
            "text": self.text,
            "url": self.url,
            "entities": self.entities,
            "signals": self.signals,
            "confidence": self.confidence,
            "raw_path": self.raw_path,
        }


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def read_json(path: str | Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_command(command: list[str], timeout: int = 90) -> CommandResult:
    proc = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return CommandResult(command, proc.returncode, proc.stdout, proc.stderr)


def parse_json_maybe(text: str) -> Any:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        first = text.find("{")
        last = text.rfind("}")
        if first >= 0 and last > first:
            return json.loads(text[first : last + 1])
    return None


def current_week_range(tz_name: str = "Asia/Shanghai") -> tuple[str, str]:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    monday = now.date() - timedelta(days=now.weekday())
    start = datetime.combine(monday, time.min, tzinfo=tz)
    return start.isoformat(), now.isoformat()


def iso_to_epoch_seconds(value: str) -> int:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            headings.append(match.group(2).strip())
    return headings


def extract_keywords(text: str, limit: int = 40) -> list[str]:
    candidates: list[str] = []
    for line in split_lines(text):
        if any(word in line for word in ACTION_WORDS):
            short = re.sub(r"^[-*+\d.\s]+", "", line).strip()
            if 4 <= len(short) <= 80:
                candidates.append(short)
    for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9][\u4e00-\u9fffA-Za-z0-9_-]{2,24}", text):
        if token not in candidates and len(token) >= 3:
            candidates.append(token)
    seen: set[str] = set()
    result: list[str] = []
    for item in candidates:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
        if len(result) >= limit:
            break
    return result


def infer_signals(text: str) -> list[str]:
    signals: list[str] = []
    checks = {
        "done": ("完成", "已完成", "上线", "发布", "交付", "修复完", "done"),
        "blocked": ("阻塞", "卡住", "依赖", "风险", "无法", "blocked"),
        "deferred": ("延期", "推迟", "下周再", "延后", "defer"),
        "todo": ("待办", "TODO", "下周", "计划", "跟进", "需要"),
        "decision": ("决定", "确认", "结论", "定了", "方案"),
    }
    lowered = text.lower()
    for signal, words in checks.items():
        if any(word.lower() in lowered for word in words):
            signals.append(signal)
    return signals


def read_text_file(path: str | Path) -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in {".md", ".txt", ".markdown", ".json"}:
        return p.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        return read_docx_text(p)
    if suffix == ".pdf":
        return read_pdf_text(p)
    return p.read_text(encoding="utf-8", errors="ignore")


def read_docx_text(path: Path) -> str:
    try:
        from zipfile import ZipFile
        import xml.etree.ElementTree as ET

        with ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        parts = [node.text or "" for node in root.findall(".//w:t", ns)]
        return "\n".join(parts)
    except Exception:
        return ""


def read_pdf_text(path: Path) -> str:
    try:
        result = run_command(["pdftotext", str(path), "-"], timeout=30)
        if result.returncode == 0:
            return result.stdout
    except Exception:
        return ""
    return ""


def find_report_files(path: str | Path) -> list[Path]:
    p = Path(path)
    if p.is_file():
        return [p]
    suffixes = {".md", ".txt", ".markdown", ".docx", ".pdf"}
    files = [item for item in p.rglob("*") if item.is_file() and item.suffix.lower() in suffixes]
    return sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)


def safe_id(prefix: str, value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return f"{prefix}-{cleaned[:80]}" if cleaned else prefix


def redact_sensitive(text: str) -> str:
    patterns = [
        r"(access_token|refresh_token|appSecret|app_secret|tenant_access_token)[=:]\s*['\"]?[^'\"\s]+",
        r"Bearer\s+[A-Za-z0-9._-]+",
    ]
    result = text
    for pattern in patterns:
        result = re.sub(pattern, r"\1=<redacted>", result, flags=re.IGNORECASE)
    return result


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}

