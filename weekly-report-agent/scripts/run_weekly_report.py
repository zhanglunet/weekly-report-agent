#!/usr/bin/env python3
"""Run the full weekly report pipeline in dependency order."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from common import ensure_dir, read_json, write_json


SCRIPT_DIR = Path(__file__).resolve().parent


def run_step(command: list[str]) -> None:
    print("+ " + " ".join(command))
    proc = subprocess.run(command, check=False, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True, help="Prior report file or folder")
    parser.add_argument("--out", required=True, help="Work/output directory")
    parser.add_argument("--start", help="ISO start time")
    parser.add_argument("--end", help="ISO end time")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--sources", default="im,meeting,doc")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    out = ensure_dir(args.out)
    python = sys.executable or "python3"
    common_time_args = ["--timezone", args.timezone]
    if args.start and args.end:
        common_time_args = ["--start", args.start, "--end", args.end, "--timezone", args.timezone]

    run_step([python, str(SCRIPT_DIR / "parse_report_history.py"), "--input", args.history, "--out", str(out)])

    collect_cmd = [
        python,
        str(SCRIPT_DIR / "collect_lark_context.py"),
        "--profile",
        str(out / "report_profile.json"),
        "--tasks",
        str(out / "last_week_tasks.json"),
        "--out",
        str(out),
        "--sources",
        args.sources,
        *common_time_args,
    ]
    if args.dry_run:
        collect_cmd.append("--dry-run")
    run_step(collect_cmd)

    run_step(
        [
            python,
            str(SCRIPT_DIR / "build_task_timeline.py"),
            "--evidence",
            str(out / "evidence.jsonl"),
            "--tasks",
            str(out / "last_week_tasks.json"),
            "--out",
            str(out / "task_timeline.json"),
        ]
    )
    run_step(
        [
            python,
            str(SCRIPT_DIR / "generate_report.py"),
            "--profile",
            str(out / "report_profile.json"),
            "--timeline",
            str(out / "task_timeline.json"),
            "--out",
            str(out / "weekly_report.md"),
            *common_time_args,
        ]
    )
    run_step(
        [
            python,
            str(SCRIPT_DIR / "validate_report.py"),
            "--report",
            str(out / "weekly_report.md"),
            "--timeline",
            str(out / "task_timeline.json"),
            "--evidence",
            str(out / "evidence.jsonl"),
            "--out",
            str(out / "validation.json"),
        ]
    )
    summary = {
        "report": str(out / "weekly_report.md"),
        "validation": read_json(out / "validation.json", {}),
        "dry_run": args.dry_run,
    }
    write_json(out / "run_summary.json", summary)
    print(f"Report ready: {out / 'weekly_report.md'}")


if __name__ == "__main__":
    main()

