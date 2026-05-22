# Studio Chat Eval API Reference

All endpoints require authentication. The `qa.py` script handles auth automatically via `$STUDIO_API_TOKEN`.

In paths, `{base_id}` is the playbook base ID (stable across versions).

## Contents

- [Create Test Case](#create-test-case)
- [Batch Create Test Cases](#batch-create-test-cases)
- [List Test Cases](#list-test-cases)
- [Get Test Case](#get-test-case)
- [Update Test Case](#update-test-case)
- [Delete Test Case](#delete-test-case)
- [Trigger Eval Run](#trigger-eval-run)
- [List Eval Runs](#list-eval-runs)
- [Get Eval Run](#get-eval-run)
- [Get Run Results](#get-run-results)
- [Cancel Eval Run](#cancel-eval-run)
- [Get Single Result](#get-single-result)
- [Chat with Assistant](#chat-with-assistant)
- [Dry-Run a Case](#dry-run-a-case)
- [Get Active Version](#get-active-version)
- [List Playbooks](#list-playbooks)
- [Playbook Override](#playbook-override)
- [Tool Mocks during chat](#tool-mocks-during-chat)

---

## Create Test Case

`POST /playbooks/{base_id}/eval-cases`

Create a single eval test case for a playbook.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique name (lowercase with dashes) |
| `scenario` | string | Yes | User scenario description for the simulator |
| `termination` | string | Yes | Expected outcome condition |
| `first_message` | string | No | Exact first message (LLM generates if omitted) |
| `max_turns` | int | No | Max turns (1-50, default: 10) |
| `assertions` | array | No | `[{"criteria": "..."}]` — LLM-evaluated criteria |
| `assertion_tags` | array | No | `["tag1", "tag2"]` — tags the assistant should apply |
| `tool_mocks` | object | No | Stub specific tools with canned responses for this case. See [Tool Mocks](#tool-mocks) below. |
| `user_context` | object | No | Per-case user context; merges over the run-level `user_context` (case wins). Use for case-specific user attributes or `eval_overrides`. |

**Response:** `EvalCase` object with `id`, `created_at`, `is_enabled`, etc.

### Tool Mocks

`tool_mocks` is a map of tool name → rule (or list of rules). Each rule sets one match condition (`match_kind`) and exactly one payload (`return_value` xor `error`).

**Match conditions:**

| `match_kind` | Required field | Fires when |
|---|---|---|
| `any` | — | every call to this tool |
| `call_ordinal` | `call_ordinal: int` (1-indexed) | the Nth call to this tool |
| `args_match` | `match_args: dict` | call args ⊇ `match_args` (subset filter) |

**Payload:** exactly one of `return_value` (any JSON) OR `error` (string — raised as a tool error).

**Example case body with mocks:**

```json
{
  "name": "refund-flow",
  "scenario": "...",
  "termination": "...",
  "tool_mocks": {
    "lookup_order": [
      {"match_kind": "args_match", "match_args": {"order_id": "ORD-123"}, "return_value": {"status": "delivered"}},
      {"match_kind": "any", "error": "Order not found"}
    ],
    "process_refund": {"match_kind": "any", "return_value": {"refund_id": "RFND-999"}}
  }
}
```

**Exhaustive contract:** once a tool has any rule, every call to that tool during the run MUST match a rule. Unmatched calls fail the run with `no mock matched call #N for tool …` — they do NOT fall through to the real implementation. Always include an `any` catch-all if call counts are uncertain.

Tools not listed in `tool_mocks` are unaffected — they call the real implementation.

---

## Batch Create Test Cases

`POST /playbooks/{base_id}/eval-cases/batch`

Create up to 100 test cases in a single request.

**Request body:**

```json
{
  "cases": [
    {
      "name": "case-name",
      "scenario": "...",
      "termination": "...",
      "assertions": [{"criteria": "..."}]
    }
  ]
}
```

Maximum 100 cases per request. Invalid names are skipped. Returns 400 only if ALL cases fail.

**Response:** `list[EvalCase]` — the successfully created cases.

---

## List Test Cases

`GET /playbooks/{base_id}/eval-cases`

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled_only` | bool | false | Only return enabled cases |

**Response:** `list[EvalCase]` ordered by name.

---

## Get Test Case

`GET /eval-cases/{case_id}`

**Response:** `EvalCase` object. Returns 404 if not found.

---

## Update Test Case

`PATCH /eval-cases/{case_id}`

Partial update — only include fields to change.

**Request body:** Any fields from `EvalCaseCreate` plus `is_enabled: bool`.

**Response:** Updated `EvalCase`.

---

## Delete Test Case

`DELETE /eval-cases/{case_id}`

**Response:** 204 No Content. Returns 404 if not found.

---

## Trigger Eval Run

`POST /playbooks/{base_id}/eval-runs`

Triggers an evaluation run in the background. Returns immediately with a pending run.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `playbook_id` | string | Yes | Specific playbook version ID to test |
| `name` | string | No | Optional human-readable label for the run (≤255 chars). Surfaced in run list / diff page. |
| `trigger_source` | string | No | `api` (default), `ui`, `cli`, `cron` |
| `user_context` | object | No | Context dict passed to the agent (simulates user attributes). Use the `eval_overrides.*` sub-namespace for ground-truth values judges read directly. |
| `case_ids` | array | No | Explicit list of case IDs to run. When set, ONLY these cases execute and `is_enabled` is IGNORED — pick a subset (or a disabled case) without flipping flags. Unset ⇒ run every enabled case. Empty list ⇒ 400. Unknown IDs ⇒ 404. |
| `concurrency` | int | No | Cases to run in parallel (1..5, default 1). `1` = sequential. Higher fans out via a thread pool; beyond 5 rate limits dominate. |
| `model` | string | No | Override the **assistant** model for this run. See [Model strings](#model-strings) below. |
| `simulator_model` | string | No | Override the simulator LLM. Default: `EVAL_SIMULATOR_MODEL` env (typically `anthropic/claude-sonnet-4`). |
| `judge_model` | string | No | Override the LLM judge for `text`-type assertions. Structured assertions ignore this. Default: `EVAL_EVALUATOR_MODEL` env (typically `openai/gpt-4o`). |
| `playbook_override` | object | No | In-memory playbook field overrides (see [Playbook Override](#playbook-override)). Requires admin / API-key auth. |

**Response:** `EvalRun` with `status: "pending"`.

The run executes asynchronously:
1. Status changes to `running` when execution starts
2. `passed_cases` and `failed_cases` update as each case completes
3. Status changes to `completed` (or `failed`/`cancelled`) when done

### Model strings

`model`, `simulator_model`, and `judge_model` all accept the same OpenRouter-compatible syntax:

- **Single model**: `provider/model_id` — e.g. `openai-direct/gpt-4o-mini`, `anthropic/claude-sonnet-4`. A `provider/` prefix is required; bare `gpt-4o-mini` ⇒ 422.
- **Fallback**: `primary{timeout}fallback` — primary first; on timeout (seconds) the second model takes over. Example: `groq/llama-3.3-70b-versatile{8}openai-direct/gpt-4o-mini`.
- **A/B experiment**: `modelA:50,modelB:50` — conversation_id hashed to deterministically assign each case to one variant. Percentages must sum to 100.

Empty / whitespace ⇒ field treated as unset (defaults take over). Malformed input ⇒ 422.

**Recommended slugs** (these are actually in use across the stack — invented slugs will 422):

| Family | Slug | Notes |
|---|---|---|
| Anthropic Sonnet | `anthropic/claude-sonnet-4.6` | Newest. Best general assistant. |
| Anthropic Sonnet | `anthropic/claude-sonnet-4.5` | One rev behind. |
| Anthropic Sonnet | `anthropic/claude-sonnet-4` | Default eval **simulator**. |
| Anthropic Sonnet | `anthropic/claude-3.5-sonnet` | Stable cheap baseline. |
| Anthropic Haiku | `anthropic/claude-haiku-4.5` | Fast / cheap. |
| OpenAI GPT-5 | `openai/gpt-5.4` | Newest flagship. |
| OpenAI GPT-5 | `openai/gpt-5.4-mini` | GPT-5 mini. Supports `[reasoning=…]`. |
| OpenAI GPT-5 | `openai/gpt-5.2-chat` | Stable GPT-5 chat. |
| OpenAI GPT-4 | `openai/gpt-4.1-mini` | Solid mid-tier. |
| OpenAI GPT-4 | `openai/gpt-4.1-nano` | Smallest GPT-4.1. |
| OpenAI GPT-4o | `openai/gpt-4o` | Default eval **judge**. |
| OpenAI GPT-4o | `openai/gpt-4o-mini` | Cheap judge / assistant. |
| OpenAI direct | `openai-direct/gpt-4o` | Direct provider (lower latency, different billing). |
| OpenAI direct | `openai-direct/gpt-4o-mini` | Direct-provider 4o-mini. |
| Google Gemini | `google/gemini-2.5-flash` | Newest stable Flash. |
| Google Gemini | `google/gemini-2.5-flash-lite` | Cheaper Flash. |
| Google Gemini | `google/gemini-2.0-flash-001` | Previous Flash gen. |
| Google Gemini | `google/gemini-3-flash-preview` | Gemini 3 preview (may change). |

**Reasoning suffix** (GPT-5 family only): append `[reasoning=X]` where X ∈ `{none, low, medium, high, xhigh}`. Example: `openai/gpt-5.4-mini[reasoning=medium]`. `none` disables reasoning entirely.

---

## List Eval Runs

`GET /playbooks/{base_id}/eval-runs`

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number (1-indexed) |
| `page_size` | int | 10 | Items per page (1-100) |

**Response:**

```
items               array   List of EvalRunWithDetails
total               int     Total run count
page                int     Current page
page_size           int     Items per page
total_pages         int     Total pages
```

Each run includes: `playbook_name`, `playbook_version`, `status`, `passed_cases`, `failed_cases`, `total_cases`.

---

## Get Eval Run

`GET /eval-runs/{run_id}`

**Response:** `EvalRunWithDetails` with playbook name and version.

**Run status values:** `pending`, `running`, `completed`, `failed`, `cancelled`.

---

## Get Run Results

`GET /eval-runs/{run_id}/results`

Per-case results with assertion details and the simulated conversation.

**Response:** `list[EvalResultWithCase]`

Each result contains:

```
id                      string  Result ID
case_id                 string  Test case ID
case_name               string  Test case name
case_scenario           string  Scenario description
status                  string  "passed", "failed", or "error"
total_assertions        int     Total assertion count
passed_assertions       int     Passed count
failed_assertions       int     Failed count
assertion_results       array   Per-assertion details
  criteria              string  The criteria evaluated
  passed                bool    Whether it passed
  explanation           string  LLM explanation of why
tag_results             object  {tag_name: bool} — tag assertion results
conversation            array   The simulated conversation
  role                  string  "user" or "assistant"
  content               string  Message text
error_message           string  Error details (if status is "error")
```

---

## Cancel Eval Run

`POST /eval-runs/{run_id}/cancel`

Cancel a pending or running eval. The runner stops after the current case completes.

Returns 400 if run is already completed, failed, or cancelled.

**Response:** Updated `EvalRunWithDetails` with `status: "cancelled"`.

---

## Get Single Result

`GET /eval-results/{result_id}`

**Response:** `EvalResult` (same fields as in run results, without case_name/case_scenario).

---

## Chat with Assistant

`POST /playbooks/{base_id}/active/chat`

Send a message to the active version of a playbook. Multi-turn conversations are supported
by reusing the same `conversation_id`.

**Note:** `conversation_id` is an arbitrary string. The skill generates one automatically
(e.g., `qa_a1b2c3d4e5f6`). Use the same ID for follow-up messages.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conversation_id` | string | Yes | Conversation identifier (reuse for multi-turn) |
| `user_message` | string | Yes | The user's message |
| `context` | object | No | User context dict (email, plan, etc.) |
| `tags` | array | No | Tags to associate with the conversation |
| `include_citations` | bool | No | Return KB citation details in response (default: false) |
| `playbook_override` | object | No | In-memory playbook field overrides (see [Playbook Override](#playbook-override)). Forces preview+eval mode for the conversation. Requires admin / API-key auth. |
| `tool_mocks` | object | No | Per-request tool-call mocks. Same shape as `EvalCase.tool_mocks` — see [Tool Mocks during chat](#tool-mocks-during-chat) below. Forces preview+eval mode. Requires admin / API-key auth. |

**Response:**

```
explanation             string  Agent reasoning summary
events                  array   Messages, labels, handoffs, notes
  event_type            string  "message", "label", "handoff_agent", etc.
  data                  object  Event-specific payload
tool_calls              array   Tool calls made during execution
  name                  string  Tool name (e.g., "search_knowledge_base", "load_skill")
  arguments             string  JSON string of tool arguments
  result                string  Tool execution result
  tool_type             string  "kb_search", "custom", "list_agents", "list_teams", "list_kbs"
  is_mocked             bool    True when the result came from a tool_mocks rule (stub).
                                False (default) for real tool executions.
citations               array   KB citations (only if include_citations=true)
  citation_id           string  Reference ID (used as [[id]] in message text)
  kb_id                 string  Knowledge base ID
  item_id               string  Item ID within the KB
  content               string  Retrieved snippet content
  file_name             string  Source file name (if applicable)
elapsed_time_ms         int     Response time in milliseconds
first_seen              bool    True if this is the first message in the conversation
```

---

## Dry-Run a Case

Runs a **single, unsaved** `EvalCase` against a playbook version (with optional `playbook_override`) without persisting either to storage. State lives in process for ~30 minutes and is polled by ID. Step 5 of the [QA practice workflow](../SKILL.md#qa-practice-workflow-read-this-first).

Admin / API-key only.

### Start a Dry-Run

`POST /playbooks/{base_id}/eval-cases/dry-run`

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `case` | object | Yes | An `EvalCaseCreate` payload (`name`, `scenario`, `termination`, `max_turns`, `assertions`, `tool_mocks`, `user_context`). Same shape as [Create Test Case](#create-test-case). |
| `playbook_id` | string | Yes | Specific playbook version to simulate against. Must belong to `{base_id}`. |
| `playbook_override` | object | No | Optional [Playbook Override](#playbook-override) applied to the playbook for this dry-run only. Lets you iterate on instructions / skills against an unsaved case simultaneously. |

**Response:** `{"dry_run_id": "..."}` (202 Accepted). Poll the status endpoint until terminal.

### Get Dry-Run State

`GET /eval-cases/dry-run/{dry_run_id}`

**Response (`DryRunState`):**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `pending`, `running`, `completed`, `failed`, `cancelled`. |
| `turns` | array | Conversation turns captured so far (same shape as eval result `conversation`). |
| `assertion_results` | array | Per-assertion grading (populated when status reaches `completed`). |
| `terminated` | bool | Whether the simulator hit the termination condition. |
| `termination_reason` | string | The simulator's reason for stopping. |
| `error_message` | string | Set when `status == failed`. |

Returns 404 if the dry-run ID is unknown or expired.

### Cancel a Dry-Run

`POST /eval-cases/dry-run/{dry_run_id}/cancel`

Signals the runner to stop on the next turn boundary. In-flight turns finish but no new turn is started.

**Response:** Updated `DryRunState`.

---

## Get Active Version

`GET /playbooks/{base_id}/active`

Returns the currently active playbook version. Use this to get the `playbook_id` for triggering eval runs.

**Response:** Playbook object with `id` (the version ID), `version_number`, `name`, etc.

---

## List Playbooks

`GET /projects/{pid}/playbooks`

List all playbooks (assistants) in a project. Use this to discover `base_id` values.

Replace `{pid}` with `$STUDIO_PROJECT_ID`.

**Response:** List of playbook objects, each with `id`, `base_id`, `name`, `version_number`.

---

## Playbook Override

Both `POST /playbooks/{base_id}/active/chat` and `POST /playbooks/{base_id}/eval-runs` accept an optional `playbook_override` object that replaces fields on the saved playbook in memory for that call only. No new playbook version is created.

**Use this to iterate on instructions or skills without persisting a draft version.** Requires admin or API-key authentication (sandbox `sbs_` keys count as admin).

**Override shape:**

| Field | Type | Replaces |
|-------|------|----------|
| `content` | string | Main playbook instructions (free-text). |
| `skills` | list **or** patch object | List form: full replace (drop saved skills, use exactly these; `[]` disables all). Patch form: `{add, replace, remove}` — surgical edit on top of the saved skills. See below. |
| `examples` | list of objects | Global reference examples. |
| `kb_ids` | list of strings | Knowledge base IDs. `[]` disables all KBs. |
| `api_tools` | list of strings | API tool IDs. `[]` disables all tools. |
| `enrichment_tool_ids` | list of strings | Auto-run-at-start tool IDs. |

**Skills patch shape** (object form of `skills`):

```json
{
  "skills": {
    "remove": ["legacy-flow"],
    "replace": [
      {"name": "refund-flow", "description": "...", "content": "..."}
    ],
    "add": [
      {"name": "english-only", "description": "...", "content": "..."}
    ]
  }
}
```

Operators are applied in order `remove` → `replace` → `add`. The BE returns **422** for: `remove` / `replace` of an unknown name, `add` of a name that already exists after `remove` ran, or duplicate names within one operator list. (Strict validation — typos surface immediately.) `remove: [X]` + `add: [{name:X, …}]` of the same name **is** allowed.

**Skill object shape** (used in `skills` list form, in `replace`, and in `add`):

```json
{
  "name": "english-only",
  "description": "Force English replies regardless of input language",
  "content": "Reply only in English even when the customer writes in another language.",
  "examples": [],
  "order": 0
}
```

Only `name`, `description` and `content` are required. The saved-version skill row also has a `trigger` field — the override endpoint omits it because the agent's system prompt only surfaces `name` + `description` for skill discovery, never `trigger`.

**Semantics:**

- Each field is independent. Omit a field and the saved playbook's value is used.
- Lists are **replaced wholesale**, not merged.
- Chat conversations using an override are forced into `is_preview=true` + `is_eval=true`, so they don't pollute production analytics, the sticky-model cache, or chatlogs.
- Override skills have `is_active` forced to `true` server-side so they always load.

**Example chat request:**

```json
POST /playbooks/PB_BASE_ID/active/chat
{
  "conversation_id": "qa_iter_001",
  "user_message": "I want a refund",
  "playbook_override": {
    "content": "You are a CX assistant. Be terse. Always reply in English.",
    "skills": [
      {
        "name": "refund-flow",
        "description": "Handle refund requests",
        "content": "Ask for order id, then check eligibility..."
      }
    ],
    "kb_ids": ["kb-uuid-a"]
  }
}
```

**Example eval-run request:**

```json
POST /playbooks/PB_BASE_ID/eval-runs
{
  "playbook_id": "PB_VERSION_ID",
  "playbook_override": {
    "content": "...candidate prompt to validate against all cases..."
  }
}
```

---

## Tool Mocks during chat

`POST /playbooks/{base_id}/active/chat` accepts an optional `tool_mocks` field that stubs specific tool calls for that single chat request. Same wire shape and semantics as `EvalCase.tool_mocks` — the chat handler bridges into the same wrapper plumbing the eval runner uses, so once installed, every tool dispatch goes through the match-and-mock pipeline.

**Properties:**

- Admin / API-key only (`require_admin` gate).
- Forces `is_eval=true` and `is_preview=true` so the conversation is excluded from chatlogs, sticky-model assignment, and production analytics.
- Mocked calls surface as `tool_calls[i].is_mocked = true` in the response so the caller can tell stubbed responses apart from real ones.
- Composes with `playbook_override` — both can be set on the same request to test a variant playbook against mocked tool responses.
- Exhaustive per tool: once a tool is in `tool_mocks`, every call to it MUST match a rule. A missing match raises an explicit error (`no mock matched call #N for tool X`) rather than silently falling through to the real tool.

### What can be mocked

Anything that dispatches through the agent's toolset wrapper:

- **Composio integration tools** — Uppercase `TOOLKIT_ACTION` slugs: `SLACK_SEND_MESSAGE`, `CAL_POST_NEW_BOOKING_REQUEST`, `GMAIL_SEND_EMAIL`, etc. The available set depends on the project's `SUPPORTED_TOOLKITS` config.
- **Custom API tools** registered on the playbook (`api_tools`).
- **Custom toolkit tools** (the in-house `CUSTOM_TOOLKIT_REGISTRY`).
- **Built-in tools**: `search_knowledge_base`, `load_skill`, `list_agents`, `list_teams`, `list_kbs`.

**Cannot be mocked** (not dispatched as tool calls):

- **Agent events** (`message`, `note`, `label`, `priority`, `handoff_agent`, `handoff_team`) — these are items inside the LLM's structured output. To validate them, use the matching structured assertions in evals.
- **Enrichment tools** (`enrichment_tool_ids`) — run BEFORE the agent's first turn; the wrapper doesn't exist yet.

### Wire shape

```json
POST /playbooks/{base_id}/active/chat
{
  "conversation_id": "qa_repro_001",
  "user_message": "Quiero un reembolso del pedido ORD-99999",
  "include_citations": true,
  "tool_mocks": {
    "lookup_order": {"match_kind": "any", "error": "Order not found"},
    "SLACK_SEND_MESSAGE": {"match_kind": "any", "return_value": {"ok": true, "ts": "1234.5678"}},
    "search_knowledge_base": [
      {"match_kind": "args_match", "match_args": {"query": "refund"}, "return_value": [{"title": "Refund policy", "snippet": "..."}]},
      {"match_kind": "any", "return_value": []}
    ]
  }
}
```

Combine with `playbook_override` to test an unsaved variant against mocked tools in a single request:

```json
{
  "conversation_id": "qa_repro_002",
  "user_message": "Quiero un reembolso del pedido ORD-99999",
  "playbook_override": {
    "content": "You are a refund specialist. ALWAYS verify the order first via lookup_order."
  },
  "tool_mocks": {
    "lookup_order": {"match_kind": "any", "error": "Order not found"}
  }
}
```

### Why not on `POST /eval-runs`?

Run-level `tool_mocks` is intentionally not supported. The right place for deterministic mocks across an eval run is the **case body itself** (`EvalCase.tool_mocks`) — that way the mocks travel with the case and the run trigger stays a thin dispatch. The CLI surfaces this as a 4xx-style error on `qa.py runs create --tool-mocks-file`. For chat-only iteration, the field above is correct; for runs, put the mocks on the cases.

