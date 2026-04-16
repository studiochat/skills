---
name: studio-chat-admin
description: >
  Manage Studio Chat project configuration — knowledge bases, playbooks, syncing, schedule,
  API tools, alerts, and trending topics. Use when asked to create, update, delete, or inspect
  KBs, playbooks, office hours, alerts, or any project settings. Also use to generate and browse
  trending topics analyses. Covers all CRUD operations via the Studio Chat API.
---

# Studio Chat Admin

Read and write Studio Chat project configuration using the API. All calls are authenticated automatically via environment variables. The API base URL (`https://api.studiochat.io`) is hardcoded in the scripts.

**IMPORTANT: Always confirm before creating or modifying.** Never create knowledge bases,
playbooks, API tools, or trigger syncing without explicit user confirmation. Show what
you're about to do and wait for approval before executing any write operation.

## Key Terminology

**Assistants and playbooks are the same concept.** In the API, the term "playbook" is used
everywhere — but users refer to them as "assistants," "bots," or "agents." When the user
mentions any of these, they mean a playbook.

## Setup

Set the following environment variables before using the scripts:

```bash
export STUDIO_API_TOKEN="sbs_your_api_key_here"
export STUDIO_PROJECT_ID="your-project-uuid"
```

API keys are available by request from the Studio Chat team at hey@studiochat.io.

## API Client

```bash
python3 scripts/api.py <path> [-X METHOD] [--body JSON] [--params k=v] [-o file]
```

Supports GET, POST, PUT, PATCH, DELETE. Auth injected from env vars.

## Full API Reference

See [references/api-reference.md](references/api-reference.md) for complete endpoint specs.

---

## Knowledge Bases

KBs are the information the assistant searches to answer customers. Types: TEXT, FAQ, SNIPPETS, FILE.

### List KBs

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/knowledgebases" \
  --params include_playbook_usage=true
```

### Get KB content

```bash
python3 scripts/api.py "/knowledgebases/KB_ID"
```

### Create Text KB

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/knowledgebases/text" \
  -X POST --body '{
    "title": "Product FAQ",
    "content": "Your plain text content here..."
  }'
```

### Create FAQ KB

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/knowledgebases/faq" \
  -X POST --body '{
    "title": "Common Questions",
    "faq_items": [
      {"questions": ["How do I reset my password?"], "answer": "Go to Settings > Security > Reset Password."},
      {"questions": ["What are your hours?"], "answer": "Monday-Friday 9am-5pm EST."}
    ]
  }'
```

### Create Snippets KB (product catalog)

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/knowledgebases/snippets" \
  -X POST --body '{
    "title": "Product Catalog",
    "snippet_items": [
      {"title": "Basic Plan", "content": "Price: $10/mo. Includes 100 conversations."},
      {"title": "Pro Plan", "content": "Price: $50/mo. Includes 1000 conversations."}
    ]
  }'
```

### Update KB

```bash
python3 scripts/api.py "/knowledgebases/KB_ID" \
  -X PATCH --body '{"content": "New text content..."}'
```

### Delete / Restore KB

```bash
python3 scripts/api.py "/knowledgebases/KB_ID" -X DELETE
python3 scripts/api.py "/knowledgebases/KB_ID/restore" -X POST
```

**After KB changes, sync the project to apply them.**

### Correction Notes

Add correction notes to individual KB items to override their content at query time. Notes take effect immediately — no syncing required.

**List all notes in the project:**

```bash
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/notes"
```

**List all items with notes** in a specific KB:

```bash
python3 scripts/api.py "/knowledgebases/KB_ID/notes"
```

**Get notes for a specific item:**

```bash
python3 scripts/api.py "/knowledgebases/KB_ID/items/ITEM_ID/notes"
```

**Add a note** to an item:

```bash
python3 scripts/api.py "/knowledgebases/KB_ID/items/ITEM_ID/notes" -X POST --body '{"note": "The correct answer is X, not Y."}'
```

**Remove a note** from an item:

```bash
python3 scripts/api.py "/knowledgebases/KB_ID/items/ITEM_ID/notes" -X DELETE --body '{"note": "The correct answer is X, not Y."}'
```

**Edit a note** on an item:

```bash
python3 scripts/api.py "/knowledgebases/KB_ID/items/ITEM_ID/notes" -X PUT --body '{"old_note": "old text", "new_note": "corrected text"}'
```

Notes override the original content for the LLM. Use them to correct outdated information without editing the source. To clear all notes, remove them one by one.

---

## Playbooks

Playbooks define how the AI assistant behaves — instructions, linked KBs, and model.

### List playbooks

```bash
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/playbooks"
```

### Create playbook

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/playbooks" \
  -X POST --body '{
    "name": "Support Bot",
    "content": "You are a helpful support assistant.\n\nRules:\n- Be concise and friendly\n- Escalate billing disputes",
    "kb_ids": ["KB_ID_1", "KB_ID_2"]
  }'
```

### Get latest playbook version

```bash
python3 scripts/api.py "/playbooks/BASE_ID/latest"
```

### Update playbook (creates new version automatically)

**IMPORTANT:** Before updating instructions, ALWAYS fetch the latest version first using
`GET /playbooks/BASE_ID/latest`, even if you already have the instructions in your context.
The playbook may have been modified by another process since you last read it. Read the
latest content, apply your changes on top of it, then send the PATCH.

```bash
# 1. Fetch the current latest version
python3 scripts/api.py "/playbooks/BASE_ID/latest"

# 2. Apply your changes on top of the fetched content and patch
python3 scripts/api.py "/playbooks/BASE_ID/latest" \
  -X PATCH --body '{"content": "Updated instructions based on latest..."}'
```

### Version management

```bash
# Get version history
python3 scripts/api.py "/playbooks/PLAYBOOK_ID/history"

# Get currently active version (uses base_id)
python3 scripts/api.py "/playbooks/BASE_ID/active"

# Set active version
python3 scripts/api.py "/playbooks/BASE_ID/active" \
  -X PUT --body '{"version_number": 3}'
```

### Playbook settings

```bash
# Enable/disable playbook (kill switch)
python3 scripts/api.py "/playbooks/PLAYBOOK_ID/settings" \
  -X PATCH --body '{"is_disabled": true}'

# Configure winback
python3 scripts/api.py "/playbooks/PLAYBOOK_ID/settings" \
  -X PATCH --body '{"winback_enabled": true, "winback_delay_minutes": 30}'
```

---

## Syncing

After modifying KBs, the project must be synced to apply changes. This re-indexes the knowledge base sources.

```bash
# Sync the project (re-index knowledge bases)
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/train" -X POST

# Check sync status
python3 scripts/api.py "/jobs/JOB_ID"
```

---

## Schedule (Office Hours)

```bash
# Get current schedule
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/schedule"

# Create schedule
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/schedule" \
  -X POST --body '{
    "name": "Business Hours",
    "timezone": "America/New_York",
    "enabled": true,
    "weekly_schedule": {
      "monday": {"start_time": "09:00", "end_time": "17:00", "is_available": true},
      "saturday": {"is_available": false},
      "sunday": {"is_available": false}
    }
  }'

# Add a holiday override
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/schedule/overrides" \
  -X POST --body '{"date": "2025-12-25", "label": "Christmas Day", "is_available": false}'
```

---

## Skills

Skills are sub-instructions loaded on-demand during conversations. Only skill metadata (name + description) goes in the system prompt; the full content is loaded via a `load_skill` tool call when the conversation matches the skill's description. This keeps the base context window small.

Skills are versioned with the playbook — adding, editing, or deleting a skill creates a new playbook version.

### List skills

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/playbooks/BASE_ID/skills"
```

### Create skill

Creates a new playbook version with the skill added.

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/playbooks/BASE_ID/skills" \
  -X POST --body '{
    "name": "refund-process",
    "description": "Handle refund requests for orders",
    "trigger": "Handle refund requests for orders",
    "content": "## Refund Process\n\n1. Ask for order number\n2. Search in {{ kb(KB_ID) }} for the order\n3. Process refund within 48 hours\n4. Use {{ tool(TOOL_ID) }} to issue the refund",
    "is_active": true,
    "order": 0
  }'
```

### Update skill

Creates a new playbook version with the skill modified. All fields are optional.

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/playbooks/BASE_ID/skills/refund-process" \
  -X PATCH --body '{"description": "Updated description", "content": "Updated instructions..."}'
```

### Delete skill

Creates a new playbook version without the skill.

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/playbooks/BASE_ID/skills/refund-process" \
  -X DELETE
```

### Reorder skills

Creates a new playbook version with updated display order. Body is an ordered array of skill names.

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/playbooks/BASE_ID/skills/reorder" \
  -X PUT --body '["password-reset", "refund-process", "billing-inquiry"]'
```

### Skill content supports templates

Skill instructions support the same template macros as playbook instructions:
- `{{ kb(KB_ID) }}` — Reference a knowledge base for search
- `{{ tool(TOOL_ID) }}` — Reference an API tool
- `{{ integration(SLUG) }}` — Reference a Composio/custom integration
- `{{ composio_tool: TOOL_NAME | Display Name }}` — Reference a specific integration tool
- `{{ custom_tool: short_name }}` — Reference a configured custom tool

The referenced tools/KBs are registered in the agent even before the skill is loaded, ensuring they're available when needed.

---

## Example Blocks

Example blocks are reference conversations that show the assistant HOW to communicate — tone, style, personality, containment strategies, and approach. They are inline in the instructions or skills via `{{ examples: BLOCK_ID }}` template macros.

When compiled, examples are injected into the prompt as `<example id="xxxxx">` tags. The LLM is instructed to follow the style of matching examples and reference them in its response with `<<example_id>>` markers.

### How examples work

1. **Create an example block** — a block holds one or more reference conversations
2. **Reference it in instructions or skills** — using `{{ examples: BLOCK_ID }}`
3. **At runtime** — the assistant sees the examples, adopts the style, and cites which example it followed

Example blocks are **immutable** — editing creates a new block (new ID), and saving the playbook creates a new version pointing to the new block. Previous versions retain their original examples for rollback.

### Create example block

```bash
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$API_BASE/projects/$STUDIO_PROJECT_ID/example-blocks" \
  -d '{
    "examples": [
      {
        "turns": [
          {"role": "user", "content": "Hola, necesito ayuda"},
          {"role": "assistant", "content": "¡Hola! Entiendo que necesitás ayuda. Estoy acá para vos. ¿En qué te puedo ayudar?"}
        ]
      },
      {
        "turns": [
          {"role": "user", "content": "Me cobraron de más"},
          {"role": "assistant", "content": "Lamento mucho eso. Voy a revisar tu caso ahora mismo. ¿Me pasás tu número de cuenta para verificar?"}
        ]
      }
    ]
  }'
```

Returns the block with its `id`. Use this ID in the `{{ examples: BLOCK_ID }}` macro.

### List example blocks

```bash
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  "$API_BASE/projects/$STUDIO_PROJECT_ID/example-blocks"
```

### Get example block

```bash
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  "$API_BASE/projects/$STUDIO_PROJECT_ID/example-blocks/BLOCK_ID"
```

### Update example block

```bash
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  "$API_BASE/projects/$STUDIO_PROJECT_ID/example-blocks/BLOCK_ID" \
  -H "Content-Type: application/json" \
  -X PATCH -d '{
    "examples": [
      {
        "turns": [
          {"role": "user", "content": "Updated user message"},
          {"role": "assistant", "content": "Updated assistant response"}
        ]
      }
    ]
  }'
```

### Delete example block

```bash
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  "$API_BASE/projects/$STUDIO_PROJECT_ID/example-blocks/BLOCK_ID" -X DELETE
```

### Using examples in instructions

Add `{{ examples: BLOCK_ID }}` anywhere in the playbook instructions:

```bash
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X PATCH "$API_BASE/playbooks/BASE_ID/latest" \
  -d '{
    "content": "Sos el asistente de Acme Corp.\n\nSeguí el estilo de estos ejemplos:\n{{ examples: BLOCK_ID }}\n\nConsultá {{ kb(KB_ID) }} para responder consultas."
  }'
```

### Using examples in skills

Same syntax works inside skill content:

```bash
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$API_BASE/projects/$STUDIO_PROJECT_ID/playbooks/BASE_ID/skills" \
  -d '{
    "name": "reclamos",
    "description": "Manejar reclamos de clientes",
    "trigger": "Manejar reclamos de clientes",
    "content": "## Manejo de reclamos\n\n1. Validar la emoción del cliente\n2. Pedir datos del caso\n3. Ofrecer solución\n\n{{ examples: BLOCK_ID }}",
    "is_active": true,
    "order": 0
  }'
```

### Workflow: Import style from a human agent

This is the most powerful use case — take the best CX agent's conversations and replicate their style in the AI assistant.

**Step 1**: Identify the best conversations (e.g., from Intercom, or from Studio Chat's own chat log)

**Step 2**: Create example blocks with those conversations, anonymizing user data:

```bash
# Example: the best agent's greeting style
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$API_BASE/projects/$STUDIO_PROJECT_ID/example-blocks" \
  -d '{
    "examples": [
      {
        "turns": [
          {"role": "user", "content": "Hola"},
          {"role": "assistant", "content": "¡Hola! Bienvenido/a a Acme Corp. Soy tu asistente virtual. ¿En qué te puedo ayudar hoy?"}
        ]
      }
    ]
  }'

# Example: how the best agent handles complaints
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$API_BASE/projects/$STUDIO_PROJECT_ID/example-blocks" \
  -d '{
    "examples": [
      {
        "turns": [
          {"role": "user", "content": "Me robaron, me cobraron doble"},
          {"role": "assistant", "content": "Entiendo tu frustración y lamento mucho lo que pasó. Vamos a revisar tu caso ahora mismo para solucionarlo lo antes posible. ¿Me podrías pasar tu número de cuenta o el ID de la transacción?"}
        ]
      }
    ]
  }'
```

**Step 3**: Reference the blocks in the assistant's instructions and skills:

```bash
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X PATCH "$API_BASE/playbooks/BASE_ID/latest" \
  -d '{
    "content": "Sos el asistente de Acme Corp.\n\n{{ examples: GREETING_BLOCK_ID }}\n\nConsultá la base de conocimiento para responder."
  }'
```

**Step 4**: For specific scenarios (complaints, refunds), add examples to the corresponding skill:

```bash
curl -s -H "Authorization: Bearer $STUDIO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X PATCH "$API_BASE/projects/$STUDIO_PROJECT_ID/playbooks/BASE_ID/skills/reclamos" \
  -d '{"content": "## Reclamos\n\nManejar con empatía.\n\n{{ examples: COMPLAINTS_BLOCK_ID }}"}'
```

The assistant will now adopt the style of your best human agent for each scenario.

### Data placeholder syntax

In example conversations, use `#` to mark where dynamic data should go. The assistant understands these are placeholders to be filled with real data:

```json
{
  "turns": [
    {"role": "user", "content": "¿Cuándo llega mi pedido?"},
    {"role": "assistant", "content": "Tu pedido está en estado # y se estima que llegue en # días hábiles."}
  ]
}
```

---

## API Tools

Custom HTTP integrations the assistant can call during conversations.

```bash
# List tools
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/api-tools" --params include_playbook_usage=true

# Create tool
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/api-tools" \
  -X POST --body '{
    "name": "Check Order Status",
    "description": "Look up order status by order ID",
    "url": "https://api.example.com/orders/{order_id}",
    "method": "GET",
    "parameters": [
      {"name": "order_id", "type": "string", "description": "The order ID", "required": true}
    ]
  }'
```

---

## Project Settings

```bash
# Get settings
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/settings"

# Update personality tone
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/settings" \
  -X PATCH --body '{"personality_tone": "friendly"}'
```

Personality tones: `professional`, `friendly`, `casual`, `expert`, `playful`.

---

## Alerts

Alerts are cron-based condition monitors that evaluate custom conditions and notify via Slack and/or email when triggered. Each alert has a set of conditions (written as natural language instructions), a cron schedule (minimum 10-minute interval), and optional notification channels.

### List alerts

```bash
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/alerts"
```

Returns all alert definitions for the project with `last_run_at` and `last_triggered_at` timestamps.

### Create alert

**Single condition:**

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/alerts" \
  -X POST --body '{
    "name": "High handoff rate",
    "instructions": "Check if the handoff rate exceeds 30% in the last period",
    "cron_expression": "*/30 * * * *",
    "playbook_base_ids": ["BASE_ID_1"],
    "slack_channel": "alerts-channel",
    "email_recipients": ["team@example.com"]
  }'
```

**Multi-condition** — pass `instructions` as a JSON array of strings. Each condition is evaluated independently by index; the alert triggers if ANY condition is met:

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/alerts" \
  -X POST --body '{
    "name": "Quality monitor",
    "instructions": "[\"Handoff rate exceeds 30%\", \"Negative sentiment above 50%\", \"Conversation volume dropped by more than 40%\"]",
    "cron_expression": "0 */6 * * *",
    "slack_channel": "alerts-channel"
  }'
```

The executor evaluates each condition independently and returns per-condition results in the run's `trigger_summary`:

```json
[
  {"index": 0, "condition": "Handoff rate exceeds 30%", "triggered": true, "summary": "Handoff at 35%"},
  {"index": 1, "condition": "Negative sentiment above 50%", "triggered": false, "summary": "At 12%, within normal range"},
  {"index": 2, "condition": "Volume dropped by more than 40%", "triggered": false, "summary": "Volume stable at +2%"}
]
```

Fields:
- `name` (required) — Alert display name
- `instructions` (required) — Plain text (single condition) or JSON array of strings (multi-condition). Conditions are written in natural language and evaluated by the data-expert skill against real conversation data.
- `cron_expression` (required) — Cron schedule (minimum 10-minute interval)
- `playbook_base_ids` (optional) — Filter analysis to specific playbooks
- `slack_channel` (optional) — Slack channel name for notifications
- `email_recipients` (optional) — List of email addresses for notifications

At least one notification channel (`slack_channel` or `email_recipients`) should be configured for the alert to be useful.

### Get alert

```bash
python3 scripts/api.py "/alerts/ALERT_ID"
```

### Update alert

```bash
python3 scripts/api.py "/alerts/ALERT_ID" \
  -X PATCH --body '{"cron_expression": "0 */6 * * *", "is_enabled": false}'
```

All fields optional: `name`, `instructions`, `cron_expression`, `playbook_base_ids`, `slack_channel`, `email_recipients`, `is_enabled`.

### Delete alert

```bash
python3 scripts/api.py "/alerts/ALERT_ID" -X DELETE
```

Soft delete — requires human user (API keys cannot delete).

### Test run an alert

Triggers a manual test run using the alert's cron interval as the evaluation window. Returns immediately with a run object (status `pending`); execution happens in the background.

```bash
python3 scripts/api.py "/alerts/ALERT_ID/test" -X POST
```

### List alert runs

```bash
python3 scripts/api.py "/alerts/ALERT_ID/runs" --params limit=20 offset=0
```

Returns past executions (newest first) with: `status`, `triggered`, `trigger_summary`, `window_start`, `window_end`, `execution_log`.

### Get a specific run

```bash
python3 scripts/api.py "/alerts/runs/RUN_ID"
```

---

## Trending Topics

Trending topics analysis identifies the top conversation themes for a project over a configurable time window. Analysis runs asynchronously via a background job with progress tracking.

### Generate analysis

Starts a new trending topics analysis job. Returns a `job_id` to poll for progress.

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/insights/trending-topics/generate" \
  -X POST --body '{
    "playbook_base_ids": ["BASE_ID_1"],
    "time_window_days": 14
  }'
```

Fields (all optional):
- `playbook_base_ids` — Filter to specific playbooks
- `tags` — Filter by conversation tags
- `time_window_days` — Analysis window in days (1-90, default 7)

Returns 409 if an analysis already exists for today with the same config, or a job is already running.

### Check status

Quick status check — returns the current state (completed analysis, running job, or not found).

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/insights/trending-topics/status" \
  --params "time_window_days=14"
```

Optional query params: `playbook_base_ids` (comma-separated), `tags` (comma-separated), `time_window_days`.

### Poll job progress

After generating, poll this endpoint to track progress (0-100%).

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/insights/trending-topics/job/JOB_ID"
```

Returns: `status` (pending/running/completed/failed), `progress` (0-100), `step`, `progress_message`, `analysis_id` (when completed).

### Get analysis

Fetch the full results of a completed analysis.

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/insights/trending-topics/analysis/ANALYSIS_ID"
```

Returns: `topics` (up to 5 trending topics with conversation counts, sentiment breakdown, handoff rates, example conversations), `total_conversations`, `conversations_analyzed`, `time_window_days`, `playbook_base_ids`.

### List past analyses

Browse all past analyses for a project, newest first.

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/insights/trending-topics/analyses" \
  --params limit=20 offset=0
```

### Export analysis as PDF

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/insights/trending-topics/analysis/ANALYSIS_ID/pdf" \
  -o trending-topics-report.pdf
```

---

## Important Notes

- **KB status flow**: ADDED -> (sync) -> ACTIVE. After edits: ACTIVE -> EDITED -> (sync) -> ACTIVE.
- **Always sync after KB changes**: Creating, updating, or deleting KBs requires syncing.
- **Playbook versioning**: Every update creates a new version. Use `active` endpoint to control which version is live.
- **Skills versioning**: Skill changes (add/edit/delete) also create new playbook versions. Use the dedicated skill endpoints for individual operations.
- **base_id vs playbook_id**: Active version endpoints use `base_id` (stable across versions). Other endpoints use `playbook_id` (specific version). Skill endpoints use `base_id`.
- **Soft deletes**: Delete operations are soft — use restore to undo.
