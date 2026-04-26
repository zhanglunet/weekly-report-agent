# Weekly Report Agent

一个用于 Hermes/Codex 的周报生成 Skill。它会读取上周或历来周报，自动采集本周飞书/Lark 中的聊天、会议纪要、云文档和知识库线索，跟踪上周任务进展，并生成本周周报草稿。

## 一句话安装和使用

安装：

```bash
npx skills add https://github.com/zhanglunet/weekly-report-agent/tree/main/weekly-report-agent
```

使用：

```text
用 weekly-report-agent，授权我的飞书账号，读取我提供的上周周报或周报文件夹，生成本周周报。
```

就这两句。安装后重启 Hermes/Codex，让新 Skill 生效。

## 功能

- 飞书 user 身份授权，读取用户本人可见范围内的数据。
- 支持输入上周周报文件或周报文件夹。
- 自动计算本周时间范围：默认从周一 00:00 到当前时间。
- 采集并归一化聊天、会议、文档证据。
- 对照上周计划生成任务进展状态：已完成、推进中、阻塞、延期、待确认、新增。
- 生成 Markdown 周报，并输出校验结果。
- 支持 dry-run，无需飞书授权即可验证完整管线。

## 目录结构

```text
.
├── weekly-report-agent/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── assets/default_report_template.md
│   ├── references/
│   └── scripts/
├── tests/fixtures/last_week_report.md
└── weekly-report-agent-design.md
```

关键脚本：

- `run_weekly_report.py`：完整管线入口。
- `parse_report_history.py`：解析历史周报和上周任务。
- `collect_lark_context.py`：采集飞书上下文，支持 `--dry-run`。
- `build_task_timeline.py`：生成任务进展时间线。
- `generate_report.py`：生成 Markdown 周报。
- `validate_report.py`：校验周报和证据链。

## 本地快速验证

用内置 fixture 跑通 dry-run：

```bash
python3 weekly-report-agent/scripts/run_weekly_report.py \
  --history tests/fixtures/last_week_report.md \
  --out /tmp/weekly-report-agent-demo \
  --dry-run
```

生成结果：

```text
/tmp/weekly-report-agent-demo/
├── report_profile.json
├── last_week_tasks.json
├── evidence.jsonl
├── task_timeline.json
├── weekly_report.md
├── validation.json
└── run_summary.json
```

查看周报：

```bash
sed -n '1,200p' /tmp/weekly-report-agent-demo/weekly_report.md
```

## 接入真实飞书数据

先完成 `lark-cli` 配置和用户授权：

```bash
lark-cli config init --new
lark-cli auth login --scope "<required_scope>"
```

然后去掉 `--dry-run`：

```bash
python3 weekly-report-agent/scripts/run_weekly_report.py \
  --history /path/to/last_week_report.md \
  --out .weekly-report-work
```

默认数据源是：

```text
im,meeting,doc
```

可手动指定：

```bash
python3 weekly-report-agent/scripts/run_weekly_report.py \
  --history /path/to/last_week_report.md \
  --out .weekly-report-work \
  --sources meeting,doc
```

## 时间范围

默认使用 `Asia/Shanghai` 时区，范围为本周一 00:00 到当前时间。

也可以显式指定：

```bash
python3 weekly-report-agent/scripts/run_weekly_report.py \
  --history /path/to/last_week_report.md \
  --out .weekly-report-work \
  --start 2026-04-20T00:00:00+08:00 \
  --end 2026-04-26T18:00:00+08:00
```

## Hermes 使用流程

目标交互是三步：

1. 授权自己的飞书账号。
2. 提供历来周报文件夹，或直接提供上周周报。
3. 生成本周周报，并在预览区确认/修改/导出。

Hermes 侧建议映射的 actions：

- `authorize_lark()`
- `select_report_history(input)`
- `analyze_report_profile()`
- `collect_week_context(time_range, sources)`
- `generate_weekly_report(options)`
- `revise_report(feedback)`
- `export_report(format)`
- `publish_to_lark_doc(folder_or_doc)`

## 安全说明

- 默认使用飞书 user 身份，访问范围受用户授权和飞书权限控制。
- 脚本会尽量脱敏命令输出中的 token/secret。
- `.weekly-report-work/` 已加入 `.gitignore`，避免误提交本地采集结果。
- 不应把 app secret、access token、refresh token 写入仓库。

## 当前状态

已实现第一版可运行 MVP：

- 本地周报解析。
- dry-run 数据采集。
- lark-cli 真实采集入口。
- 任务状态归并。
- Markdown 周报生成。
- 校验报告输出。

真实飞书端到端运行需要可用的 `lark-cli` 配置、飞书应用权限和用户授权。
