# Toolkit Actions — the full catalog & how to wire them into instructions

Toolkit actions let an assistant *do* things in a third-party system mid-conversation:
create a support ticket, close the conversation, set attributes, post to Slack, add an entry
to a Notion database, append or look up a row in a Google Sheet, check availability and
book a meeting on Cal.com. This reference covers
**every** toolkit action Studio Chat supports and how to make an assistant use it from its
instructions.

> The Slack walkthrough in `SKILL.md` (**Toolkit Actions**) is the worked example of the
> connect → discover → configure → wire workflow. This file generalizes it to all toolkits
> and adds the per-action detail. Endpoint specs live in
> [`api-reference.md`](./api-reference.md#custom-toolkits--tool-configurations-pills).

---

## The mental model

An action reaches an assistant through three layers:

1. **Connection** — the customer connects the toolkit in the UI with *their own* credentials
   (an Intercom access token, a Slack bot token / OAuth, a Zendesk subdomain+token, …).
   **The builder never connects a toolkit** — you have no access to the customer's secrets.
   Your job starts once it's connected.
2. **Tool configuration (a "pill")** — a saved instance of *one action* with its parameters
   decided: some **pinned** to a fixed value, some left for the **assistant** to fill, some
   pulled from **conversation context**. Creating a pill returns a stable `short_name`
   (`create_ticket_a1b2c`).
3. **The macro** — `{{ custom_tool: short_name }}` placed in the instructions/skills at the
   spot that describes *when* to do it. That's what actually exposes the action to the agent.

A macro with no pill behind it is the #1 cause of "the assistant can't do X". Always
create the pill first, then reference its exact `short_name`.

---

## How each parameter gets its value

Every action has a list of configurable params (its `tool_params`). For each one you choose:

| Mode | How | When |
|---|---|---|
| **Pinned** | put a literal in `config.params` | the value is fixed by the casuística (a channel, a ticket type, a motivo) |
| **Assistant decides** | list it in `config.dynamic_schema` (or leave an LLM-fillable param un-pinned) | the value depends on the specific conversation (a ticket title, a submotivo) |
| **From context** | pin a `{{deps.<path>}}` template in `config.params` | the value is in the conversation context (`{{deps.contact.email}}`) |

**`llm_decideable: false` = pin-only.** Some params (Slack `channel`, Intercom
`ticket_type_id`, a `state` filter, a `tag_name`) must never be guessed by the model — the
`tool_params` entry flags them `llm_decideable: false`. You **must** pin these; the assistant
is not offered them at runtime.

**`metadata_source` = its valid values are fetched live.** A param like Slack `channel`
(`metadata_source: "channels"`) or Intercom `ticket_type_id` (`metadata_source: "ticket_types"`)
has its options fetched from the connected account via the metadata endpoint — you pick from
real ids, never invent them.

**`dynamic_children`** — a parent param (e.g. `ticket_type_id`) whose choice unlocks a second
layer of configurable attributes (the ticket type's Motivo/Submotivo). Fetch them with the
child `metadata_source` once the parent is chosen.

**Conditional attributes.** A `dynamic_schema` attribute can depend on the value of a sibling
list attribute — add `condition: {"parent_key": "<parent attr name>", "value": "<parent option
name>"}`. The attribute then only applies when the parent equals that value (a *Submotivo Retiros
Ecuador* applies only when *Motivo* is *"Retiros Ecuador"*). The service doesn't expose these
dependencies — the configuration replicates them — so set the condition explicitly. It works whether
the parent is pinned or assistant-decided; the pinned `"<id>:<label>"` value is matched by id or
label. The deep dive below is the canonical example.

**`access_check`** — a param (Google Sheets `spreadsheet_id`) whose value must pass a live
connectivity check before the action can work. The same check is exposed as a metadata type,
so verify programmatically **before** creating the pill (see the Google Sheets section).

**Optional static params with an on/off state.** A param like Notion's `page_content` has three
states: pinned (a fixed body/template in `params`), assistant-written (just leave it out), or
**off** — list its key in the `__empty_fields__` meta (base64 JSON array in `params`) to disable
it entirely. A `hintable` param also accepts an operator hint via the `__param_hints__` meta
(base64 JSON `{param_key: hint}`) that guides the assistant when it writes the value.

**`unsupported: true` children.** Some dynamic children exist upstream but cannot be written by
the toolkit (Notion `relation`/`people`/`formula`/rollup/… properties). The metadata endpoint
returns them flagged `unsupported` with a reason — NEVER put them in `params` or
`dynamic_schema`; they exist in the response so you can tell the customer why that field can't
be filled.

---

## The discovery & verification loop

Run these (all accept the project `sbs_` token) instead of guessing:

```bash
# 1. Is the toolkit connected? (prerequisite — grab connected_account_id)
GET /projects/{pid}/custom-toolkits/INTERCOM_TICKETS/status

# 2. What actions does it expose + their configurable schema?
GET /projects/{pid}/custom-toolkits/INTERCOM_TICKETS/actions

# 3. Live options for a select/dynamic param
GET /projects/{pid}/custom-toolkits/INTERCOM_TICKETS/metadata/ticket_types
GET /projects/{pid}/custom-toolkits/INTERCOM_TICKETS/metadata/ticket_type_attributes?ticket_type_id=123

# 4. After configuring — is this pill actually valid?
GET /projects/{pid}/tool-configurations/{config_id}/schema     # per-attribute + issues[]
GET /projects/{pid}/tool-configuration-audit                   # every misconfigured pill
GET /projects/{pid}/custom-tool-usages                         # which macro is used where
```

A pill is **broken** when a required attribute is left empty — it fails *silently* at call
time (e.g. Intercom returns `400 Missing required attributes`). The `schema` and
`tool-configuration-audit` endpoints surface exactly these before they hit a customer.

---

## Catalog of supported toolkits & actions

Slugs in **bold** are the `tool_slug` you pass to `POST /tool-configurations`.

### Intercom Tickets — `INTERCOM_TICKETS` (api_key)
Create and look up Intercom support tickets. Credentials: Intercom access token
(scopes: read/write tickets; + read/write conversations to link a ticket to the chat;
+ read users to resolve an email).

| Action | What it does | Key params |
|---|---|---|
| **`INTERCOM_TICKETS_CREATE_TICKET`** | Creates a real ticket (irreversible). | `ticket_type_id` (pin-only, from `ticket_types`) · `contact_email` (usually `{{deps.contact.email}}`) · **plus the ticket type's own attributes** (Motivo/Submotivo…) — see the taxonomy section below · `title`/`description` are always LLM-written |
| **`INTERCOM_TICKETS_GET_TICKET`** | Looks up one ticket by its Inbox number. | `ticket_id` · `contact_email` |
| **`INTERCOM_TICKETS_FIND_TICKETS`** | Lists a user's tickets by email (surface what's open before creating). | `contact_email` · `state` (pin-only filter: open/closed/…/all) |

**In instructions:** *"When the user reports a failed withdrawal in Ecuador, create a ticket
with `{{ custom_tool: create_ticket_824ce }}`."* The pill pins the ticket type **and** the
Motivo; the assistant supplies the title, description, and submotivo.

### Intercom Conversations — `INTERCOM_CONVERSATIONS` (api_key)
Act on the *current* Intercom conversation and its contact.

| Action | What it does | Key params |
|---|---|---|
| **`INTERCOM_CONVERSATIONS_FIND_DUPLICATES`** | Lists the user's open conversations — call it *before* creating a ticket/handoff to avoid duplicates. | `contact_email` · `state` (pin-only) |
| **`INTERCOM_CONVERSATIONS_CLOSE_CONVERSATION`** | Closes the current conversation, optionally leaving an internal note first. | `closing_note` (optional; LLM or pinned) |
| **`INTERCOM_CONVERSATIONS_SET_HIGH_PRIORITY`** | Flags the conversation high-priority via a tag + an Intercom Workflow. | `tag_name` (pin-only — the tag your Workflow listens on) |
| **`INTERCOM_CONVERSATIONS_SET_ATTRIBUTES`** | Sets custom attributes on the conversation and/or the contact (user). | dynamic attributes (from `settable_attributes`); each carries an `attr_model` = `conversation` \| `contact`. Pin the ones that are fixed, let the assistant decide the rest |

**In instructions:** *"Before answering, check for an open case with
`{{ custom_tool: find_conversations_b1fc4 }}`; if the retiro is stuck, flag it with
`{{ custom_tool: set_high_priority_xxxx }}` and set `issue_type` = 'withdrawal' via
`{{ custom_tool: set_attrs_xxxx }}`."`

> **SET_ATTRIBUTES pitfall:** a pill with **no attributes configured** is a no-op, and an
> attribute name Intercom doesn't recognize is dropped silently. The `schema`/audit
> endpoints flag both.

### Slack — `SLACK` (bot token) · `SLACK_OAUTH` (one-click OAuth)
Same action, two connection variants (the `tool_slug` differs).

| Action | What it does | Key params |
|---|---|---|
| **`SLACK_SEND_MESSAGE`** / **`SLACK_OAUTH_SEND_MESSAGE`** | Posts a message to a channel. | `channel` (pin-only, from `channels`) · `mentions` (pin-only, from `members`, **depends on** `channel`) · `message` (LLM-written or pinned) |

Full worked example: see **Toolkit Actions** in `SKILL.md`. **In instructions:** *"When the
customer reports an outage, post a heads-up with `{{ custom_tool: notify_oncall_a1b2c }}`."*

### Zendesk — `ZENDESK` (api_key: subdomain + email + api_token)

| Action | What it does | Key params |
|---|---|---|
| **`ZENDESK_CLOSE_TICKET`** | Solves the current Zendesk ticket, optionally leaving an internal note first. | `closing_note` (optional) · required *solve fields* (from `required_solve_fields`) — some Zendesk instances force fields on solve; pin or let the assistant fill them |

### Pylon — `PYLON` (api_key: api_token + user_id)

| Action | What it does | Key params |
|---|---|---|
| **`PYLON_CLOSE_ISSUE`** | Closes the current Pylon issue, optionally leaving an internal note first. | `closing_note` (optional) · `close_state` (pin-only — the target state) |

### GU1 (KYB) — `GU1` (api_key)

| Action | What it does | Key params |
|---|---|---|
| **`GU1_GET_COMPANY`** | Reads a company's KYB status, risk score, and verification details (read-only). | `company_id` |

### Cal.com — `CAL_COM` (api_key)
Check availability and book meetings on the customer's Cal.com calendar. Credentials: a
Cal.com API key (`cal_…`, from Settings → Developer → API keys).

| Action | What it does | Key params |
|---|---|---|
| **`CAL_COM_GET_AVAILABILITY`** | Lists available slots for an event type (read-only). Slots come back grouped by date, in the resolved time zone. | `event_type_id` (pin-only, from `event_types`) · `timezone` (optional — pin an IANA zone, use context, or leave to the assistant; defaults to the calendar owner's) · `max_days_ahead` (optional pin, 1-90, default 31 — clamps how far ahead the assistant may search) · `max_slots` (optional pin, 1-60, default 60 — how many options are offered; set low, e.g. 6, for short lists) · the assistant provides the ISO date range at runtime ("next week" → dates) |
| **`CAL_COM_BOOK_MEETING`** | Books a real meeting (irreversible — sends calendar invites). | `event_type_id` (pin-only) · `attendee_email` (usually `{{deps.contact.email}}`) · `attendee_name` (pin or assistant) · `timezone` (optional) — the three are `hintable`: when assistant-decided, add per-field guidance via the `__param_hints__` meta (e.g. `attendee_name`: "ask for first and last name") · the assistant provides `start` (a slot from availability, verbatim) and optional `notes` |

**Discovery:** `GET .../custom-toolkits/CAL_COM/metadata/event_types` → `[{id, name}]` (name
includes the duration, e.g. `"Demo (30 min)"`).

**Config shape:**

```json
// GET_AVAILABILITY + BOOK_MEETING pills typically pin the same event type
{
  "params": {
    "event_type_id": "123:Demo (30 min)",
    "attendee_email": "{{deps.contact.email}}",
    "timezone": "America/Argentina/Buenos_Aires",
    "__param_hints__": "<base64 of {\"attendee_name\":\"Ask for first and last name\"}>"
  }
}
```

Notes:
- **Virtual meetings (Google Meet / Cal Video / Zoom)**: the meeting *location* is configured on
  the **event type in Cal.com**, not in the pill. With Google Meet set there (and Google Calendar
  connected in Cal.com), every booking auto-generates the Meet link: the attendee gets the invite
  by email, and the booking result's `location` carries the URL so the assistant can share it in
  the chat immediately.
- **Always wire BOTH pills together**: availability first, then booking. The booking `start`
  must be a slot the availability action returned — the runtime converts it to UTC and the
  tool description forbids invented times.
- Same-slot booking retries are deduped; a different slot or attendee books normally.
- In instructions: *"To schedule a demo, check slots with `{{ custom_tool: check_avail_a1b2c }}`,
  offer them, and once the user confirms one, book it with `{{ custom_tool: book_demo_c3d4e }}`."*

### Notion Databases — `NOTION_DATABASES` (api_key)
Add entries (pages) to **existing** Notion databases — it never creates databases. Credentials:
a Notion internal integration token (`secret_`/`ntn_`); each target database must be explicitly
**shared with the integration** in Notion (⋯ → Connections), or it won't appear in `databases`.

| Action | What it does | Key params |
|---|---|---|
| **`NOTION_DATABASES_ADD_ENTRY`** | Creates a real entry/page in a database (irreversible). | `database_id` (pin-only, from `databases`, stored `"<id>:<label>"`) · **the database's own properties** as dynamic children (from `database_properties?database_id=<id>`) · `page_content` (optional page body — pin it, let the assistant write it, or turn it off) |

**Discovery:**

```bash
GET .../custom-toolkits/NOTION_DATABASES/metadata/databases                         # only DBs shared with the integration
GET .../custom-toolkits/NOTION_DATABASES/metadata/database_properties?database_id=<id>
```

Property descriptors map Notion types → config types: `title` (required; usually
assistant-decides), `rich_text`/`url`/`email`/`phone_number` → text, `number` → typed number,
`date` → typed date, `checkbox` → boolean, `select`/`status` → select with options,
`multi_select` → multi-select. Entries flagged `unsupported: true` (relation, people, formula,
rollup, …) cannot be written — skip them.

**Config shape:**

```json
{
  "params": {
    "database_id": "1f3b2c…:Leads CRM",
    "Fuente": "optid123:WhatsApp",
    "__preconfigured_types__": "<base64 of {\"Fuente\":\"select\"}>",
    "__param_hints__": "<base64 of {\"page_content\":\"Summarize the request in 2-3 lines\"}>"
  },
  "dynamic_schema": [
    { "key": "Name", "name": "Name", "type": "text", "data_type": "title", "required": true },
    { "key": "Estado", "name": "Estado", "type": "select", "data_type": "status",
      "options": [ {"id": "…", "name": "Nuevo"}, {"id": "…", "name": "Contactado"} ] },
    { "key": "Email", "name": "Email", "type": "text", "data_type": "email" }
  ]
}
```

Notes:
- Pinned `select`/`status` values are `"<optionId>:<optionLabel>"`; pinned `multi_select` is a
  comma-separated list of option ids (+ an optional `__<key>_labels__` display companion).
  Record their types in `__preconfigured_types__` so the runtime builds the right payload.
- **Page body (`page_content`)**: pin a fixed text/`{{deps.*}}` template in `params`; leave it
  out entirely → the assistant may write the body (add a `__param_hints__` hint to guide it);
  or disable it with `"__empty_fields__": "<base64 of [\"page_content\"]>"`.
- Assistant-decides `date` properties must be ISO 8601 — the runtime already instructs the
  model, no config needed.

**In instructions:** *"When the visitor qualifies as a lead, register them with
`{{ custom_tool: add_lead_9f3a1 }}`."* The pill pins the database and any fixed properties; the
assistant fills name/email/status per conversation.

### Google Sheets — `GOOGLE_SHEETS` (toggle — server-side service account)
Append rows to / look up values in a Google Sheet. No customer credentials: the customer just
**enables** the toolkit, then shares each target spreadsheet as **Editor** with the platform's
service-account email. Only the **first sheet (tab)** is used; its **header row (row 1)**
defines the columns and must pre-exist.

| Action | What it does | Key params |
|---|---|---|
| **`GOOGLE_SHEETS_ADD_ROW`** | Appends one row (irreversible). | `spreadsheet_id` (pin-only, URL or bare id — verify with `sheet_access` first) · **the sheet's columns** as dynamic children (from `sheet_columns?spreadsheet_id=<id>`) |
| **`GOOGLE_SHEETS_FIND_ROW`** | Checks whether a value exists in one column; returns `found: true/false` (+ row number). Read-only. | `spreadsheet_id` (pin-only) · `search_column` (pin-only, from `sheet_column_options?spreadsheet_id=<id>`) · `search_value` (fixed, `{{deps.contact.email}}`, or assistant-decided) |

**Discovery / access-check flow (mandatory before configuring):**

```bash
# 1. Learn the service-account email (works before any sheet is involved)
GET .../custom-toolkits/GOOGLE_SHEETS/metadata/sheet_access
#    → {configured, service_account_email}          ← ask the customer to share the
#                                                      spreadsheet as EDITOR with this email
# 2. Verify access to the specific spreadsheet (accepts full URL or bare id)
GET .../custom-toolkits/GOOGLE_SHEETS/metadata/sheet_access?spreadsheet_id=<url-or-id>
#    → {access: true, title, first_sheet, …}   or   {access: false, error: "no_access"|"not_found"|"invalid_id"}
# 3. Fetch the columns / column options
GET .../custom-toolkits/GOOGLE_SHEETS/metadata/sheet_columns?spreadsheet_id=<id>
GET .../custom-toolkits/GOOGLE_SHEETS/metadata/sheet_column_options?spreadsheet_id=<id>
```

Do **not** create the pill until `sheet_access` returns `access: true` — the runtime would fail
on every call. Save the returned `title` as the `__spreadsheet_title__` meta: it flows into the
tool's description so the model knows exactly which sheet it targets (critical when several
sheet pills coexist).

**Config shapes:**

```json
// ADD_ROW — pin the fixed/context columns, let the assistant fill the rest
{
  "params": {
    "spreadsheet_id": "https://docs.google.com/spreadsheets/d/1AbC…/edit",
    "Origen": "WhatsApp",
    "Email": "{{deps.contact.email}}",
    "__spreadsheet_title__": "Leads 2026"
  },
  "dynamic_schema": [
    { "key": "Nombre", "name": "Nombre", "type": "text", "data_type": "string" },
    { "key": "Consulta", "name": "Consulta", "type": "text", "data_type": "string",
      "hint": "One-line summary of what they asked for" }
  ]
}

// FIND_ROW — membership check against a column
{
  "params": {
    "spreadsheet_id": "1AbC…",
    "search_column": "Email",
    "search_value": "{{deps.contact.email}}",
    "__spreadsheet_title__": "Whitelist beta"
  }
}
```

Notes:
- Column keys in `params`/`dynamic_schema` are the **exact header texts** from `sheet_columns`.
- Omit `search_value` from `params` to let the assistant decide it at runtime.
- Rows are matched/written against the live header row: if the customer later renames a header,
  the ADD_ROW result includes a `dropped_columns` warning (values that no longer matched).

**In instructions:** *"Before answering pricing questions, check the beta whitelist with
`{{ custom_tool: find_row_c4d2e }}`; if `found` is false, offer the waitlist and register them
with `{{ custom_tool: add_row_88a1b }}`."*

---

## Deep dive: Intercom ticket taxonomy (Motivo / Submotivo)

This is where most misconfigurations live, so configure it deliberately.

An Intercom ticket type (e.g. *Operaciones en Ecuador*) defines a required **`Motivo`** (a
list attribute) and one **`Submotivo <X>`** per motivo, each **conditionally required** when
`Motivo == X` (a "Submotivo Retiros Ecuador" is required only when Motivo is "Retiros
Ecuador"). **Intercom's API does not expose the condition** — the configuration replicates it.

**Design rule — pin the Motivo by casuística, let the assistant pick the Submotivo.**
The motivo is usually determined by *where* the macro lives: a `retiros` skill always means
"Retiros Ecuador", a compliance instruction always means "Cuenta bloqueada / … / compliance".
Pinning it (instead of leaving it to the model) is deterministic and stops the assistant from
choosing a wrong motivo. The **submotivo** is the genuine per-conversation decision → assistant.

**Config shape for a pinned-motivo ticket pill:**

```json
{
  "params": {
    "ticket_type_id": "3050614:Operaciones en Ecuador.",
    "contact_email": "{{deps.contact.email}}",
    "Motivo": "c770c2b4-…-4f31f0:Retiros Ecuador",
    "__preconfigured_types__": "<base64 of {\"Motivo\":\"list\"}>",
    "__link_conversation__": "true",
    "__share_with_customer__": "true"
  },
  "dynamic_schema": [
    { "key": "Submotivo Retiros Ecuador", "name": "Submotivo Retiros Ecuador",
      "type": "select", "data_type": "list",
      "options": [ {"id": "…", "name": "Retiro Ecuador fallido"}, … ],
      "condition": { "parent_key": "Motivo", "value": "Retiros Ecuador" } }
  ]
}
```

Notes:
- **Pinned list values are stored `"<id>:<label>"`** (the label rides along for the UI; the
  runtime sends the bare id). Get the id+label from
  `metadata/ticket_type_attributes?ticket_type_id=<id>`.
- **Mark the submotivo conditional on its motivo** with
  `condition: {"parent_key": "<parent attribute name>", "value": "<parent option name>"}` —
  the taxonomy stays explicit and self-documenting, and a later multi-motivo pill behaves
  correctly. `parent_key` and `value` use the **names** (e.g. `"Motivo"` / `"Retiros
  Ecuador"`), not ids. The runtime matches a **pinned `"<id>:<label>"`** parent by either its
  id or its label, so a condition works whether the motivo is pinned or assistant-decided.
- **Verify:** `GET /tool-configurations/{id}/schema` should show `Motivo: preconfigured`, the
  matching `Submotivo: assistant_decides` (with its `condition`), the other submotivos
  `not_applicable`, and **0 issues**. The audit is conditional-aware — it won't false-flag a
  submotivo whose motivo can't occur.
- **Not every type requires a motivo.** Some (e.g. a "Fraude" type) mark `Motivo` optional
  (`required_to_create=false`); those pills are fine with just title/description. Trust the
  metadata `required` flag over assumptions.

---

## Gotchas learned the hard way

- **`<id>:<label>` everywhere.** `ticket_type_id`, Slack `channel`, and any pinned list
  attribute are stored as `"<id>:<label>"`. The runtime resolves the id; you don't need to
  strip it, but when you *read* a config, expect the label suffix.
- **Required-but-empty fails silently.** A missing required attribute doesn't error at
  save time — it 400s at *create* time, invisibly, for every conversation. Always run the
  `schema`/audit check after configuring a ticket/attributes pill.
- **In-use pills need approval to change.** Editing or deleting a pill whose macro appears in
  the **active or latest** version of any playbook (instructions or skills) returns **202** —
  queued for admin approval — for `sbs_` callers. *Creating* a pill, or editing one not yet
  referenced anywhere, executes directly. Check `in_use` on the list/get response first.
- **Metadata needs the connection.** The metadata endpoint reads the stored credentials; a
  `missing_scope` hint means the customer's connection lacks a scope — tell them, you can't
  fix it from here.
- **Conversation-scoped actions use context.** SET_ATTRIBUTES, SET_HIGH_PRIORITY,
  CLOSE_CONVERSATION, and ticket-linking act on the *current* conversation — `contact_email`
  is typically `{{deps.contact.email}}`, and the conversation id comes from context, not a
  param.
- **Base64 meta values are UTF-8.** `__dynamic_schema__`, `__preconfigured_types__`,
  `__empty_fields__`, `__param_hints__` are base64-encoded **UTF-8** JSON — encode accented /
  emoji attribute names as UTF-8 bytes before base64.
- **Notion: the database must be shared with the integration.** An empty `databases` list (or a
  missing database) almost always means the customer hasn't added the integration under the
  database's ⋯ → Connections. This toolkit never creates databases — the database and its
  properties must pre-exist.
- **Sheets: verify access BEFORE configuring.** `sheet_access` with the spreadsheet id must
  return `access: true` (customer shares the sheet as **Editor** with the service-account
  email). Only the first tab is used; columns = the header row. Distinct rows in one
  conversation both append (same-row retries are deduped), and FIND_ROW matching is
  case-insensitive with numeric tolerance ("500" matches a cell showing "$500.00").

---

## The wiring pattern, end to end

1. **Status** → confirm the toolkit `is_connected`; if not, ask the user to connect it and stop.
2. **Actions + metadata** → learn the action's params and fetch live ids.
3. **Create the pill** → `POST /tool-configurations` with the params pinned per the casuística
   (pin the deterministic stuff, leave the per-conversation stuff to the assistant). Read the
   `short_name`.
4. **Verify** → `GET /tool-configurations/{id}/schema` shows 0 issues.
5. **Wire the macro** → put `{{ custom_tool: <short_name> }}` in the instruction/skill exactly
   where the situation is described; if the assistant writes any text (a ticket title, a Slack
   message), say there how it should read. Confirm with the user, then re-read to check the
   `short_name` is spelled exactly.
