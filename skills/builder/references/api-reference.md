# Studio Chat Admin API Reference

All endpoints require authentication via `$STUDIO_API_TOKEN`. The `api.py` script handles auth automatically.
Replace `{pid}` with `$STUDIO_PROJECT_ID`.

---

## Knowledge Bases

### List KBs
`GET /projects/{pid}/knowledgebases`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `include_final_delete` | bool | false | Include permanently deleted KBs |
| `include_playbook_usage` | bool | false | Include which playbooks use each KB |

### Get KB
`GET /knowledgebases/{kb_id}`

Returns full content. Fields depend on type: `content` (TEXT/FILE), `faq_items` (FAQ), `snippet_items` (SNIPPETS).

### Create Text KB
`POST /projects/{pid}/knowledgebases/text`

```json
{
  "title": "string (required)",
  "content": "string (required)"
}
```

### Create FAQ KB
`POST /projects/{pid}/knowledgebases/faq`

```json
{
  "title": "string (required)",
  "faq_items": [
    {
      "questions": ["string", "string"],
      "answer": "string"
    }
  ]
}
```

### Create Snippets KB
`POST /projects/{pid}/knowledgebases/snippets`

```json
{
  "title": "string (required)",
  "snippet_items": [
    {
      "title": "string",
      "content": "string"
    }
  ]
}
```

### Update KB
`PATCH /knowledgebases/{kb_id}`

All fields optional — only include what you want to change:

```json
{
  "title": "string",
  "content": "string (TEXT only)",
  "faq_items": "array (FAQ only)",
  "snippet_items": "array (SNIPPETS only)",
  "instructions": "string (Markdown hints for LLM on how to use this KB)"
}
```

Sets status to EDITED. FILE KBs cannot be edited (400).

### Delete KB
`DELETE /knowledgebases/{kb_id}` — Soft delete (status → DELETED)

### Restore KB
`POST /knowledgebases/{kb_id}/restore` — Undo soft delete

### Rollback KB
`POST /knowledgebases/{kb_id}/rollback` — Revert to previous version (EDITED→ACTIVE, ADDED→removed)

---

## Playbooks

### List Playbooks
`GET /projects/{pid}/playbooks`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `include_deleted` | bool | false | Include soft-deleted playbooks |
| `include_versions` | bool | false | Include all versions |

### Get Playbook
`GET /playbooks/{playbook_id}`

Returns: `id`, `base_id`, `name`, `version_number`, `content` (instructions), `kb_ids`, `model`, `created_at`.

### Create Playbook
`POST /projects/{pid}/playbooks`

```json
{
  "name": "string (required)",
  "content": "string (required, instructions)",
  "kb_ids": ["kb_id_1", "kb_id_2"],
  "api_tools": ["tool_id_1"],
  "model": "string (optional, e.g. 'gpt-4o-mini')"
}
```

### Get Latest Playbook Version
`GET /playbooks/{base_id}/latest`

Returns the most recent version of a playbook by base_id.

### Update Latest Playbook Version (recommended)
`PATCH /playbooks/{base_id}/latest`

Always patches the most recent version. Creates a new version automatically. All fields optional:

```json
{
  "name": "string",
  "content": "string (instructions)",
  "kb_ids": ["kb_id_1", "kb_id_2"],
  "api_tools": ["tool_id_1"]
}
```

### Update Specific Playbook Version
`PATCH /playbooks/{playbook_id}`

Patches a specific version by ID (useful for intentional rollbacks). Same body as above.

### Delete Playbook
`DELETE /playbooks/{playbook_id}` — Soft delete

### Restore Playbook
`POST /playbooks/{playbook_id}/restore` — Undo soft delete

### Rollback Playbook
`POST /playbooks/{playbook_id}/rollback` — Revert to previous version

### Get Playbook History
`GET /playbooks/{playbook_id}/history`

Returns: array of `{id, version_number, name, created_at, updated_at}`

### Get Playbook Version
`GET /playbooks/{playbook_id}/versions/{version_number}`

Returns full playbook content for a historical version.

### Get Active Version
`GET /playbooks/{base_id}/active`

**Note: uses base_id.** Returns: `{base_id, version_number, playbook}`.

### Set Active Version
`PUT /playbooks/{base_id}/active`

**Note: uses base_id.**

```json
{
  "version_number": 3
}
```

### Remove Active Version
`DELETE /playbooks/{base_id}/active`

### Get Active Version History
`GET /playbooks/{base_id}/active/history`

**Note: uses base_id.** Returns deployment timeline: `{items: [{version_number, activated_at, activated_by}]}`

---

## Playbook Settings

### Get Settings
`GET /playbooks/{playbook_id}/settings`

Returns null if not configured.

### Update Settings
`PATCH /playbooks/{playbook_id}/settings`

All fields optional:

```json
{
  "is_disabled": "bool (kill switch)",
  "url_shortener_enabled": "bool",
  "url_shortener_regex": "string (regex to filter URLs)",
  "winback_enabled": "bool",
  "winback_delay_minutes": "int",
  "winback_include_tags": ["string"],
  "winback_exclude_tags": ["string"]
}
```

---

## Syncing (Re-indexing Knowledge Bases)

### Sync Project
`POST /projects/{pid}/train`

Returns: `{job_id: "string"}`. No request body needed.

### Check Sync Job
`GET /jobs/{job_id}`

Returns: `{status: "pending"|"running"|"completed"|"failed", progress: 0-100, error: "string|null"}`

### Check if Sync Needed
`GET /projects/{pid}`

Check `needs_retraining` field in response.

---

## Schedule

### Get Schedule
`GET /projects/{pid}/schedule`

### Create Schedule
`POST /projects/{pid}/schedule`

```json
{
  "name": "string (required)",
  "timezone": "string (required, e.g. 'America/New_York')",
  "enabled": true,
  "weekly_schedule": {
    "monday": {"start_time": "09:00", "end_time": "17:00", "is_available": true},
    "tuesday": {"start_time": "09:00", "end_time": "17:00", "is_available": true},
    "saturday": {"is_available": false}
  }
}
```

### Update Schedule
`PATCH /projects/{pid}/schedule`

All fields optional:

```json
{
  "name": "string",
  "timezone": "string",
  "enabled": "bool",
  "weekly_schedule": "object"
}
```

### Delete Schedule
`DELETE /projects/{pid}/schedule`

### Create Date Override
`POST /projects/{pid}/schedule/overrides`

```json
{
  "date": "2025-12-25",
  "label": "Christmas Day",
  "is_available": false,
  "override_schedule": {"start_time": "09:00", "end_time": "13:00"}
}
```

`override_schedule` required when `is_available=true`.

### Update Date Override
`PATCH /projects/{pid}/schedule/overrides/{override_id}`

### Delete Date Override
`DELETE /projects/{pid}/schedule/overrides/{override_id}`

---

## API Tools

### List API Tools
`GET /projects/{pid}/api-tools`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `include_playbook_usage` | bool | false | Show which playbooks use each tool |

### Get API Tool
`GET /projects/{pid}/api-tools/{tool_id}`

### Create API Tool
`POST /projects/{pid}/api-tools`

```json
{
  "name": "string (required, ^[a-zA-Z0-9_.-]{1,64}$, max 64 — NO spaces)",
  "description": "string (required) — what it does and when to use it",
  "url": "string (required) — URL template with {{ param }} placeholders (DOUBLE braces, Jinja)",
  "method": "GET|POST|PUT|PATCH|DELETE",
  "headers": {"X-API-Key": "..."},
  "parameters": [
    {"name": "order_id", "description": "What this URL param represents"}
  ],
  "body_type": "fields | json (default: fields)",
  "body_fields": [
    {"name": "subject", "type": "string|number|integer|boolean", "value": "{{ subject }} | literal | {{ context.path }}", "description": "LLM hint (templated values only)", "required": true}
  ],
  "body_json": "raw JSON template with {{ param }} (used when body_type=json)",
  "data_expiration_hours": "int|null (response cache TTL; 0=always re-fetch, null=never)",
  "response_jmespath": "string|null (optional JMESPath to trim the response before the LLM sees it)"
}
```

**URL templating uses `{{ param }}` — double braces (Jinja), not `{param}`.**

**`parameters`** = URL placeholders only. Each is `{name, description}` and is **always string** (no `type`/`required` — they're implicit). Every `{{ name }}` in `url` should have one; the `description` is what the LLM sees. A param named `context.<path>` (or `{{ context.<path> }}` written straight in the URL) is resolved from conversation context and is **not** asked to the LLM.

**`body_fields`** = the body for POST/PUT/PATCH (`body_type: "fields"`, the default). Per field, `value` is:
- a `{{ param }}` template → exposed to the LLM (typed by `type`, prompted by `description`),
- a literal (`"chatbot"`, `"false"`) → hardcoded, sent as-is (cast to `type`),
- a `{{ context.path }}` → resolved from context, not asked to the LLM.

**JSON body** (`body_type: "json"`): put the template string in `body_json`; `body_fields` then only supplies each param's `type`/`description`/`required`. A full-string `"{{ x }}"` keeps the typed value; embedded interpolates as string.

### Update API Tool
`PATCH /projects/{pid}/api-tools/{tool_id}`

All fields optional — same shape as create.

### Delete API Tool
`DELETE /projects/{pid}/api-tools/{tool_id}` — Soft delete

---

## Custom Toolkits & Tool Configurations (Pills)

Toolkit actions (Intercom Tickets/Conversations, Slack, Zendesk, Pylon, GU1) are wired into
instructions as **pills**: `{{ custom_tool: short_name }}`, each backed by a **tool
configuration** (one action with its params pinned / assistant-decided / context-driven). See
[`toolkit-actions.md`](./toolkit-actions.md) for the conceptual guide + full action catalog.
All of these accept the project (`sbs_`) token.

### List connected toolkits
`GET /projects/{pid}/custom-toolkits` — every toolkit with `is_connected`, `connected_account_id`.

### Toolkit connection status (one toolkit)
`GET /projects/{pid}/custom-toolkits/{toolkit_slug}/status`
Returns `{toolkit_slug, name, auth_type, is_connected, connected_account_id, tools}`. A toolkit's
actions can only be configured/called once `is_connected` is true; pass `connected_account_id`
as `toolkit_connection_id` when creating a config.

### A toolkit's actions + configurable schema
`GET /projects/{pid}/custom-toolkits/{toolkit_slug}/actions`
Returns `{toolkit_slug, is_connected, connected_account_id, actions: [{tool_slug, params[], metadata_sources[]}]}`.
Each param carries `key, label, type, required, llm_decideable, metadata_source, dynamic_children, options`.

### Dynamic metadata (options for select/dynamic params)
`GET /projects/{pid}/custom-toolkits/{toolkit_slug}/metadata/{metadata_type}`
`metadata_type` comes from the action's `metadata_sources`. Examples: Slack `channels`,
`members?channel=<id>`; Intercom `ticket_types`, `ticket_type_attributes?ticket_type_id=<id>`,
`settable_attributes`. Reads the stored credentials — needs the toolkit connected.

### List tool configurations (pills)
`GET /projects/{pid}/tool-configurations`
Each entry adds `in_use` (bool) + `usages` (`[{playbook_base_id, playbook_name, location, version}]`).
`location` is `"instructions"` or `"skill:<name>"`.

### Get / create / update / delete a pill
- `GET /projects/{pid}/tool-configurations/{config_id}` — with `in_use`/`usages`.
- `POST /projects/{pid}/tool-configurations` — body: `{tool_slug, toolkit_connection_id, display_name, config}`.
  `config` = `{params: {...}, dynamic_schema: [...]}`. Returns the generated `short_name`. Creating is direct (no approval).
- `PUT /projects/{pid}/tool-configurations/{config_id}` — body `{config}`. **In-use → 202 approval.**
- `DELETE /projects/{pid}/tool-configurations/{config_id}` — **in-use → 202 approval.**

> **Approval gating:** editing/deleting a pill referenced in the **active or latest** version of
> any playbook (instructions or skills) is queued for human approval (`202` + `approval_id`) for
> `sbs_` callers. Pills not yet referenced anywhere are updated/deleted directly. Check `in_use` first.

### Effective schema of a pill (per-attribute + problems)
`GET /projects/{pid}/tool-configurations/{config_id}/schema`
Merges the config with live service metadata: each attribute's `mode`
(`preconfigured` | `assistant_decides` | `empty` | `not_applicable`), `required`, `value`, `options`,
`condition`, plus detected `issues[]` and `metadata_available`.

### Audit every pill in the project
`GET /projects/{pid}/tool-configuration-audit`
Returns `{total_configs, misconfigured: [{id, short_name, display_name, tool_slug, toolkit_slug, in_use, issues[]}], skipped}`.
Surfaces required-but-empty attributes (a silent `400` at call time), in-use first. The Intercom
audit is conditional-aware (a `Submotivo X` is only required when the Motivo can be `X`).

### Macro → usage map
`GET /projects/{pid}/custom-tool-usages`
`{short_name: [{playbook_base_id, playbook_name, location, version}]}` across the active + latest
version of every playbook (instructions + skills). Ties a pill back to the skill/casuística using it.

---

## Project Settings

### Get Project
`GET /projects/{pid}`

Returns: `{id, name, account_id, needs_retraining}`

### Get Settings
`GET /projects/{pid}/settings`

Returns: `{project_id, settings: {personality_tone, user_enrichment_url}}`

### Update Settings
`PATCH /projects/{pid}/settings`

```json
{
  "personality_tone": "professional|friendly|casual|expert|playful",
  "user_enrichment_url": "string|null",
  "user_enrichment_headers": {"key": "value"}
}
```

---

## Alerts

### List Alerts
`GET /projects/{pid}/alerts`

Returns: `{items: [AlertDefinition], total: int}`

Each item includes `last_run_at` and `last_triggered_at` from the most recent runs.

### Create Alert
`POST /projects/{pid}/alerts`

```json
{
  "name": "string (required)",
  "instructions": "string (required — plain text for single condition, or JSON-encoded array for multi-condition)",
  "cron_expression": "string (required, minimum 10-min interval)",
  "playbook_base_ids": ["string (optional)"],
  "slack_channel": "string (optional)",
  "email_recipients": ["string (optional)"]
}
```

**Multi-condition format:** Pass `instructions` as a JSON-serialized array of strings: `"[\"Condition 1\", \"Condition 2\"]"`. Each condition gets an index (0, 1, ...) and is evaluated independently. The alert triggers if ANY condition is met.

Returns: `AlertDefinition` (201)

### Get Alert
`GET /alerts/{alert_id}`

Returns: `AlertDefinition` with `last_run_at`, `last_triggered_at`.

### Update Alert
`PATCH /alerts/{alert_id}`

All fields optional:

```json
{
  "name": "string",
  "instructions": "string",
  "cron_expression": "string",
  "playbook_base_ids": ["string"],
  "slack_channel": "string",
  "email_recipients": ["string"],
  "is_enabled": "bool"
}
```

### Delete Alert
`DELETE /alerts/{alert_id}` — Soft delete (204). Requires human user.

### Test Run Alert
`POST /alerts/{alert_id}/test`

Triggers manual execution using the cron interval as the evaluation window. Returns: `AlertRun` (202). Execution runs in background.

### List Alert Runs
`GET /alerts/{alert_id}/runs`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Results per page |
| `offset` | int | 0 | Skip N results |

Returns: `{items: [AlertRun], total: int}` (newest first)

### Get Alert Run
`GET /alerts/runs/{run_id}`

Returns: `AlertRun`

### AlertDefinition fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Alert ID |
| `project_id` | UUID | Project ID |
| `name` | string | Display name |
| `instructions` | string | Conditions to evaluate |
| `cron_expression` | string | Cron schedule |
| `playbook_base_ids` | string[] | Playbook filter |
| `slack_channel` | string | Slack channel name |
| `email_recipients` | string[] | Email addresses |
| `is_enabled` | bool | Whether alert is active |
| `last_run_at` | datetime | Last execution time |
| `last_triggered_at` | datetime | Last time conditions triggered |
| `created_at` | datetime | Created timestamp |
| `updated_at` | datetime | Updated timestamp |

### AlertRun fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Run ID |
| `alert_definition_id` | UUID | Parent alert ID |
| `status` | string | `pending`, `running`, `completed`, `failed` |
| `triggered` | bool | Whether conditions were triggered |
| `trigger_summary` | string | Summary of evaluation results |
| `window_start` | datetime | Evaluation window start |
| `window_end` | datetime | Evaluation window end |
| `sami_session_id` | UUID | SAMI session used for evaluation |
| `error_message` | string | Error details (on failure) |
| `execution_log` | array | Log entries: `[{ts, step, detail}]` |
| `started_at` | datetime | Execution start time |
| `completed_at` | datetime | Execution end time |
| `created_at` | datetime | Created timestamp |

---

## Monitors

Aggregate-style triggers (count of conversations matching a filter) evaluated on a cron
schedule. Read endpoints, mutations, preview, and test all accept `sbs_` keys directly.
Delete needs a human reviewer — `sbs_` callers get a **202** with an approval id.

### Preview Monitor
`POST /projects/{pid}/monitors/preview`

Live count for the form — 7 daily buckets + the lookback total.

```json
{
  "filter": {/* ConversationFilter or null */},
  "window_basis": "last_message | first_message",
  "playbook_base_id": "string (optional)",
  "window_minutes": "int (1..1440, required)"
}
```

Returns:

```json
{
  "daily_buckets": [{"bucket_start": "datetime", "count": 0}],
  "window_count": 0
}
```

### List Monitors
`GET /projects/{pid}/monitors`

Returns: `{items: [MonitorDefinition], total: int}`. Each item carries `last_run_at`,
`last_triggered_at`, and `recent_runs` (up to 24 sparkline points).

### Create Monitor
`POST /projects/{pid}/monitors`

```json
{
  "name": "string (required, ≤255)",
  "filter": {/* ConversationFilter or null */},
  "window_basis": "last_message (default) | first_message",
  "playbook_base_id": "string (required, ≤36)",
  "cron_expression": "string (default '*/10 * * * *', min 10-min interval)",
  "window_minutes": "int (1..1440, required)",
  "comparison_kind": "absolute (default) | baseline_relative",
  "threshold": "float (>0, required)",
  "baseline_hours": "int (1..168, required when baseline_relative)",
  "slack_channel": "string (optional)",
  "email_recipients": ["string (optional)"]
}
```

Returns: `MonitorDefinition` (201).

### Get Monitor
`GET /monitors/{monitor_id}`

Returns: `MonitorDefinition` with `last_run_at`, `last_triggered_at`, `recent_runs`.

### Update Monitor
`PATCH /monitors/{monitor_id}`

All fields optional:

```json
{
  "name": "string",
  "filter": {/* ConversationFilter — pass empty group to clear */},
  "window_basis": "last_message | first_message",
  "project_id": "string (re-parent — only meaningful with playbook_base_id)",
  "playbook_base_id": "string",
  "cron_expression": "string",
  "window_minutes": "int",
  "comparison_kind": "absolute | baseline_relative",
  "threshold": "float",
  "baseline_hours": "int",
  "slack_channel": "string",
  "email_recipients": ["string"],
  "is_enabled": "bool"
}
```

### Duplicate Monitor
`POST /monitors/{monitor_id}/duplicate`

Creates a disabled clone named `copy-{original.name}` under the same account. Returns:
`MonitorDefinition` (201).

### Delete Monitor
`DELETE /monitors/{monitor_id}` — 204 on success.

For sandbox (`sbs_`) callers the request is queued for human approval and returns:

```json
{
  "approval_id": "uuid",
  "status": "pending",
  "description": "Delete monitor {monitor_id}",
  "message": "Request queued for admin approval."
}
```
(HTTP 202.)

### Test Run Monitor
`POST /monitors/{monitor_id}/test`

Inline evaluation. Persists a `MonitorRun` and fires Slack/email if the rule triggers
(marked as a TEST run). Returns: `MonitorRun` (200).

### List Monitor Runs
`GET /monitors/{monitor_id}/runs`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Results per page |
| `offset` | int | 0 | Skip N results |

Returns: `{items: [MonitorRun], total: int}` (newest first).

### Get Monitor Run
`GET /monitors/runs/{run_id}`

Returns: `MonitorRun`.

### Conversation filter shape

The `filter` field is a compound AST. Three leaf types, all accept `negate: true`:

```jsonc
// Tag leaf
{ "type": "tag",     "value": "billing", "negate": false }

// Skill leaf — matches if the named skill was successfully invoked in the conversation
{ "type": "skill",   "value": "refund-process" }

// Handoff leaf — value is a bool
{ "type": "handoff", "value": true }

// Group — combines children with AND or OR (max depth 6, max 64 nodes)
{ "type": "group", "op": "and", "children": [/* leaves or nested groups */] }
```

`null` (or an empty group) matches every conversation in the window.

### MonitorDefinition fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Monitor ID |
| `project_id` | UUID | Project ID |
| `account_id` | UUID | Owning account |
| `name` | string | Display name |
| `filter` | object \| null | Conversation filter AST |
| `window_basis` | enum | `last_message` or `first_message` |
| `playbook_base_id` | UUID \| null | Assistant scope (version-stable) |
| `cron_expression` | string | Cron schedule |
| `window_minutes` | int | Lookback window in minutes |
| `comparison_kind` | enum | `absolute` or `baseline_relative` |
| `threshold` | float | Absolute count or baseline multiplier |
| `baseline_hours` | int \| null | Anchor for baseline-relative comparison |
| `slack_channel` | string \| null | Slack channel name |
| `email_recipients` | string[] \| null | Email addresses |
| `is_enabled` | bool | Whether the cron worker picks it up |
| `created_at` | datetime | Created timestamp |
| `updated_at` | datetime | Updated timestamp |
| `last_run_at` | datetime \| null | Most recent run |
| `last_triggered_at` | datetime \| null | Most recent triggered run |
| `recent_runs` | array | Up to 24 sparkline points (chronological) |

### MonitorRun fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Run ID |
| `monitor_id` | UUID | Parent monitor |
| `project_id` | UUID | Project ID |
| `account_id` | UUID | Owning account |
| `status` | enum | `pending`, `running`, `completed`, `failed` |
| `triggered` | bool \| null | Whether the rule fired |
| `current_value` | float \| null | The count over the lookback window |
| `threshold_value` | float \| null | The numeric threshold the count was compared to |
| `baseline_value` | float \| null | The baseline count (only for `baseline_relative`) |
| `summary` | string \| null | Human-readable result |
| `window_start` | datetime \| null | Lookback window start |
| `window_end` | datetime \| null | Lookback window end |
| `error_message` | string \| null | Error details (on failure) |
| `started_at` | datetime \| null | Execution start time |
| `completed_at` | datetime \| null | Execution end time |
| `created_at` | datetime | Created timestamp |

---

## Trending Topics

### Generate Analysis
`POST /projects/{pid}/conversations/insights/trending-topics/generate`

```json
{
  "playbook_base_ids": ["string (optional)"],
  "tags": ["string (optional)"],
  "time_window_days": "int (optional, 1-90, default 7)"
}
```

Returns: `{job_id: "string", status: "pending"}` (200). Returns 409 if analysis already exists for today with same config.

### Check Status
`GET /projects/{pid}/conversations/insights/trending-topics/status`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `playbook_base_ids` | string | — | Comma-separated playbook base IDs |
| `tags` | string | — | Comma-separated tags |
| `time_window_days` | int | 7 | Time window in days (1-90) |

Returns:

```json
{
  "status": "completed|running|pending|failed|not_found",
  "can_regenerate": "bool",
  "analysis": "TrendingTopicsAnalysisInfo (if completed)",
  "job": "TrendingTopicsJobInfo (if running/pending)",
  "error_message": "string (if failed)"
}
```

### Poll Job Progress
`GET /projects/{pid}/conversations/insights/trending-topics/job/{job_id}`

Returns:

```json
{
  "id": "UUID",
  "status": "pending|running|completed|failed",
  "progress": "0-100",
  "step": "fetching_data|identifying_topics|classifying|aggregating|saving",
  "progress_message": "string",
  "analysis_id": "UUID (when completed)",
  "error_message": "string (on failure)",
  "started_at": "datetime",
  "completed_at": "datetime"
}
```

### Get Analysis
`GET /projects/{pid}/conversations/insights/trending-topics/analysis/{analysis_id}`

Returns: `TrendingTopicsAnalysisInfo`

### List Past Analyses
`GET /projects/{pid}/conversations/insights/trending-topics/analyses`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Results per page |
| `offset` | int | 0 | Skip N results |

Returns: `{items: [TrendingTopicsAnalysisInfo], total: int}` (newest first)

### Export Analysis as PDF
`GET /projects/{pid}/conversations/insights/trending-topics/analysis/{analysis_id}/pdf`

Returns: PDF file (binary). Use `-o filename.pdf` with the API client.

### TrendingTopicsAnalysisInfo fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Analysis ID |
| `analysis_date` | string | Date (YYYY-MM-DD) |
| `topics` | array | Up to 5 trending topics |
| `total_conversations` | int | Total conversations in window |
| `conversations_analyzed` | int | Conversations with summaries |
| `created_at` | string | ISO timestamp |
| `start_date` | string | Window start (ISO) |
| `end_date` | string | Window end (ISO) |
| `time_window_days` | int | Window size in days |
| `playbook_base_ids` | string[] | Playbook filter used |

### TrendingTopic fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Topic name (2-4 words) |
| `description` | string | Topic description |
| `insight` | string | Detailed analysis |
| `example_question` | string | Representative question |
| `conversation_count` | int | Number of conversations |
| `percentage` | float | % of total conversations |
| `sentiment` | string | Dominant sentiment |
| `sentiment_breakdown` | object | `{positive, neutral, negative}` counts |
| `handoff_count` | int | Number of handoffs |
| `handoff_rate` | float | Handoff percentage |
| `conversation_ids` | string[] | Conversation IDs in topic |
| `example_conversations` | array | Up to 4 example conversations |

---

## KB Item Metadata

`GET /knowledgebases/{kb_id}/items/{item_id}`

Returns: `{item_id, item_type, title, url}`

Item types: `snippet`, `faq`, `notion`, `intercom`, `gdrive`.

---

## KB Item Correction Notes

Correction notes are annotations attached to individual KB items. They override the original content at query time — no syncing needed. Notes take effect immediately.

### List all notes in a project

`GET /projects/{project_id}/notes`

Returns: `{project_id, items_with_notes: [{knowledgebase_id, knowledgebase_title, item_id, item_title, notes: [{text, created_at}]}], total}`

### List all items with notes in a KB

`GET /knowledgebases/{kb_id}/notes`

Returns: `{knowledgebase_id, items_with_notes: [{item_id, title, notes: [{text, created_at}]}], total}`

### Get notes for a specific item

`GET /knowledgebases/{kb_id}/items/{item_id}/notes`

Returns: `{item_id, title, notes: [{text, created_at}]}`

### Add a note to an item

`POST /knowledgebases/{kb_id}/items/{item_id}/notes`

```json
{"note": "The correct minimum order is $7500, not $5000."}
```

### Remove a note from an item

`DELETE /knowledgebases/{kb_id}/items/{item_id}/notes`

```json
{"note": "The correct minimum order is $7500, not $5000."}
```

### Edit a note on an item

`PUT /knowledgebases/{kb_id}/items/{item_id}/notes`

```json
{"old_note": "old text to find", "new_note": "replacement text"}
```

---

## Skills

Skills are sub-instructions loaded on-demand for context window management. They are versioned with the playbook.

### List skills for a playbook

`GET /projects/{project_id}/playbooks/{base_id}/skills`

Returns all skills for the latest version of the playbook, ordered by display order.

### Create a skill

`POST /projects/{project_id}/playbooks/{base_id}/skills`

Creates a new playbook version with the skill added.

```json
{
  "name": "refund-process",
  "description": "Handle refund requests for orders",
  "trigger": "Handle refund requests for orders",
  "content": "## Refund Process\n1. Ask for order number\n2. Verify return window",
  "is_active": true,
  "order": 0
}
```

### Update a skill

`PATCH /projects/{project_id}/playbooks/{base_id}/skills/{skill_name}`

Creates a new playbook version with the skill modified. All fields optional.

```json
{
  "description": "Updated description",
  "content": "Updated instructions..."
}
```

### Delete a skill

`DELETE /projects/{project_id}/playbooks/{base_id}/skills/{skill_name}`

Creates a new playbook version without the skill.

### Reorder skills

`PUT /projects/{project_id}/playbooks/{base_id}/skills/reorder`

Creates a new playbook version with updated order. Body is an ordered array of skill names.

```json
["password-reset", "refund-process", "billing-inquiry"]
```

### Conditional enablement (`enable_condition`)

Optional on create/update. Gates an `is_active` skill on the live conversation
context (same dict the `{{ context: path }}` pill reads), re-evaluated every
turn. Non-matching skills are excluded from the agent entirely (not listed, not
loadable; a `{{ skill: name }}` reference gets a static "disabled by condition"
bounce from `load_skill`). `null` / omitted = unconditional.

```json
{
  "name": "oferta-vip-arg",
  "description": "Aplicar la promo 50% OFF cuando el cliente pregunta precios",
  "trigger": "El cliente pregunta precios o totales",
  "content": "## Promo activa...",
  "is_active": true,
  "enable_condition": {
    "op": "and",
    "clauses": [
      {"path": "contact.country", "operator": "eq", "value": "ARG"},
      {"path": "contact.vip", "operator": "eq", "value": true}
    ]
  }
}
```

- Groups (`and`/`or`, optional `negate`) nest one level; max 16 clauses.
- Operators: `eq`, `neq`, `in`, `not_in` (array values), `contains`, `exists`,
  `not_exists` (no value), `gt`, `gte`, `lt`, `lte` (numeric).
- Lax equality for stringly-typed payloads: `true` matches `"true"`, `5`
  matches `"5"`; strings are case-sensitive; booleans never equal numbers.
- **Fail-closed**: a missing key / empty string / empty context makes every
  clause false except `not_exists` (including `neq`). Empty context = all
  conditional skills off until the attribute arrives on a later turn.
- On PATCH: omitted = keep the stored condition, explicit `null` = clear it.
  Full-playbook `skills` snapshots also preserve stored conditions for items
  that omit the field.
- Validation errors return 422 (bad operator/path, wrong value arity, depth > 2,
  more than 16 clauses).

### Dry-run a condition

`POST /projects/{project_id}/playbooks/{base_id}/skills/condition-check`

Read-only (no version created; sandbox keys don't queue an approval). Validates
the condition and optionally evaluates it — against a sample `context`, or
against a real conversation's latest context snapshot via `conversation_id`
(takes precedence; 404 if the conversation doesn't exist).

```json
{"condition": {"op": "and", "clauses": [{"path": "campaign", "operator": "eq", "value": "active"}]}, "conversation_id": "abc123"}
```

Response:

```json
{"valid": true, "rendered": "campaign == \"active\"", "result": true, "context_found": true, "context": {"campaign": "active"}}
```

`valid: false` + `error` for malformed conditions; `context_found: false` when
the conversation predates context snapshots (the condition would fail closed).

---

### Supported KB types

All item types support notes: FAQ (`faq_items[].id`), Snippets (`snippet_items[].id`), Notion (`notion_items[].id`), Intercom (`intercom_items[].id`), GDrive (`gdrive_items[].id`).

### How notes work

- Notes are injected into RAG search results at query time (not indexed)
- No syncing required — changes are immediate
- KB status is NOT changed when adding/removing notes
- Notes override the original content for the LLM

---

## Approvals

Queued sandbox writes. When a write returns **202** with an `approval_id`, a human admin
has to approve it from the Approvals panel before it executes.

### Describe a queued change
`PATCH /approvals/{approval_id}/description`

```json
{"description": "What is changing and why, in plain language for the reviewer."}
```

Returns the full approval. Only PENDING approvals accept a description (409 once
reviewed). Always call this right after receiving a 202 — the panel shows your text as
the primary explanation of the request.

The `description` is free text (stored verbatim, max 20000 chars). For edits to existing
text, embed one or more **diff blocks** and the panel renders them as side-by-side
before/after; everything outside the blocks renders as normal text:

```
[[diff]]
[[before]]
current text, verbatim
[[after]]
new text, verbatim
[[/diff]]
```

Each marker must be on its own line. `[[before]]`/`[[after]]` are required (leave
`[[before]]` empty for an addition, `[[after]]` empty for a deletion). See the
"Show the actual edit with a diff block" section of SKILL.md for guidance.

### List / get approvals
`GET /approvals?status=pending` · `GET /approvals/{approval_id}`

Useful to check whether a queued change was approved (`status` becomes
`executed`/`failed`) before building on top of it.
