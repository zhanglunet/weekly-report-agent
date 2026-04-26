# Lark Data Sources

## Identity

Use user identity for weekly report generation. Personal chats, meetings, docs, and Wiki resources are usually visible only to the authorized user.

## Authentication

Start authorization with read scopes only. If a command fails with missing scopes, surface the missing scope list to Hermes and ask the user to re-authorize.

Never display app secrets, access tokens, refresh tokens, or raw credential files.

## Chat

Preferred commands:

```bash
lark-cli im +messages-search --query "<keyword>" --start-time "<epoch>" --end-time "<epoch>" --format json
lark-cli im +chat-messages-list --chat-id "<chat_id>" --start-time "<epoch>" --end-time "<epoch>" --format json
lark-cli im +messages-mget --message-ids "<ids>" --format json
```

Search keywords should come from:

- Previous report tasks.
- Project names.
- People names.
- Meeting/doc titles.
- Action terms such as 完成, 上线, 发布, 阻塞, 延期, 待办, 跟进.

## Meetings

Preferred commands:

```bash
lark-cli vc +search --start-time "<epoch>" --end-time "<epoch>" --format json
lark-cli vc +notes --meeting-ids "<ids>" --format json
```

Fetch notes summaries and todos first. Read transcripts only when summaries are insufficient.

## Docs and Wiki

Preferred commands:

```bash
lark-cli docs +search --query "<keyword>" --format json
lark-cli docs +fetch --doc "<doc_token>"
lark-cli wiki spaces get_node --params '{"token":"<wiki_token>"}'
```

Wiki URLs must be resolved to their underlying object token and object type before fetching.

## Collection Rules

- Keep raw command outputs under `.weekly-report-work/raw`.
- Normalize all sources into `EvidenceItem`.
- Preserve source IDs, URLs, timestamps, and raw paths.
- Paginate when a response has a next page token.
- Use dry-run mode when Lark is not authorized.

