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

Toolkit actions (Intercom Tickets, Slack, Zendesk, Pylon, …) are wired into instructions/skills
as **pills**: `{{ custom_tool: short_name }}`. Each pill points at a **tool configuration** — a saved
setup of one action (e.g. one Intercom ticket type) where each attribute is either *pre-configured*
(a fixed value), left for the *assistant to decide* at runtime, or *empty*. A required attribute left
empty silently fails at call time (e.g. Intercom returns `400 Missing required attributes`). These
endpoints let you **discover, audit, and edit** those configs by API.

All accept the project API token (`X-API-Key: sbs_…`).

### List connected toolkits
`GET /projects/{pid}/custom-toolkits` → every registered toolkit with connection status
(`is_connected`, `connected_account_id`).

### Is a specific toolkit connected? (prerequisite to use its actions)
`GET /projects/{pid}/custom-toolkits/{toolkit_slug}/status`

A toolkit's actions can only be configured/called once it is **connected**. Check first:

```json
{"toolkit_slug": "INTERCOM_TICKETS", "name": "Intercom Tickets", "auth_type": "api_key",
 "is_connected": true, "connected_account_id": "conn-abc123",
 "tools": ["INTERCOM_TICKETS_CREATE_TICKET", "INTERCOM_TICKETS_GET_TICKET", "INTERCOM_TICKETS_FIND_TICKETS"]}
```

If `is_connected` is `false`, **ask the user to connect the toolkit** (it needs credentials/OAuth) and
stop — you cannot create a tool configuration without `connected_account_id`. Use it as the
`toolkit_connection_id` when creating a config.

### List a toolkit's actions and their configurable schema
`GET /projects/{pid}/custom-toolkits/{toolkit_slug}/actions`

Returns the connection status plus each action (`tool_slug`) with the fields you can configure:

```json
{
  "toolkit_slug": "INTERCOM_TICKETS",
  "is_connected": true,
  "connected_account_id": "conn-abc123",
  "actions": [
    {
      "tool_slug": "INTERCOM_TICKETS_CREATE_TICKET",
      "params": [
        {"key": "ticket_type_id", "label": "Ticket Type", "type": "select", "required": true,
         "llm_decideable": false, "metadata_source": "ticket_types",
         "dynamic_children": {"metadata_source": "ticket_type_attributes", "parent_key_param": "ticket_type_id"}},
        {"key": "contact_email", "label": "Contact Email", "type": "text", "required": true}
      ],
      "metadata_sources": ["ticket_types", "ticket_type_attributes"]
    }
  ]
}
```

### Fetch dynamic options (attributes, types, values)
`GET /projects/{pid}/custom-toolkits/{toolkit_slug}/metadata/{metadata_type}`

`metadata_type` comes from `metadata_sources` above. For Intercom Tickets:
- `ticket_types` → available ticket types (feeds `ticket_type_id`).
- `ticket_type_attributes?ticket_type_id=…` → every attribute of a type with `data_type`, `options`,
  `required` (`required_to_create`), and visibility flags. This is how you learn the valid Motivo /
  Submotivo values and which are required.

### List tool configurations (pills) — with usage
`GET /projects/{pid}/tool-configurations`

Each entry adds `in_use` + `usages` (where the `{{ custom_tool: short_name }}` macro appears):

```json
{
  "id": "…", "short_name": "create_ticket_824ce", "display_name": "Create Ticket",
  "tool_slug": "INTERCOM_TICKETS_CREATE_TICKET", "toolkit_connection_id": "…", "toolkit_slug": "INTERCOM_TICKETS",
  "config": {"params": {"ticket_type_id": "…"}, "dynamic_schema": [{"key": "Motivo", "type": "select", "options": [...]}]},
  "in_use": true,
  "usages": [{"playbook_base_id": "…", "playbook_name": "Joaquina", "location": "skill:retiros", "version": "active+latest"}]
}
```

`config.params` = pre-configured/fixed values (also holds `ticket_type_id`, `contact_email`, and meta
keys like `__link_conversation__`). `config.dynamic_schema` = the attributes the assistant decides
(each `{key, label, type, data_type, options, condition, …}`).

### Get one tool configuration
`GET /projects/{pid}/tool-configurations/{config_id}` → same shape, with `in_use`/`usages`.

### Effective schema for a config (per-attribute + problems)
`GET /projects/{pid}/tool-configurations/{config_id}/schema`

Merges the stored config with **live service metadata** so you see each attribute's `mode`
(`assistant_decides` | `preconfigured` | `empty`), whether the service `required`s it, its `options`,
any `condition`, plus a list of detected `issues`:

```json
{
  "id": "…", "short_name": "create_ticket_824ce", "tool_slug": "INTERCOM_TICKETS_CREATE_TICKET",
  "toolkit_slug": "INTERCOM_TICKETS",
  "attributes": [
    {"key": "Motivo", "label": "Motivo", "type": "list", "required": true, "mode": "empty",
     "value": null, "options": [...], "condition": null,
     "problem": "Required attribute 'Motivo' is left empty — Intercom will reject every create."}
  ],
  "issues": ["Required attribute 'Motivo' is left empty — …"],
  "metadata_available": true
}
```

### Audit every config in the project
`GET /projects/{pid}/tool-configuration-audit`

Scans all pills and returns the misconfigured ones (in-use first) — the fastest way to find pills that
will 400 at runtime:

```json
{"total_configs": 38,
 "misconfigured": [
   {"id": "…", "short_name": "create_ticket_824ce", "display_name": "Create Ticket",
    "tool_slug": "INTERCOM_TICKETS_CREATE_TICKET", "toolkit_slug": "INTERCOM_TICKETS", "in_use": true,
    "issues": ["Required attribute 'Motivo' is left empty — …"]}],
 "skipped": []}
```

`skipped` lists config IDs whose toolkit isn't connected or whose live metadata couldn't be fetched.

### Map macros → configs (where each pill is used)
`GET /projects/{pid}/custom-tool-usages` → `{short_name: [{playbook_base_id, playbook_name, location, version}]}`
across the **active and latest** version of every playbook (instructions + skills). Use it to tie a pill
like `create_ticket_824ce` back to the skill/casuística that references it.

### Create a tool configuration (pill)
`POST /projects/{pid}/tool-configurations`

```json
{
  "toolkit_connection_id": "string (required) — from the connected toolkit",
  "tool_slug": "INTERCOM_TICKETS_CREATE_TICKET",
  "display_name": "Create Ticket — Retiros Ecuador",
  "config": {
    "params": {"ticket_type_id": "…", "contact_email": "{{ deps.email }}"},
    "dynamic_schema": [
      {"key": "Motivo", "type": "select", "data_type": "list", "options": [{"id": "…", "name": "…"}]},
      {"key": "Submotivo Retiros Ecuador", "type": "select", "data_type": "list",
       "condition": {"parent_key": "Motivo", "value": "Retiros"}, "options": [...]}
    ]
  }
}
```

Returns the config with its generated `short_name` (`{slug(display_name)}_{last5(config_id)}`). Creating a
pill has **no effect** until its macro is added to instructions, so this executes directly.

### Update / Delete a tool configuration
`PUT /projects/{pid}/tool-configurations/{config_id}` (body: `{"config": {…}}`) ·
`DELETE /projects/{pid}/tool-configurations/{config_id}`

> **Approval gating:** if the pill is referenced in the **active or latest** version of any playbook
> (instructions or skills), an edit/delete via a project (`sbs_`) token reaches live behavior and is
> **queued for human approval** — the call returns **202** with `{approval_id, status: "pending"}`. Pills
> not yet wired into any instruction are updated/deleted directly. Check `in_use` first (list/get) to know
> which path you'll hit.

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
