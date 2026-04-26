# 周报生成智能体功能设计与开发计划

## 1. 目标与边界

目标：做一个可在 Hermes Agent 中使用的“周报生成 Skill”。用户只需要完成三步：

1. 授权自己的飞书账号。
2. 提供历来周报文件夹，或直接提供上周周报。
3. 一键生成本周周报。

智能体自动从“本周一 00:00 到当前时间”搜索飞书信息，包括聊天记录、会议纪要、云文档、知识库/云空间文档、任务线索等；结合历来周报尤其是上周周报，追踪任务进展，整理成本周周报草稿，并支持用户在 Hermes 前端预览、补充、再生成。

边界：

- 第一版只生成 Markdown/飞书文档格式的周报，不做复杂排版型 PPT。
- 第一版以用户本人授权可见范围为准，不尝试绕过飞书权限。
- 写入飞书文档、创建新文档属于可选发布动作，生成草稿默认落本地或 Hermes 会话产物。
- “本周知识库”通过用户可访问的飞书文档、Wiki、会议纪要、聊天附件和给定周报目录推断，不预设单独数据库。

## 2. 用户体验流程

### 2.1 Hermes 三步流程

#### Step 1：飞书授权

界面元素：

- “授权飞书账号”按钮。
- 授权状态：未授权 / 授权中 / 已授权 / 权限不足。
- 权限说明折叠面板：展示需要读取的资源类型，不展示 token。

行为：

- 调用 `lark-cli auth login` 发起 user 身份授权。
- 按最小权限分阶段申请 scope。基础版先申请读取聊天、云文档、会议记录/纪要相关权限；遇到权限不足时再增量授权。
- 授权成功后执行一次轻量 health check，例如获取当前用户、搜索最近一条可见文档或会议。

#### Step 2：提供历史周报上下文

用户可以二选一：

- 提供“历来周报文件夹”：支持本地文件夹、飞书云空间文件夹、飞书 Wiki 节点。
- 提供“上周周报”：支持本地文件、飞书文档链接、飞书文档 token。

界面元素：

- 文件夹/文档选择器或粘贴 URL 输入框。
- “检测周报格式”按钮。
- 识别结果预览：标题模式、日期范围、栏目结构、上周待办、未完成项、风险项。

行为：

- 若提供文件夹：按更新时间和标题日期识别最近几份周报，优先定位上周周报。
- 若提供上周周报：直接抽取上周任务、承诺、阻塞、下周计划。
- 生成一个 `report_profile`：包含周报结构、语气、固定栏目、常用项目名、负责人命名风格。

#### Step 3：生成本周周报

界面元素：

- 时间范围：默认本周一 00:00 到当前时间，可手动调整。
- 数据源开关：聊天、会议、文档、知识库、历史周报。
- “生成周报”按钮。
- 生成过程进度：检索中、归并中、任务跟踪中、起草中、校验中。
- 结果预览：Markdown 编辑器 + “重新生成/按反馈修改/导出/发布到飞书”。

行为：

- 自动检索飞书信息。
- 归并证据，形成任务进展表。
- 对照上周周报，标注完成、推进中、延期、取消、新增。
- 按历史周报格式生成本周周报。
- 给出低置信度条目和需要用户确认的问题。

## 3. 数据源与飞书 CLI 设计

### 3.1 认证与身份

默认使用 user 身份，因为用户自己的聊天、会议、云文档和知识库通常不是 bot 可见资源。

关键命令：

```bash
lark-cli config init --new
lark-cli auth login --scope "<required_scope>"
lark-cli auth status
```

权限策略：

- 首次授权只申请读权限。
- 权限不足时解析错误中的 `permission_violations` 和 `hint`，在 Hermes 中提示用户增量授权。
- 禁止在日志、前端、报告中输出 appSecret、accessToken。

### 3.2 聊天记录

优先用：

```bash
lark-cli im +messages-search --query "<keyword>" --start-time "<ts>" --end-time "<ts>" --format json
lark-cli im +chat-messages-list --chat-id "<chat_id>" --start-time "<ts>" --end-time "<ts>" --format json
lark-cli im +messages-mget --message-ids "<om_id,...>" --format json
```

检索策略：

- 第一阶段按关键词广搜：项目名、上周任务名、用户姓名、常见动作词。
- 第二阶段按重要 chat_id 拉取时间范围内消息。
- 第三阶段对候选消息做上下文扩展：线程回复、前后消息、附件。
- 消息信号权重：被回复/被 reaction/含 @ 用户/含“本周、完成、上线、延期、风险、待办”等词的权重更高。

输出字段：

- `source_type=im`
- `chat_id`
- `message_id`
- `sender`
- `send_time`
- `text`
- `thread_context`
- `attachments`
- `url`
- `confidence`

### 3.3 会议记录与会议纪要

优先用：

```bash
lark-cli vc +search --start-time "<ts>" --end-time "<ts>" --format json
lark-cli vc +notes --meeting-ids "<meeting_id,...>" --format json
lark-cli docs +fetch --doc "<doc_token>"
```

检索策略：

- 搜索本周已结束会议。
- 批量获取会议纪要、AI 总结、待办、章节、逐字稿链接。
- 默认读取会议总结和待办；只有证据不足时再读取逐字稿。
- 会议中出现的 action item 直接进入任务候选池，并记录会议来源。

输出字段：

- `source_type=meeting`
- `meeting_id`
- `title`
- `start_time`
- `participants`
- `summary`
- `todos`
- `doc_tokens`
- `url`
- `confidence`

### 3.4 云文档、Wiki 与知识库

优先用：

```bash
lark-cli docs +search --query "<keyword>" --format json
lark-cli docs +fetch --doc "<doc_token>"
lark-cli wiki spaces get_node --params '{"token":"<wiki_token>"}'
```

检索策略：

- 从上周周报和聊天/会议候选中抽取项目名、文档名、关键词。
- 搜索本周创建或更新的相关文档。
- 对 Wiki URL 先解析 `obj_token` 和 `obj_type`，再按文档类型读取。
- 抽取文档标题、更新时间、正文摘要、决策、待办、数据指标。

输出字段：

- `source_type=doc`
- `doc_token`
- `doc_type`
- `title`
- `updated_time`
- `url`
- `summary`
- `decisions`
- `todos`
- `confidence`

### 3.5 历史周报

输入类型：

- 本地目录：Markdown、DOCX、PDF、TXT。
- 飞书文档链接或文件夹链接。
- 飞书 Wiki 节点。

解析目标：

- 周报时间范围。
- 固定栏目结构。
- 上周完成事项。
- 上周下周计划。
- 未完成/阻塞/风险项。
- 项目和任务命名规范。
- 常用输出风格。

输出：

```json
{
  "report_profile": {
    "sections": ["本周重点", "项目进展", "风险与问题", "下周计划"],
    "tone": "简洁、结果导向",
    "task_patterns": ["项目 - 动作 - 结果 - 证据"],
    "owner_style": "姓名/团队"
  },
  "last_week_tasks": [
    {
      "task": "string",
      "expected_next_step": "string",
      "owner": "string",
      "status_last_week": "string"
    }
  ]
}
```

## 4. 核心处理管线

### 4.1 时间范围计算

默认范围：

- 开始：用户时区下本周一 00:00:00。
- 结束：当前时间。
- 当前工作区环境为 Asia/Shanghai 时，按中国时区计算。

支持用户手动改成自然周、工作周、任意时间段。

### 4.2 信息采集

流程：

1. 从历史周报抽取关键词和任务。
2. 生成检索计划：项目关键词、人员关键词、文档关键词、会议关键词。
3. 并行拉取 IM、会议、文档。
4. 对每个数据源分页拉全，保存原始 JSON。
5. 标准化成统一证据模型 `EvidenceItem`。

### 4.3 去重与关联

规则：

- 相同 URL/token/message_id 直接去重。
- 标题相似、时间接近、参会人/项目名相同的会议和文档做关联。
- 聊天中分享的文档链接与 docs fetch 结果做关联。
- 会议纪要中的待办与聊天里的推进消息做关联。

### 4.4 任务进展追踪

输入：

- 上周周报中的任务列表。
- 本周新增证据。
- 本周会议待办。
- 本周聊天中的承诺和交付。

状态分类：

- `done`：有明确完成/上线/交付/发布证据。
- `in_progress`：有推进但未完成。
- `blocked`：有阻塞、等待、依赖、风险证据。
- `deferred`：明确延期或排期变化。
- `dropped`：明确取消或不再做。
- `unknown`：无足够证据，需要用户确认。
- `new`：本周新增任务。

每个任务输出：

```json
{
  "task": "string",
  "status": "done|in_progress|blocked|deferred|dropped|unknown|new",
  "progress_summary": "string",
  "evidence_ids": ["string"],
  "owners": ["string"],
  "next_step": "string",
  "confidence": 0.0
}
```

### 4.5 周报生成

生成策略：

- 先按 `report_profile.sections` 生成结构。
- 若历史周报结构明确，严格复用栏目。
- 若没有历史结构，使用默认模板：
  - 本周概览
  - 重点进展
  - 项目/任务进展
  - 风险与阻塞
  - 下周计划
  - 需确认事项
- 每个重要结论必须能追溯到至少一个证据来源。
- 低置信度内容放入“需确认事项”，不混入确定性结论。

### 4.6 校验

自动校验：

- 是否覆盖上周所有未完成/下周计划项。
- 是否引用了本周范围外证据。
- 是否出现没有证据支撑的“已完成”。
- 是否遗漏会议纪要中的待办。
- 是否存在同一任务多个冲突状态。

用户校验：

- Hermes 前端展示“需确认事项”。
- 用户可以直接回复：“把 A 改成延期，B 删除，C 加到下周计划”。
- 二次生成时只重写受影响段落。

## 5. Skill 产物设计

建议 Skill 名称：`weekly-report-agent`

目录结构：

```text
weekly-report-agent/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── collect_lark_context.py
│   ├── parse_report_history.py
│   ├── build_task_timeline.py
│   ├── generate_report.py
│   └── validate_report.py
├── references/
│   ├── lark_data_sources.md
│   ├── report_schema.md
│   ├── hermes_flow.md
│   └── prompt_contracts.md
└── assets/
    └── default_report_template.md
```

### 5.1 SKILL.md 职责

只放核心工作流：

- 何时触发：用户要从飞书自动生成周报、跟踪任务、整理会议/聊天/文档。
- 必须先授权飞书 user 身份。
- 必须先读取历史周报或上周周报。
- 必须按本周一到当前时间采集。
- 必须保留证据链和低置信度提醒。
- 最终输出周报草稿，可选发布到飞书。

### 5.2 scripts 职责

`collect_lark_context.py`

- 入参：时间范围、关键词、数据源开关、输出目录。
- 调用 lark-cli。
- 输出标准化 `evidence.jsonl` 和原始响应。

`parse_report_history.py`

- 入参：历史周报路径或文档 token。
- 输出 `report_profile.json` 和 `last_week_tasks.json`。

`build_task_timeline.py`

- 入参：`evidence.jsonl`、`last_week_tasks.json`。
- 输出 `task_timeline.json`。

`generate_report.py`

- 入参：`task_timeline.json`、`report_profile.json`、默认模板。
- 输出 `weekly_report.md` 和 `report_meta.json`。

`validate_report.py`

- 入参：周报、证据、任务线。
- 输出校验报告和需确认事项。

### 5.3 Hermes Agent 集成

Hermes 前端需要暴露的 agent actions：

- `authorize_lark()`
- `select_report_history(input)`
- `analyze_report_profile()`
- `collect_week_context(time_range, sources)`
- `generate_weekly_report(options)`
- `revise_report(feedback)`
- `export_report(format)`
- `publish_to_lark_doc(folder_or_doc)`

状态模型：

```json
{
  "auth": {
    "status": "not_started|pending|authorized|permission_missing|failed",
    "missing_scopes": []
  },
  "history": {
    "input_type": "folder|doc|file|none",
    "status": "empty|parsed|failed"
  },
  "collection": {
    "range_start": "ISO8601",
    "range_end": "ISO8601",
    "sources": {
      "im": "pending|done|failed",
      "meeting": "pending|done|failed",
      "doc": "pending|done|failed"
    }
  },
  "report": {
    "status": "drafting|ready|needs_confirmation|published",
    "output_path": "string",
    "confidence": 0.0
  }
}
```

## 6. 数据模型

### 6.1 EvidenceItem

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

### 6.2 ReportDraft

```json
{
  "title": "string",
  "range": {
    "start": "ISO8601",
    "end": "ISO8601"
  },
  "sections": [
    {
      "heading": "string",
      "body_markdown": "string",
      "evidence_ids": ["string"]
    }
  ],
  "confirmations": [
    {
      "question": "string",
      "related_task": "string",
      "reason": "string"
    }
  ]
}
```

## 7. 默认周报模板

```markdown
# 本周周报（{{range_start}} - {{range_end}}）

## 本周概览

- {{summary_bullet_1}}
- {{summary_bullet_2}}
- {{summary_bullet_3}}

## 重点进展

| 事项 | 本周进展 | 状态 | 证据 |
| --- | --- | --- | --- |
| {{task}} | {{progress}} | {{status}} | {{source}} |

## 上周计划跟踪

| 上周事项 | 本周结果 | 下一步 |
| --- | --- | --- |
| {{task}} | {{result}} | {{next_step}} |

## 风险与阻塞

- {{risk}}

## 下周计划

- {{next_week_plan}}

## 需确认事项

- {{confirmation_question}}
```

## 8. 开发计划

### Phase 0：需求固化与技术 Spike（0.5-1 天）

产出：

- 确认 Hermes Agent 的 action 接口方式。
- 确认 skill 安装位置和触发方式。
- 用真实账号跑通 lark-cli user 授权。
- 用最小命令验证 IM、VC、Docs 三类读取。

验收：

- 能在本地拿到一条聊天、一条会议记录、一个文档内容。

### Phase 1：Skill 骨架与本地 CLI 管线（1-2 天）

任务：

- 创建 `weekly-report-agent` skill 目录。
- 编写 `SKILL.md`、`agents/openai.yaml`。
- 实现 `parse_report_history.py`。
- 实现时间范围计算。
- 定义 JSON schema 和输出目录规范。

验收：

- 输入上周周报，能抽取栏目和上周任务。
- 运行脚本能输出 `report_profile.json` 和 `last_week_tasks.json`。

### Phase 2：飞书数据采集（2-3 天）

任务：

- 实现 `collect_lark_context.py`。
- 接入 IM 搜索、会议搜索与纪要、文档搜索与读取。
- 做分页、重试、限流、原始响应归档。
- 实现权限不足提示。

验收：

- 给定本周时间范围和关键词，生成 `evidence.jsonl`。
- 每条 evidence 都有来源、时间、URL/token。

### Phase 3：任务跟踪与证据归并（2 天）

任务：

- 实现实体抽取：项目、任务、人员、日期。
- 实现上周任务与本周证据匹配。
- 实现状态分类和置信度。
- 实现去重和证据链。

验收：

- 上周周报中的任务都能出现在跟踪表。
- 每个任务状态都有解释和证据引用。

### Phase 4：周报生成与校验（1-2 天）

任务：

- 实现 `generate_report.py`。
- 实现历史格式复用。
- 实现默认模板。
- 实现 `validate_report.py`。
- 支持用户反馈后的局部重写。

验收：

- 生成一份结构完整、证据可追溯的 `weekly_report.md`。
- 低置信度内容进入“需确认事项”。

### Phase 5：Hermes 前端交互（2-3 天）

任务：

- 实现三步向导。
- 对接授权、历史周报输入、生成、预览、修订、导出。
- 展示采集进度和权限错误。
- 支持数据源开关和时间范围调整。

验收：

- 用户可以在 Hermes 中完成三步生成周报。
- 失败时能明确知道是授权、权限、数据源还是生成问题。

### Phase 6：发布与质量加固（1-2 天）

任务：

- 加入测试样例和模拟飞书响应。
- 加入端到端 dry run。
- 做日志脱敏。
- 做大数据量分页和重试测试。
- 编写最小使用说明，嵌入 Skill metadata，不额外堆 README。

验收：

- 真实账号完成一次完整周报生成。
- 不泄露 token/secret。
- 输出质量通过人工检查。

## 9. 风险与应对

### 权限不足

风险：用户授权 scope 不够，或应用后台未开通权限。

应对：

- 按数据源逐项检测。
- 在 Hermes 中展示缺失 scope。
- 支持增量授权。

### 聊天搜索召回不足

风险：全局消息搜索可能需要关键词，无法无差别拉取所有消息。

应对：

- 从上周周报、会议、文档抽关键词。
- 支持用户指定重点群聊。
- 对重点群聊使用 `chat-messages-list` 按时间拉取。

### 信息过载

风险：本周消息太多，生成结果噪声高。

应对：

- 先构建候选任务池。
- 对消息按任务相关性、互动强度、动作词打分。
- 只把高权重证据进入正文，低权重证据进入备查。

### 幻觉与错误归因

风险：模型把没有证据的事写成确定结论。

应对：

- 每个完成/风险/延期结论必须绑定 evidence。
- 没有证据的条目归入“需确认事项”。
- 校验器检查“无证据已完成”。

### 历史周报格式差异

风险：不同周报结构不一致。

应对：

- 优先上周格式。
- 历来周报只用于抽取风格和稳定栏目。
- 识别失败时回退默认模板。

## 10. MVP 范围

MVP 必做：

- 飞书 user 授权。
- 输入上周周报。
- 拉取本周会议纪要和相关文档。
- 基于关键词搜索聊天记录。
- 生成 Markdown 周报。
- 标注上周任务跟踪状态。
- 展示需确认事项。

MVP 暂缓：

- 自动发布到飞书文档。
- 对所有群聊无关键词全量扫描。
- 多人团队周报汇总。
- PPT/图表化输出。
- 自动发送给指定群。

## 11. 推荐实施顺序

1. 先做本地 skill 管线，不碰复杂前端。
2. 用真实上周周报验证任务抽取。
3. 接入飞书三类数据源：会议优先，其次文档，最后聊天。
4. 生成第一版 Markdown 周报。
5. 再接 Hermes 三步交互。
6. 最后做发布到飞书文档和质量加固。

