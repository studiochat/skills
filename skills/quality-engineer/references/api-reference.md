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
- [Get Active Version](#get-active-version)
- [List Playbooks](#list-playbooks)

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

**Response:** `EvalCase` object with `id`, `created_at`, `is_enabled`, etc.

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
| `trigger_source` | string | No | `api` (default), `ui`, `cli` |
| `user_context` | object | No | Context dict passed to the agent (simulates user attributes) |

**Response:** `EvalRun` with `status: "pending"`.

The run executes asynchronously:
1. Status changes to `running` when execution starts
2. `passed_cases` and `failed_cases` update as each case completes
3. Status changes to `completed` (or `failed`/`cancelled`) when done

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

**Response:**

```
explanation             string  Agent reasoning summary
events                  array   Messages, labels, handoffs, notes
  event_type            string  "message", "label", "handoff_agent", etc.
  data                  object  Event-specific payload
tool_calls              array   Tool calls made during execution
citations               array   KB citations (if include_citations=true)
elapsed_time_ms         int     Response time in milliseconds
first_seen              bool    True if this is the first message in the conversation
```

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
