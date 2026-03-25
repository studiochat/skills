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

### Update Playbook
`PATCH /playbooks/{playbook_id}`

Creates a new version automatically. All fields optional:

```json
{
  "name": "string",
  "content": "string (instructions)",
  "kb_ids": ["kb_id_1", "kb_id_2"],
  "api_tools": ["tool_id_1"]
}
```

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

## Training

### Train Project
`POST /projects/{pid}/train`

Returns: `{job_id: "string"}`. No request body needed.

### Check Training Job
`GET /jobs/{job_id}`

Returns: `{status: "pending"|"running"|"completed"|"failed", progress: 0-100, error: "string|null"}`

### Check if Training Needed
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
  "name": "string (required)",
  "description": "string (required)",
  "url": "string (required)",
  "method": "GET|POST|PUT|PATCH|DELETE",
  "headers": {"key": "value"},
  "parameters": [
    {
      "name": "string",
      "type": "string",
      "description": "string",
      "required": true
    }
  ],
  "data_expiration_hours": "int|null (cache TTL, null=never)"
}
```

### Update API Tool
`PATCH /projects/{pid}/api-tools/{tool_id}`

All fields optional.

### Delete API Tool
`DELETE /projects/{pid}/api-tools/{tool_id}` — Soft delete

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

## KB Item Metadata

`GET /knowledgebases/{kb_id}/items/{item_id}`

Returns: `{item_id, item_type, title, url}`

Item types: `snippet`, `faq`, `notion`, `intercom`, `gdrive`.

---

## KB Item Correction Notes

Correction notes are annotations attached to individual KB items. They override the original content at query time — no retraining needed. Notes take effect immediately.

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

### Replace all notes on an item (batch)

`PATCH /knowledgebases/{kb_id}/items/{item_id}/notes`

```json
{"action": "set", "notes": ["First correction", "Second correction"]}
```

To clear all notes: `{"action": "set", "notes": []}`.

### Supported KB types

All item types support notes: FAQ (`faq_items[].id`), Snippets (`snippet_items[].id`), Notion (`notion_items[].id`), Intercom (`intercom_items[].id`), GDrive (`gdrive_items[].id`).

### How notes work

- Notes are injected into RAG search results at query time (not indexed)
- No retraining required — changes are immediate
- KB status is NOT changed when adding/removing notes
- Notes override the original content for the LLM
