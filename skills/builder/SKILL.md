---
name: builder
description: >
  Build and configure Studio Chat assistants — instructions, knowledge bases, skills, example blocks,
  API tools, toolkit actions (Intercom, Slack, Zendesk, Pylon, Notion databases, Google Sheets), alerts, schedules, and trending topics. Use when asked
  to create, update, or manage any aspect of an assistant's configuration, including wiring up the
  template macros (pills) and the objects they reference. Covers all CRUD operations via the Studio Chat API.
---

# Builder

Build and configure Studio Chat assistants using the API. All calls are authenticated automatically via environment variables. The API base URL (`https://api.studiochat.io`) is hardcoded in the scripts.

**IMPORTANT: Always confirm before creating or modifying.** Never create knowledge bases,
playbooks, API tools, or trigger syncing without explicit user confirmation. Show what
you're about to do and wait for approval before executing any write operation.

## Approvals: describe every queued change

With a sandbox key (`sbs_`), some write operations don't execute immediately: the API
answers **202** with `{"approval_id": "...", "status": "pending", ...}` and queues the
request for a human admin to review. Whenever a request returns 202 with an
`approval_id`, immediately attach an explanation of the change — it is what the reviewer
reads in the approvals panel instead of the raw payload:

```bash
python3 scripts/api.py "/approvals/APPROVAL_ID/description" -X PATCH --body '{
  "description": "Links the new Refunds FAQ KB to the Support assistant so it can answer refund questions on its own. Before: 1 KB linked. After: 2 KBs. Asked by the user in chat."
}'
```

Write it for the human admin (shown verbatim in the UI):

- WHAT changes and WHY — the user request or the data that motivated it
- the relevant before → after in plain words (names, counts, key fields), not JSON
- a few sentences, in the language the account operates in

Then tell the user the change is queued for approval. Only PENDING approvals accept a
description (409 once reviewed); you can re-PATCH to refine it while it is pending.

### Show the actual edit with a diff block

When the change is an **edit to existing text** — a skill's `content`, a playbook's
instructions, a KB item, an example block, a tool description — prose alone makes the
reviewer guess what moved. Embed a **diff block** in the description and the approvals
panel renders it as a side-by-side before/after (red = removed, green = added), the same
widget used for playbook version diffs. Put a short prose explanation first (the WHAT/WHY
above), then the diff block(s):

```
[[diff]]
[[before]]
4. Si los 3 fallan → escalar a humano.
[[after]]
Si las 3 variantes fallan, NO escales todavía: pedile al cliente la razón social
exacta y reintentá. Si vuelve a fallar, o si no la sabe → escalá a humano.
[[/diff]]
```

Rules for the diff block (the parser is strict — follow these exactly or the block
won't render):

- Each of the four markers — `[[diff]]`, `[[before]]`, `[[after]]`, `[[/diff]]` — must be
  on its **own line**, lowercase, no spaces inside the brackets. Always close with
  `[[/diff]]`.
- `[[before]]` and `[[after]]` are **required**. The text between `[[before]]` and
  `[[after]]` is the old version; the text between `[[after]]` and `[[/diff]]` is the new
  version. Paste both **verbatim** — do NOT re-summarize inside the block; the prose above
  already does that.
- Include only the **section that actually changed** plus a line or two of surrounding
  context, not the whole skill. Big walls of unchanged text bury the change.
- For a brand-new addition leave `[[before]]` empty; for a deletion leave `[[after]]`
  empty. (Identical before/after just renders "no difference".)
- You may include **several** `[[diff]]…[[/diff]]` blocks in one description (e.g. two
  separate edits in the same skill). Text outside the blocks renders normally.
- This is plain text inside the same `description` field — no extra API call. If the panel
  ever doesn't render it, it still reads as legible before/after text.

Use a diff block for text edits; skip it for pure structural changes (linking a KB,
toggling a setting, creating an empty object) where a before → after count in prose is
clearer.

## Key Terminology

**Assistants and playbooks are the same concept.** In the API, the term "playbook" is used
everywhere — but users refer to them as "assistants," "bots," or "agents." When the user
mentions any of these, they mean a playbook.

## Setup

Set the following environment variables before using the scripts:

```bash
export STUDIO_API_TOKEN="sbs_your_api_key_here"
export STUDIO_PROJECT_ID="your-project-uuid"
# Optional — point at a different backend (e.g. local dev):
# export STUDIO_API_URL="http://localhost:8000"
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
    "name": "Support Assistant",
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

### Conditional skills (`enable_condition`)

A skill with `is_active: true` can additionally be gated on the **live conversation
context** — the same per-turn context dict the `{{ context: path }}` pill reads.
Skills whose condition doesn't match are removed from the agent for that turn:
not listed in the system prompt, not loadable, and their skill-scoped tools/KBs
are not registered. `enable_condition: null` (or omitted) = always enabled.

Use it for segment-specific casuísticas: promos for one country, VIP-only flows,
per-campaign behavior — instead of duplicating assistants or asking the model to
self-filter.

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/playbooks/BASE_ID/skills" \
  -X POST --body '{
    "name": "oferta-vip-arg",
    "description": "Aplicar la promo 50% OFF cuando el cliente pregunta precios",
    "trigger": "El cliente pregunta precios o totales",
    "content": "## Promo activa\n1. Calcular el total\n2. Aplicar 50% de descuento",
    "is_active": true,
    "enable_condition": {
      "op": "and",
      "clauses": [
        {"path": "contact.country", "operator": "eq", "value": "ARG"},
        {"path": "contact.vip", "operator": "eq", "value": true}
      ]
    }
  }'
```

**Condition format** — a small boolean AST:

- Group: `{"op": "and" | "or", "clauses": [...], "negate": false}`. Groups nest
  one level (OR-of-ANDs / AND-of-ORs), max 16 clauses total.
- Clause: `{"path": "dotted.path", "operator": "...", "value": ..., "negate": false}`.
  `path` uses the context-pill grammar (dot-separated keys into the context dict).

| Operator | Value | Matches when |
|---|---|---|
| `eq` / `neq` | scalar | equal / not equal (lax: `true` matches `"true"`, `5` matches `"5"`) |
| `in` / `not_in` | non-empty array | actual equals any / no element (lax per element) |
| `contains` | scalar | substring of a string value, or member of a list value |
| `exists` / `not_exists` | — (omit `value`) | key present and non-empty / missing or empty |
| `gt` `gte` `lt` `lte` | number | numeric comparison (numeric-looking strings coerce) |

**Semantics you must design around (fail-closed):**

- A **missing key**, empty string, or empty/absent context makes every clause
  false **except `not_exists`** — including `neq`. "Missing or different" is
  spelled `not_exists OR neq` explicitly.
- Conditions re-evaluate **every turn**: a skill hidden on turn 1 (context not
  yet populated) appears the moment the attribute arrives.
- Equality is case-sensitive for strings (`"ARG"` ≠ `"arg"`); whitespace is
  stripped; booleans never equal numbers (`true` ≠ `1`).
- If the skill is referenced via `{{ skill: name }}` from instructions while its
  condition doesn't match, `load_skill` returns a static bounce telling the model
  the skill is disabled for this conversation and to proceed without it — safe,
  but don't rely on it as a control-flow mechanism.

**Updating / clearing:** on `PATCH .../skills/{name}`, omitting `enable_condition`
keeps the stored condition; an explicit `"enable_condition": null` clears it
(back to unconditional). The full-playbook `skills` snapshot behaves the same
way — items that omit the field preserve the stored condition by skill name, so
config-as-code that predates this field never wipes conditions. To **set** a
condition from config-as-code you must include the field explicitly.

### Dry-run a condition (`condition-check`)

Validate a condition and test what it would do — against a hand-built context or
against a **real conversation's** latest context snapshot. Read-only: no version
is created and sandbox (`sbs_`) keys don't queue an approval.

```bash
# Validate + evaluate against a sample context
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/playbooks/BASE_ID/skills/condition-check" \
  -X POST --body '{
    "condition": {"op": "and", "clauses": [{"path": "contact.country", "operator": "eq", "value": "ARG"}]},
    "context": {"contact": {"country": "ARG"}}
  }'

# Would this skill have fired in a real conversation? (uses its latest context snapshot)
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/playbooks/BASE_ID/skills/condition-check" \
  -X POST --body '{
    "condition": {"op": "and", "clauses": [{"path": "campaign", "operator": "eq", "value": "active"}]},
    "conversation_id": "CONVERSATION_ID"
  }'
```

Response: `{"valid": true, "rendered": "campaign == \"active\"", "result": true, "context_found": true, "context": {...}}`.
`valid: false` + `error` on a malformed condition; `context_found: false` when the
conversation has no context snapshot (the condition would fail closed). **Always
dry-run against a real conversation of the target segment before shipping a
condition** — context shapes differ per integration (webhook vs public chat API),
and a path that works for one client may never match for another.

### Template macros (the "pills")

Skill content and playbook instructions support the **same five** inline macros. They are the only macros the compiler recognizes:

| Macro | Points at | Object created via |
|---|---|---|
| `{{ kb(KB_ID) }}` | a knowledge base the agent can search | [Knowledge Bases](#knowledge-bases) |
| `{{ tool(TOOL_ID) }}` | a custom HTTP API tool | [API Tools](#api-tools) |
| `{{ custom_tool: short_name }}` | one **pre-configured** toolkit action (some params pinned) | [Toolkit Actions](#toolkit-actions-slack) (a tool configuration) |
| `{{ examples: BLOCK_ID }}` | a reference example block | [Example Blocks](#example-blocks) |

Each referenced KB / tool / action is registered in the agent **even before** the skill loads, so it's available the moment the skill fires.

**`{{ custom_tool: short_name }}` requires an object to exist first** — a *tool configuration* — and missing it is the most common source of "the assistant can't do X". See [Toolkit Actions](#toolkit-actions-slack).

**`{{ examples: BLOCK_ID }}` is the ONLY way to add examples** — never paste sample conversations directly into instruction or skill text. See [Example Blocks](#example-blocks).

> **No save-time validation.** A playbook saves fine even if a macro points at something that doesn't exist or a toolkit action that isn't connected — at runtime the macro silently degrades to literal text and the action just isn't available (only a log warning). Always confirm the referenced object exists before writing the macro.
>
> There is **no** `{{ composio_tool: … }}` macro (Composio was removed).

---

## Tagging

The assistant can apply **conversation tags** each turn (the `tags` field in its output). Tags are validated against a **closed whitelist** the platform builds automatically by parsing the instructions and skills: **every tag value wrapped in single backticks is registered as a supported tag.** At runtime, any tag the assistant emits that is NOT in this list is dropped — it never reaches the conversation.

### Backtick policy (IMPORTANT)

**Single backticks are reserved for tag values.** The whitelist is built by parsing backtick-wrapped tokens, so anything you wrap in single backticks that *looks like a tag* becomes a "supported tag".

- ✅ **Wrap every tag value in single backticks**, in both instructions and skills — e.g. `` `billing` ``, `` `refund_request` ``, `` `escalation-whatsapp` ``. If a tag is mentioned **without** backticks everywhere, it won't be in the whitelist and the assistant **cannot apply it** (it gets dropped).
- ❌ **Do NOT use single backticks for anything that is not a tag** — status values (`completed`, `failed`, `processing`), API field names (`source_channel`), tool IDs, enum values, currency codes, or code snippets. Backticked, they get parsed as fake tags, polluting the whitelist and the output spec. For those, use plain text, "double quotes", or fenced code blocks instead.

**What the parser recognises as a tag:** a single-token, lowercase `snake_case` / `kebab-case` value (may start with a digit, e.g. `2fa`). Tokens that are camelCase (`manualReview`), dotted (`user.status`), numeric (`5003`), or multi-word are ignored — so they're safe even if backticked, but prefer not to backtick non-tags at all.

> Rule of thumb: **if it isn't a tag the assistant should apply to the conversation, don't put it in single backticks.**

When defining the tag taxonomy (in the instructions and/or a dedicated `tagging` skill), list every tag value in backticks. Tags that arrive externally (routing/channel tags injected via the chat API context) are not parsed here and are never filtered — only tags the assistant itself emits go through the whitelist.

---

## Example Blocks

Example blocks are reference conversations that show the assistant HOW to communicate — tone, style, personality, containment strategies, and approach. They are inline in the instructions or skills via `{{ examples: BLOCK_ID }}` template macros.

> **Example blocks are THE only way to add examples. Always.** Never write sample conversations, "here's a good reply:", Q→A pairs, or any other verbatim example directly into the instructions or skill text. Every example — without exception — goes into an example block and is referenced with `{{ examples: BLOCK_ID }}`. If you catch yourself typing an example turn inline in `content`, stop and move it into a block.
>
> Why: blocks are compiled into structured `<example id="…">` tags the LLM is told to follow and cite (`<<id>>`), they're versioned/immutable for clean rollback, and they keep the instructions readable. Examples pasted raw into the prose get none of that machinery — they read as literal rules, bloat the prompt, and can't be cited or rolled back. When migrating or editing an existing playbook, **move any inline examples you find into blocks** and replace them with the macro.

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

Custom HTTP integrations the assistant can call during conversations. Project-owned and self-contained — once created, reference it in instructions or a skill with `{{ tool(TOOL_ID) }}`. Different from **toolkit actions** (below), which depend on a connection the user owns.

```bash
# List tools
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/api-tools" --params include_playbook_usage=true
```

### Create a GET tool (URL parameters)

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/api-tools" \
  -X POST --body '{
    "name": "check_order_status",
    "description": "Look up order status by order ID. Use when the customer asks where their order is.",
    "url": "https://api.example.com/orders/{{ order_id }}",
    "method": "GET",
    "headers": {"X-API-Key": "your-secret-key"},
    "parameters": [
      {"name": "order_id", "description": "The order ID the customer provides"}
    ]
  }'
```

- **`name`** must match `^[a-zA-Z0-9_.-]{1,64}$` (LLM tool-name rule — **no spaces**).
- **`headers`** are static — put auth here (e.g. `X-API-Key`).
- **`data_expiration_hours`** (optional): response cache TTL. `0` = always re-fetch, `null`/omitted = never expires.
- **`response_jmespath`** (optional): a JMESPath applied to the JSON response before the LLM sees it, to trim/reshape verbose payloads.

### Templating: `{{ param }}` (double braces, Jinja)

Inside a tool's `url`, `body_fields`, or `body_json`, placeholders are **`{{ name }}`** (double curly braces, whitespace optional). Two kinds:

| Placeholder | Filled by | Where you declare it |
|---|---|---|
| `{{ param }}` | the **LLM** at call time | `parameters` (URL) or `body_fields` (body) — the `description` is what the LLM sees |
| `{{ context.path }}` | the **conversation context**, not asked to the LLM | nowhere extra — auto-detected (e.g. `{{ context.contact.email }}`) |

> Don't confuse this with the `{{ tool(...) }}` / `{{ kb(...) }}` **pills** that go in *playbook/skill text* (above). Those reference objects; `{{ param }}` here is a value the tool fills in. Same braces, different layer.

**Every templated field needs a description.** For URL params, each `{{ x }}` in `url` gets a `parameters` entry — `{name, description}` only, and URL params are **always string**. For body params, the description lives on the matching `body_fields` entry. That description is the *only* signal the LLM has for what to put there — write it well.

### POST / PUT / PATCH body

Define the body with **`body_fields`** (`body_type` defaults to `"fields"`). Each field's `value` is a hardcoded literal, an LLM-filled `{{ param }}`, or a `{{ context.path }}`:

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/api-tools" \
  -X POST --body '{
    "name": "create_ticket",
    "description": "Open a support ticket for the customer.",
    "url": "https://api.example.com/tickets",
    "method": "POST",
    "headers": {"X-API-Key": "your-secret-key"},
    "body_fields": [
      {"name": "subject",  "type": "string",  "value": "{{ subject }}",  "description": "Short title for the issue", "required": true},
      {"name": "priority", "type": "integer", "value": "{{ priority }}", "description": "1=low … 5=urgent",          "required": false},
      {"name": "source",   "type": "string",  "value": "chatbot"},
      {"name": "email",    "type": "string",  "value": "{{ context.contact.email }}"}
    ]
  }'
```

- `{{ subject }}` / `{{ priority }}` → exposed to the LLM, typed by `type`, prompted by `description`.
- `"value": "chatbot"` → **hardcoded** literal (no template) → sent as-is, cast to `type`.
- `{{ context.contact.email }}` → pulled from conversation context, **not** asked to the LLM.
- `type`: `string | number | integer | boolean`. `required` defaults to `true`.

**Raw JSON body** (`body_type: "json"`) — for nested structure: put the template in `body_json` with `{{ param }}` placeholders, and use `body_fields` only to carry each param's `type`/`description`/`required`:

```json
{
  "name": "submit_order", "description": "...", "url": "https://api.example.com/orders", "method": "POST",
  "body_type": "json",
  "body_json": "{\"order\": {\"id\": \"{{ order_id }}\", \"qty\": {{ qty }}}}",
  "body_fields": [
    {"name": "order_id", "type": "string",  "description": "Order id"},
    {"name": "qty",      "type": "integer", "description": "Quantity"}
  ]
}
```

A full-string `"{{ qty }}"` (or a bare `{{ qty }}`) becomes a **typed** value (int/bool preserved); an embedded `"id-{{ x }}"` is string-interpolated.

### Get / update / delete

```bash
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/api-tools/TOOL_ID"
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/api-tools/TOOL_ID" -X PATCH --body '{"description": "..."}'   # all fields optional
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/api-tools/TOOL_ID" -X DELETE                                  # soft delete
```

Then wire it into an assistant with `{{ tool(TOOL_ID) }}` (see [Template macros](#template-macros-the-pills)).

---

## Toolkit Actions

Some actions — *send a Slack message*, *create an Intercom ticket*, *set attributes*, *close the
conversation* — come from **built-in toolkits** that wrap a third-party API. Unlike a KB or an API
tool (which the builder creates outright), a toolkit must be **connected by the user** with their own
credentials before its actions can be used.

> **Full catalog of every toolkit action** — Intercom Tickets/Conversations, Slack, Zendesk, Pylon,
> GU1, Notion Databases, Google Sheets — and how to configure each and wire it into instructions is in
> [`references/toolkit-actions.md`](./references/toolkit-actions.md). It also covers the Intercom
> ticket **Motivo/Submotivo taxonomy** (the most error-prone part), the Google Sheets
> **access-check flow** (verify the sheet is shared with the service account BEFORE configuring),
> and the audit endpoints that catch a silently-broken pill. The Slack walkthrough below is the
> worked example of the shared connect → discover → configure → wire workflow; **every** toolkit
> follows the same shape.

**The builder never connects a toolkit.** Connecting requires the customer's secret (a Slack bot token, an Intercom token) or an interactive OAuth flow — that's the user's job, in the UI. The builder's role is to **discover** what's connected and wire the available actions into instructions/skills. If an action you need belongs to a toolkit that isn't connected, **stop and ask the user to connect it first** — don't write the macro and hope.

**Slack has two connection variants — same action, different slug:**

| Slug | How the user connected it | `auth_type` |
|---|---|---|
| `SLACK` | Pasted a Slack **bot token** | `api_key` |
| `SLACK_OAUTH` | Authorized via the **OAuth** popup | `oauth` |

Both expose the same `SLACK_SEND_MESSAGE` action with the same params — only the registry slug differs. In Step 1 check which one is `is_connected: true` and use **that** slug in the metadata paths below. A project typically has one or the other, not both.

> The other toolkits (Intercom Tickets/Conversations, Zendesk, Pylon, GU1, Notion Databases,
> Google Sheets) follow the same connect → discover → configure pattern — each action, its params,
> and how to wire it into instructions is documented in
> [`references/toolkit-actions.md`](./references/toolkit-actions.md). Google Sheets is the one
> twist: it's enabled with no credentials, and each spreadsheet must pass the `sheet_access`
> check (shared as Editor with the service account) before you configure a pill against it.

### The workflow (run this whenever the user asks for "send a Slack message")

When the request is *"when X happens, the assistant should send a Slack message"*, drive this conversation — don't guess the channel, message, or mentions:

1. **Check the connection first.** `GET /custom-toolkits` → is `SLACK` **or** `SLACK_OAUTH` `is_connected: true`?
   - **Neither connected →** stop. Tell the user Slack isn't connected and ask them to connect it (bot token or OAuth) in the UI, then come back. Do not write the macro.
   - **Connected →** note the connected slug and its `connected_account_id`, and continue.
2. **Ask the user three things** (these are the params you'll pin / leave open):
   - **Where?** Which channel. Fetch the options (`…/metadata/channels`) and let them pick — you pin the channel id.
   - **What message?** Either a **fixed text** (pin it in `message`) or — more common — the assistant **writes it per-situation** (leave `message` open; you'll describe *how* in the instruction next to the macro).
   - **Any mention?** If yes, fetch that channel's people (`…/metadata/members?channel=<id>`) and pin the chosen ids in `mentions` (or a special token like `!here`).
3. **Build the action object.** `POST /tool-configurations` with `tool_slug: "SLACK_SEND_MESSAGE"`, the `connected_account_id` as `toolkit_connection_id`, and `config.params` holding what you pinned (channel, mentions, optionally message). Read the generated `short_name` from the response.
4. **Reference it with the macro.** Put `{{ custom_tool: <short_name> }}` in the instruction/skill at the spot that describes the situation X — and, if the message is LLM-written, say there how it should be phrased. Confirm the change with the user before saving (every write is confirmed), then re-read to check the `short_name` is spelled exactly.

The rest of this section is the mechanics each step relies on.

### Step 1 — Discover what's available

```bash
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/custom-toolkits"
```

Returns every registry toolkit. For each, the fields that matter:

| Field | Use |
|---|---|
| `slug` | Identifies the toolkit (`SLACK` / `SLACK_OAUTH`); used in the metadata paths below. |
| `is_connected` | **Gate.** `false` ⇒ you cannot use its actions — ask the user to connect it. |
| `connected_account_id` | The connection id. You pass this as `toolkit_connection_id` when creating a tool configuration. `null` when not connected. |
| `tools` | The action slugs this toolkit exposes — for Slack, `SLACK_SEND_MESSAGE`. |
| `tool_params` | Per-action configurable params you can **pin** in a tool configuration. A param with `"metadata_source"` (e.g. Slack `channel`) has its valid values fetched via the metadata endpoint (Step 2). |
| `auth_type` | `api_key` or `oauth` — informational; either way the user connects it, not you. |

### Step 2 — Create a tool configuration

Every toolkit action is exposed the same way: create a **tool configuration** (a saved instance of one action with chosen params pinned), then reference its generated `short_name` with `{{ custom_tool: short_name }}`. Pinning the channel (and optionally a fixed message / mentions) is what makes it "send to *this* place" rather than leaving the agent to guess.

**2a. (If the action has a `metadata_source` param)** fetch the valid values so you pin a real id, not a guess. The endpoint is `GET /custom-toolkits/{SLUG}/metadata/{metadata_source}` and it returns a list of `{id, name}` options:

```bash
# list the Slack channels the connected bot can post to
# (use SLACK_OAUTH instead of SLACK if that's the connected variant)
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/custom-toolkits/SLACK/metadata/channels"
```

**Dependent params (`options_depend_on`).** Some params can only be resolved *after* another is chosen — their `tool_params` entry has an `options_depend_on` key. You must pass the parent value as a **query param** or you get an empty list back. The Slack `mentions` param depends on `channel` (`"options_depend_on": "channel"`), so to list the people you can @-mention you pass the chosen channel id:

```bash
# members of a SPECIFIC channel (omit ?channel and the backend returns [])
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/custom-toolkits/SLACK/metadata/members" \
  --params channel=C0123456789
```

So the order for a Slack pill is: fetch `channels` → pick a channel id → fetch `members?channel=<that id>` → pick the member ids to mention.

(The metadata endpoint only works once the toolkit is connected — it reads the stored credentials. If it errors with a missing-scope hint, the user's Slack connection lacks a scope — tell them; you can't fix it from here.)

**Which params to pin** — look at each entry in the action's `tool_params` (Step 1). For `SLACK_SEND_MESSAGE` there are three: `channel`, `mentions`, `message`.

- `"llm_decideable": false` (Slack `channel` and `mentions`) → you **must** pin it in `config.params`. The LLM is not allowed to choose it.
- no `llm_decideable` flag (Slack `message`) → the LLM fills it at runtime. You *can* still pin it to lock it, including to a context value via a `{{deps.…}}` template.
- **Value format for `select` params**: pin the **id** (from the metadata call), not the label. `"ID:Label"` also works — the backend keeps the part before the first `:`. So `"C0123456789"` and `"C0123456789:#soporte"` are equivalent.

Any param you pin disappears from what the LLM sees; everything else stays in the tool's schema for the LLM to fill.

**2b. Create the configuration.** `toolkit_connection_id` is the `connected_account_id` from Step 1.

*Example — send a Slack message to a fixed channel, @-mentioning specific people* (LLM only writes the text):

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/tool-configurations" \
  -X POST --body '{
    "tool_slug": "SLACK_SEND_MESSAGE",
    "toolkit_connection_id": "CONNECTED_ACCOUNT_ID_FROM_STEP_1",
    "display_name": "Notify soporte + oncall",
    "config": {
      "params": {
        "channel": "C0123456789",
        "mentions": "U0ABC123,U0DEF456"
      }
    }
  }'
```

`mentions` is a comma-separated list of Slack user ids (from the `members` metadata of that channel) and/or the special tokens `!here` / `!channel` / `!everyone`. The backend encodes them into notifying `<@U…>` / `<!here>` sequences at send time. The `tool_slug` stays `SLACK_SEND_MESSAGE` for both connection variants.

**Don't construct the `short_name` yourself.** The backend generates it (slugified `display_name` + a random suffix) and returns it in the create response, e.g.:

```json
{ "id": "…", "short_name": "notify_soporte_oncall_a1b2c", "tool_slug": "SLACK_SEND_MESSAGE", … }
```

Read `short_name` from that response — that exact string is what goes in the macro.

**2c. Reference it** in instructions or a skill:

```
When the customer reports an outage, post a heads-up with {{ custom_tool: notify_soporte_oncall_a1b2c }}.
```

### Managing tool configurations

```bash
# List existing configs (each shows in_use + usages — reuse before creating duplicates)
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/tool-configurations"

# Is the toolkit connected? (must be true before its actions can be used)
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/custom-toolkits/INTERCOM_TICKETS/status"

# See a toolkit action's configurable schema (fields, required, metadata_sources) + is_connected
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/custom-toolkits/INTERCOM_TICKETS/actions"

# Effective per-attribute view of one pill + detected problems (required-but-empty, etc.)
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/tool-configurations/CONFIG_ID/schema"

# Audit ALL pills — find the ones that will 400 at runtime (in-use first)
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/tool-configuration-audit"

# Where is each macro used? (short_name → playbook/skill)
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/custom-tool-usages"

# Update the config (short_name stays stable). If the pill is in use in active/latest
# instructions, an sbs_ token gets a 202 → the edit is queued for human approval.
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/tool-configurations/CONFIG_ID" \
  -X PUT --body '{"config": {"params": {"channel": "C0999999999"}}}'

# Delete a config (do this before the user can disconnect the toolkit —
# a connection with live tool configurations cannot be disconnected). In-use pills
# require approval (202) just like updates.
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/tool-configurations/CONFIG_ID" -X DELETE
```

**Auditing a broken pill.** When an action "isn't doing anything", run the audit — it cross-checks each
pill against its toolkit's live metadata and understands each toolkit's semantics:

- **Intercom Tickets** — required attributes left empty (e.g. `Motivo`, or a conditional `Submotivo …`),
  which otherwise fail silently with `400 Missing required attributes`.
- **Slack** (bot token *and* OAuth) — a pin-only `channel` left empty, or a pinned channel the bot can't
  access / that was renamed or archived.
- **Intercom Conversations · Set Attributes** — a tool with no attributes configured (a no-op), or an
  attribute name Intercom doesn't recognize (the write is silently dropped).

`GET .../tool-configurations/{id}/schema` gives the same per-attribute detail for a single pill.

### Checklist before writing a toolkit macro

1. `GET /custom-toolkits` → is the toolkit `is_connected: true`? If not, **ask the user to connect it** and stop.
2. Create a tool configuration (pin params, resolving ids via the metadata endpoint) → reference its `short_name` with `{{ custom_tool: short_name }}`.
3. Re-read the saved instructions to confirm the macro is spelled exactly as the `short_name` (there's no save-time validation to catch a typo).

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

## Monitors

Monitors are **aggregate** triggers (Datadog-style) — a SQL count of conversations matching
a structured filter, evaluated on a cron schedule. When the count crosses the threshold the
monitor fires and ships a notification to Slack and/or email.

Use **monitors** when the question is "how many?" (e.g. _more than 50 handoffs in the last
hour_). Use **alerts** when the question is "is the assistant misbehaving?" — alerts run a
natural-language check via the data-expert skill, monitors don't read messages at all.

Like alerts, the cron has a **10-minute minimum interval**.

### Filter shape

The filter is a compound AST over three leaf types — same shape used by other parts of the
platform. All leaves accept `negate: true`, and `group` accepts `op: "and"` or `op: "or"`.

```jsonc
// "tag billing AND skill refund AND NOT has_handoff"
{
  "type": "group",
  "op": "and",
  "children": [
    { "type": "tag",     "value": "billing" },
    { "type": "skill",   "value": "refund-process" },
    { "type": "handoff", "value": true, "negate": true }
  ]
}
```

Pass `null` (or omit the field) to match every conversation in the window.

### Comparison kinds

| `comparison_kind` | Meaning | Required field |
|---|---|---|
| `absolute` | Fire when `current >= threshold` | `threshold` |
| `baseline_relative` | Fire when `current >= threshold × baseline` (baseline = same window N hours ago) | `threshold`, `baseline_hours` |

### Window basis

- `last_message` (default) — the conversation had any activity inside the window.
- `first_message` — the conversation was created inside the window.

### Preview the filter (no monitor created)

The form preview returns a 7-day daily count + the lookback total. Use this to sanity-check
the filter before creating a monitor.

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/monitors/preview" \
  -X POST --body '{
    "filter": {"type": "tag", "value": "billing"},
    "window_basis": "last_message",
    "playbook_base_id": "BASE_ID",
    "window_minutes": 60
  }'
```

### List monitors

```bash
python3 scripts/api.py "/projects/$STUDIO_PROJECT_ID/monitors"
```

Each item carries `last_run_at`, `last_triggered_at`, and the last 24 runs as `recent_runs`
(sparkline data — `triggered`, `current_value`, `threshold_value`, `baseline_value`).

### Create monitor — absolute threshold

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/monitors" \
  -X POST --body '{
    "name": "Billing handoffs spike",
    "filter": {
      "type": "group",
      "op": "and",
      "children": [
        {"type": "tag",     "value": "billing"},
        {"type": "handoff", "value": true}
      ]
    },
    "window_basis": "last_message",
    "playbook_base_id": "BASE_ID",
    "cron_expression": "*/10 * * * *",
    "window_minutes": 60,
    "comparison_kind": "absolute",
    "threshold": 50,
    "slack_channel": "ops-alerts",
    "email_recipients": ["oncall@example.com"]
  }'
```

### Create monitor — baseline-relative

Fires when the current count is at least `threshold ×` what it was `baseline_hours` ago.
`threshold: 2.0` ⇒ "double the baseline". Good for catching spikes that don't have a fixed
absolute number.

```bash
python3 scripts/api.py \
  "/projects/$STUDIO_PROJECT_ID/monitors" \
  -X POST --body '{
    "name": "Conversation volume 2× baseline",
    "filter": null,
    "window_basis": "last_message",
    "playbook_base_id": "BASE_ID",
    "cron_expression": "*/15 * * * *",
    "window_minutes": 30,
    "comparison_kind": "baseline_relative",
    "threshold": 2.0,
    "baseline_hours": 24,
    "slack_channel": "ops-alerts"
  }'
```

Fields:

- `name` (required)
- `filter` (optional) — Conversation filter AST (see above). `null` matches everything.
- `window_basis` (default `last_message`) — `last_message` or `first_message`.
- `playbook_base_id` (required) — Scope to a single assistant (version-stable base id).
- `cron_expression` (required, default `*/10 * * * *`) — Min 10-minute interval.
- `window_minutes` (required, 1..1440) — How far back the count looks.
- `comparison_kind` (default `absolute`) — `absolute` or `baseline_relative`.
- `threshold` (required, > 0) — Absolute count or multiplier of baseline.
- `baseline_hours` (required when `baseline_relative`, 1..168) — Hours before "now" to anchor the baseline window.
- `slack_channel` (optional) — Slack channel name (no `#`).
- `email_recipients` (optional) — Email addresses.

At least one notification channel should be set or the monitor fires silently.

### Get monitor

```bash
python3 scripts/api.py "/monitors/MONITOR_ID"
```

### Update monitor

```bash
python3 scripts/api.py "/monitors/MONITOR_ID" \
  -X PATCH --body '{"threshold": 75, "is_enabled": false}'
```

All fields optional: `name`, `filter`, `window_basis`, `playbook_base_id`, `cron_expression`,
`window_minutes`, `comparison_kind`, `threshold`, `baseline_hours`, `slack_channel`,
`email_recipients`, `is_enabled`. Pass an empty group (`{"type":"group","op":"and","children":[]}`)
to clear the filter.

### Duplicate monitor

Creates a disabled copy named `copy-{original.name}` with the same scope, schedule, and
delivery — useful for A/B tweaking thresholds without touching the live one.

```bash
python3 scripts/api.py "/monitors/MONITOR_ID/duplicate" -X POST
```

### Delete monitor

```bash
python3 scripts/api.py "/monitors/MONITOR_ID" -X DELETE
```

> **Sandbox (`sbs_`) callers:** delete is the one operation that needs a human reviewer.
> The request returns **202** with `{"approval_id": "...", "status": "pending", "description": "...",
> "message": "Request queued for admin approval."}` instead of executing immediately. Confirm
> the deletion with the user (or the admin) before relying on the queue, and describe the
> queued change (see *Approvals: describe every queued change* above). Every other monitor
> operation (preview, create, list, get, update, duplicate, test, runs) executes synchronously.

### Test run a monitor

Inline manual evaluation. Persists a run row, and **delivers Slack/email if it would fire** —
clearly marked as a TEST run so it doesn't get confused with a real fire. Use it after
creating or editing a monitor to sanity-check the wiring.

```bash
python3 scripts/api.py "/monitors/MONITOR_ID/test" -X POST
```

### List monitor runs

```bash
python3 scripts/api.py "/monitors/MONITOR_ID/runs" --params limit=50 offset=0
```

Returns past runs (newest first) with `status`, `triggered`, `current_value`,
`threshold_value`, `baseline_value`, `summary`, `window_start`, `window_end`,
`error_message`, `started_at`, `completed_at`.

### Get a specific run

```bash
python3 scripts/api.py "/monitors/runs/RUN_ID"
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

## Gotchas

- **Con sandbox key (`sbs_`), las writes son 202 pending — siempre adjuntar descripción al approval.** El reviewe solo ve el description que adjuntás, no el payload raw. Si no describís, el approval queda sin contexto.
- **`playbook_base_id` para gestión de versiones, `playbook_id` para una versión específica.** Confundirlos lleva a crear versiones duplicadas.
- **Nunca eliminar KBs sin confirmar que no están linkeadas a otros asistentes.** Una KB puede estar compartida entre varios playbooks del mismo proyecto.
- **Los `pills` (template macros) deben existir como objetos en la API antes de referenciarlos en instrucciones.** Si el pill `{{nombre_cliente}}` no existe como template variable registrada, la instrucción lo trata como texto literal.
- **Trending topics se generan en background — no son instantáneos.** Después de habilitarlos, hay un delay de procesamiento. No asumir que están disponibles inmediatamente.
- **El campo `content` de las instrucciones tiene límite de tokens.** Si las instrucciones son muy largas, el asistente puede truncar en producción. Preferir casuísticas para comportamientos específicos.

## Dependencias

Este skill es la base que usan `customer-success:continuous-improvement` y `customer-success:quality-engineer` para modificar asistentes.
