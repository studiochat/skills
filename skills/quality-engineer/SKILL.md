---
name: quality-engineer
description: >
  Test and evaluate AI assistant behavior. Create test cases, run evaluations,
  analyze results, simulate conversations, and compare playbook versions.
  Also the end-to-end loop to debug and fix incorrect assistant behaviour
  starting from a conversation ID: root-cause it, validate a fix via overrides
  without saving a version, hand off to the human, and add regression evals.
  Use when asked to test an assistant, create QA scenarios, run evals,
  check assertion pass rates, verify assistant behavior, or investigate a
  conversation where the assistant misbehaved.
---

# Quality Engineer

Create test cases, run evaluations, and simulate conversations to verify AI assistant behavior. All API calls are authenticated automatically via environment variables. The API base URL (`https://api.studiochat.io`) is hardcoded in the scripts.

## Key Terminology

**Assistants and playbooks are the same concept.** In the API, the term "playbook" is used
everywhere — but users refer to them as "assistants," "bots," or "agents." When the user
mentions any of these, they mean a playbook.

**Playbook IDs:**
- `playbook_base_id` — stable ID across all versions of an assistant. Use this for case management.
- `playbook_id` — ID of a specific version. Use this when triggering a run (you choose which version to test).

## Setup

Set the following environment variables before using the scripts:

```bash
export STUDIO_API_TOKEN="sbs_your_api_key_here"
export STUDIO_PROJECT_ID="your-project-uuid"
# Optional — point the scripts at a different backend (e.g. local dev):
# export STUDIO_API_URL="http://localhost:8000"
```

API keys are available by request from the Studio Chat team at hey@studiochat.io.

---

## QA Practice Workflow (read this first)

The typical request looks like: **"se quejaron de la conversación X — investigá y arreglá"**. The skill is built around that loop:

```
Complaint → Root cause → Validated fix → New version (applied by the human) → Eval coverage
```

Reproduce the complaint, understand what drove the behaviour, fix it via in-memory overrides, hand the validated fix to the human (who applies the new version), and close the loop with regression evals.

There are four **user checkpoints** where you MUST stop and interact — pinning down the incorrect behaviour (Step 3), feedback on the proposed fix (Step 5), the mock question (Step 6), and waiting for the human to apply the new version (Step 8) — plus the full-suite offer at the end (Step 9). Don't barrel through them.

### Step 1 — Pull the full conversation (cross-skill: data-expert)

Everything starts from a **conversation ID** where the assistant did something wrong. Before touching the assistant, download the WHOLE conversation — the [data-expert](../data-expert/SKILL.md) skill is the right tool for this (see its conversation deep-dive patterns). You need:

- every message, event (`label` / `note` / `handoff_*` / `priority`) and tool call with arguments + results
- the **playbook version** that was active
- the **model** that served the conversation (sticky models / A/B splits mean different conversations may run different models — you'll need this in Step 4)
- the **user_context** that was passed in

Don't try to diagnose from a screenshot or a vague summary — read what actually happened.

### Step 2 — Pull the assistant as it was (cross-skill: builder)

Download the full content of the **exact playbook version that handled the conversation** — not the latest one: instructions, skills (casuísticas), KB list, api_tools. The [builder](../builder/SKILL.md) skill covers playbook version management. Diagnosing against the wrong version is a classic trap — the instruction you're reading may not have existed yet, or the bug may already be fixed.

### Step 3 — Pin down the incorrect behaviour (USER CHECKPOINT if unclear)

This step must end with explicit agreement on **what exactly the assistant did wrong**.

- If the user already said it ("prometió un reembolso fuera de política"), confirm it by pointing at the exact turn(s) in the conversation.
- If they didn't, build hypotheses from the transcript and **ask with hints**: «¿Qué fue lo que pasó acá? ¿Te quejás de que prometió X, o de que no derivó cuando pasó Y?» — offer the 2-3 most plausible candidates you found.

Don't move forward on a guess: the rest of the workflow optimizes for making this specific behaviour not happen again.

### Step 4 — Root-cause: explain WHY it behaved that way

To know **why** the assistant did what it did, you need to understand how Studio Chat assembles the agent at runtime:

| Layer | What it is | How it loads |
|---|---|---|
| **Playbook instructions** (`content`) | The base system prompt for the agent. Free-form text — sets persona, tone, hard rules. | Stored on the saved `Playbook` row; injected into the system prompt at compile time. |
| **Skills (casuísticas)** | Per-scenario instruction blocks the agent loads on demand via the `load_skill` tool. Each skill has `name`, `description`, and `content`. Only `name + description` are surfaced to the LLM during skill discovery — the `content` is fetched only when `load_skill` is called. | Stored on the playbook version; the compiler attaches them to the agent. |
| **Knowledge bases (`kb_ids`)** | Indexed snippets the agent searches via `search_knowledge_base`. Returns ranked passages with citation IDs (`[[abc12]]`) inlined in the assistant's response. | Configured on the playbook; the agent calls `search_knowledge_base` when it needs grounded info. |
| **API tools / toolkits** | Real-world actions: Composio integrations (`SLACK_SEND_MESSAGE`, `CAL_POST_NEW_BOOKING_REQUEST`, `GMAIL_*`), custom API tools, custom toolkits. | Registered on the playbook's `api_tools` / `integrations`; the wrapper dispatches calls at runtime. |
| **Examples** | Reference conversations the agent learns from. | Stored on the playbook; injected into the system prompt. |
| **Enrichment tools** | Run BEFORE the agent's first turn (e.g. fetch user profile, lookup order). Their result lands in `context.enrichment`. | Configured via `enrichment_tool_ids`; not mockable through `tool_mocks`. |

Whatever the assistant did wrong, the root cause lives in one (or a few) of these layers. With the conversation (Step 1) and the assistant content (Step 2) side by side, classify it:

| Root cause | What it looks like | Typical fix |
|---|---|---|
| **Wrong instruction** | An instruction/skill explicitly drives the bad behaviour (or forbids the right one). | Correct the instruction text. |
| **Misinterpreted instruction** | The instruction exists but is ambiguous, contradicts another one, or the **model** that served the conversation (Step 1) is too weak to follow it reliably. | Disambiguate the wording, resolve the contradiction, or revisit the model choice. |
| **Missing instruction** | Nothing covers the scenario, so the model fell back to its **native behaviour** (over-helpful, invents policy, answers out of scope). | Add the missing specificity — an instruction or a new casuística. |
| **Wrong layer** | Instructions are fine but: the skill description didn't trigger `load_skill`, the KB search returned irrelevant passages, or a tool returned unexpected data. | Fix the skill description / KB content / tool — not the prompt. |

Quote the exact instruction(s) — or their absence — that explain the behaviour. "The assistant was rude" is not a root cause; "skill `tone-formal` never loaded because its description only mentions invoicing" is. Use `qa.py chat --verbose` to see the **full picture** of each turn (see Step 7 below).

### Step 5 — Propose the fix and get feedback (USER CHECKPOINT)

Design the improvement and present it to the user BEFORE iterating:

- **what changes** — which instruction / which skill / which KB, as a minimal diff
- **what to wire** — a fix is often a **building block**, not just reworded prose: the right
  move may be to add an `{{ examples: ID }}` block (instead of describing the tone), a
  `{{ kb(ID) }}` search (instead of hard-coding a fact that drifted), a `{{ custom_tool: ... }}`
  Slack notification, a `{{ tool(ID) }}` API call, or a handoff instruction. **Offer the macro
  proactively** — don't just rewrite the paragraph. See [continuous-improvement → "Editing isn't
  just writing — wire the building blocks"](../continuous-improvement/SKILL.md#editing-isnt-just-writing--wire-the-building-blocks).
- **why** it addresses the root cause from Step 4
- **regression risk** — which other behaviours share the instructions/skills you're touching

Keep the diff minimal: broad rewrites are how regressions sneak in. Then wait for feedback — the user often knows constraints that aren't visible in the data (business rules, upcoming changes, tone preferences).

### Step 6 — REQUIRED: ask the user what to mock before chatting / before any eval run

**Before you chat with the assistant for the first time and before you trigger any eval run, you MUST ask the user whether any tools should be mocked.** This is not optional. Reasons:

1. **Reproducibility**: real tools depend on real state. A refund flow that worked yesterday may behave differently today because the order was actually refunded. Mocks let you reproduce the exact conditions of the customer's complaint.
2. **Safety**: real tools can have side effects (send a Slack message, charge a card, create a calendar event). Mocking the destructive ones during QA prevents collateral damage.
3. **Edge cases**: the customer complaint often involves a tool failure ("the assistant said my order was lost"). The only way to reliably reproduce that is to mock the tool with the failing payload.

When you ask, **enumerate the tools that are mockable for this playbook** so the user knows what's available. The list is the playbook's `api_tools` + the project's configured Composio/custom toolkits + the built-in tools the agent always has (`search_knowledge_base`, `load_skill`, `list_agents`, `list_teams`, `list_kbs`). Don't enumerate the events (they aren't tools) — see "What's NOT mockable" below.

Example prompt to the user:

> "Antes de chatear / antes de correr el eval: ¿querés mockear alguna tool? Las disponibles en este assistant son:
> - **Composio**: `SLACK_SEND_MESSAGE`, `CAL_POST_NEW_BOOKING_REQUEST`, `GMAIL_SEND_EMAIL` (los que tenga el project)
> - **API tools del playbook**: `lookup_order`, `process_refund`, `create_ticket` (los que estén en `api_tools`)
> - **Built-ins**: `search_knowledge_base`, `load_skill`
>
> Para reproducir la queja, capaz quieras mockear `lookup_order` con un payload de error o `search_knowledge_base` con un snippet específico. ¿Algún caso particular?"

If the user says "ninguna, dale así nomás" — proceed without mocks. But don't skip the question.

### Step 7 — Reproduce + iterate via chat with overrides + mocks

**NEVER create or save a playbook version to test a hypothesis.** All iteration happens through the chat endpoint's in-memory `playbook_override` — `--instructions` / `--instructions-file`, `--skills-file` (full replace or surgical patch), `--examples-file`, `--kb-ids`, `--api-tools` (see [Iterating without saving: playbook overrides](#iterating-without-saving-playbook-overrides)). Saving versions to test pollutes the version history with throwaway revisions; the only version that gets created in this whole workflow is the final one, applied by the human in Step 8.

First reproduce the bad behaviour **as-is** (no instruction/skill overrides — only the agreed mocks) to prove you can trigger it. Then apply the fix from Step 5 via `--instructions` / `--skills-file` and re-simulate the original scenario (same user_context, same mocked conditions) until the bad behaviour is **gone**.

```bash
# Reproduce the complaint exactly. Override the instructions OR skills
# once you're testing the fix; mock the tools that drove the failing
# behaviour.
python3 scripts/qa.py chat PLAYBOOK_BASE_ID \
  --message "Quiero un reembolso del pedido ORD-99999" \
  --conversation-id qa_repro_001 \
  --tool-mocks-file ./mocks/refund-not-found.json \
  --verbose
```

**Read the WHOLE response, not just the message.** `qa.py chat` prints to stderr a structured breakdown:

| Section | What to look at |
|---|---|
| **Events** | The message the user would see, but also `label` / `note` / `handoff_agent` / `priority` events the assistant emitted. A `[note]` is a private note (invisible to the customer but written to the conversation). A `[handoff_agent]` or `[handoff_team]` means the assistant gave up. |
| **Tool calls** | Every tool invoked, with arguments and result. `load_skill` tells you which skill the agent picked up — if the wrong one fired, the description text on that skill is wrong (the LLM picks skills off name+description, not content). `search_knowledge_base` shows the query and which articles came back — if the result is irrelevant, the KB content or chunking is the problem. `[MOCKED]` after a tool name means the response came from your mock, not the real tool. |
| **Citations** | Which KB articles the agent actually quoted. If the assistant cites the wrong article, either the article content is wrong or the search ranking is. |
| **Explanation** | Agent's own reasoning summary. Useful for catching subtle path choices ("decided to escalate because user asked twice"). |

Iterate by tweaking `--instructions` / `--skills-file` / `--tool-mocks-file` until the fix works. Nothing is persisted — no version bump, no chatlog pollution. Once the bad behaviour is reliably gone, move to Step 8.

### Step 8 — Hand off: the human applies the new version (USER CHECKPOINT)

**This skill never saves a new playbook version — not via the API, not via the builder skill.** Creating the version is a human-in-the-loop gate.

When the fix is validated, deliver the final content ready to apply:

- the full updated instructions (if they changed), and/or
- each changed/added skill as `name` + `description` + `content`

The user applies the changes in the Studio Chat UI, which creates the new version. **Wait for explicit confirmation that the new version is live and get the new version ID** — you need it for Step 9. Don't author eval runs against the old version assuming the fix "will be there".

### Step 9 — Close the loop with evals

Scale coverage to the severity / scope of the fix: a narrow fix gets one regression case; a fix touching a shared instruction or several flows gets a case per affected behaviour.

1. **Author the case(s)** — a scenario replicating the complaint, a `termination`, structured assertions for what must (not) happen, and the same `tool_mocks` you used to reproduce, so future runs are deterministic.
2. **Dry-run the definition** (optional but recommended) — `qa.py dry-run start` validates the case is gradable before persisting (see [Dry-running a candidate case](#dry-running-a-candidate-case-no-persistence)).
3. **Persist + run only the new case(s)** against the new version — no overrides now: the fix is saved, test the real thing.

   ```bash
   # Save the case
   python3 scripts/qa.py cases create PLAYBOOK_BASE_ID --body '{
     "name": "refund-order-not-found-handoff",
     "scenario": "Customer asks for a refund for an order that the lookup API returns as not-found.",
     "termination": "The assistant escalates to a human agent",
     "max_turns": 5,
     "assertions": [
       {"criteria": "The assistant does not fabricate an order status"},
       {"type": "handoff"}
     ],
     "tool_mocks": {
       "lookup_order": {"match_kind": "any", "error": "Order not found"}
     }
   }'

   # Run only this case against the NEW version (ignores is_enabled —
   # works even on disabled cases while you're still iterating)
   python3 scripts/qa.py runs create PLAYBOOK_BASE_ID \
     --playbook-id NEW_VERSION_ID \
     --case-ids NEW_CASE_ID
   ```

4. **Offer a full-suite run (USER CHECKPOINT)** — once the new case(s) pass, offer to run the whole eval suite against the new version (`runs create` without `--case-ids`) to catch regressions elsewhere. It costs time and tokens, so it's the user's call — but always offer.

### Cheat sheet — which mechanism for which question

| Question | Mechanism |
|---|---|
| "What did the assistant actually do in prod?" | data-expert skill — pull the real conversation |
| "What did the assistant's config look like back then?" | builder skill — pull that exact playbook version |
| "Does changing the prompt fix it?" | `qa.py chat --instructions ...` |
| "Does a different skill fire?" | `qa.py chat --skills-file ...` |
| "What does the assistant do when this tool returns X?" | `qa.py chat --tool-mocks-file ...` |
| "Is my new case definition gradable?" | `qa.py dry-run start --case ...` |
| "How does the fix get shipped?" | You don't ship it — the human applies the new version in the UI (Step 8) |
| "Did the fix pass without breaking the rest?" | `qa.py runs create` (no `--case-ids`) — offer it after every fix |
| "Just re-run THIS one case quickly" | `qa.py runs create --case-ids ID` |

---

## Scripts

### qa.py — Eval & testing API client

```bash
# List test cases
python3 scripts/qa.py cases list PLAYBOOK_BASE_ID

# Create a single test case
python3 scripts/qa.py cases create PLAYBOOK_BASE_ID --body '{...}'

# Create multiple test cases at once
python3 scripts/qa.py cases batch PLAYBOOK_BASE_ID --body '{"cases": [...]}'

# Delete a test case
python3 scripts/qa.py cases delete CASE_ID

# Trigger an eval run (all enabled cases, playbook's default models)
python3 scripts/qa.py runs create PLAYBOOK_BASE_ID --playbook-id VERSION_ID [--context '{}']

# Trigger an eval run against UNSAVED instructions / skills (no version bumped)
python3 scripts/qa.py runs create PLAYBOOK_BASE_ID --playbook-id VERSION_ID \
    --instructions-file ./draft-prompt.md \
    --skills-file ./draft-skills.json

# Trigger a run on a SUBSET of cases (ignores is_enabled — disabled cases included)
python3 scripts/qa.py runs create PLAYBOOK_BASE_ID --playbook-id VERSION_ID \
    --case-ids CASE_ID_1,CASE_ID_2

# Trigger a run with model overrides + parallelism
python3 scripts/qa.py runs create PLAYBOOK_BASE_ID --playbook-id VERSION_ID \
    --model openai-direct/gpt-4o-mini \
    --simulator-model anthropic/claude-sonnet-4 \
    --judge-model openai/gpt-4o \
    --concurrency 4

# List eval runs
python3 scripts/qa.py runs list PLAYBOOK_BASE_ID

# Check run status
python3 scripts/qa.py runs status RUN_ID

# Get run results (per-case details)
python3 scripts/qa.py runs results RUN_ID

# Cancel a running eval
python3 scripts/qa.py runs cancel RUN_ID

# Chat with an assistant (simulate a conversation)
python3 scripts/qa.py chat PLAYBOOK_BASE_ID --message "Hello, I need help"
python3 scripts/qa.py chat PLAYBOOK_BASE_ID --message "Follow up" --conversation-id CONV_ID

# Chat with UNSAVED instructions to iterate quickly (no version bumped)
python3 scripts/qa.py chat PLAYBOOK_BASE_ID --message "Hi" \
    --instructions "Reply in English. Be very concise." \
    --skills-file ./draft-skills.json

# Chat with MOCKED tool responses (stub Slack / KB / API tools — admin only)
python3 scripts/qa.py chat PLAYBOOK_BASE_ID --message "Quiero un reembolso de ORD-99999" \
    --tool-mocks-file ./mocks.json

# Dry-run a candidate eval case WITHOUT persisting it (validate the case
# definition before committing it via `cases create`)
python3 scripts/qa.py dry-run start PLAYBOOK_BASE_ID --playbook-id VERSION_ID \
    --case '{"name":"poc","scenario":"...","termination":"...","assertions":[{"criteria":"..."}]}'
python3 scripts/qa.py dry-run status DRY_RUN_ID
python3 scripts/qa.py dry-run cancel DRY_RUN_ID
```

## Full API Reference

See [references/api-reference.md](references/api-reference.md) for complete endpoint specs.

---

## How Evaluations Work

### The Eval Lifecycle

1. **Create test cases** — define scenarios, expected outcomes, and assertions for a playbook
2. **Trigger a run** — select a playbook version to test; runs execute asynchronously
3. **Monitor progress** — poll run status (pending → running → completed)
4. **Analyze results** — per-case pass/fail with LLM-generated explanations

### Test Case Anatomy

A test case defines **what to test** and **how to judge**:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique name (lowercase with dashes, e.g., `refund-happy-path`) |
| `scenario` | Yes | Instructions for the simulated user (what they want, how they behave) |
| `termination` | Yes | Expected outcome — the simulator checks this after each turn |
| `first_message` | No | Exact first message. If omitted, the LLM generates one from the scenario |
| `max_turns` | No | Max conversation turns (1-50, default: 10) |
| `assertions` | No | Criteria to evaluate after the conversation (LLM-as-judge) |
| `assertion_tags` | No | Tags to check — verifies the assistant applied specific tags |

### How the Simulator Works

For each test case, the system:

1. **Generates a user message** — either the exact `first_message` or an LLM-generated message based on the scenario
2. **Sends it to the assistant** — calls the actual playbook agent with the message
3. **Checks termination** — an LLM judges whether the expected outcome has ALREADY occurred (a promised/imminent outcome doesn't count; outcomes that are assistant actions — handoff, tag, note — are checked against the real emitted events). Write `termination` as an observable, completed fact: "el asistente derivó la conversación", not "el usuario quedará conforme"
4. **Repeats** — generates the next user message based on the scenario + conversation so far
5. **Evaluates assertions** — after the conversation ends, each assertion is evaluated by an LLM judge
6. **Checks tags** — verifies expected tags were applied during the conversation

### User Context

You can pass a `user_context` dict when triggering a run. This context is forwarded to the
assistant agent, simulating a real user with specific attributes:

```json
{
  "user_context": {
    "email": "test@example.com",
    "plan": "premium",
    "account_id": "acc-123"
  }
}
```

The assistant sees this context exactly as it would in a real conversation.

### Picking which cases to run

By default a run executes **every enabled case** for the playbook. Two ways to narrow it:

- **`is_enabled` flag** (persistent): toggle via the UI or `PATCH /eval-cases/{id}`. Permanently skips a case across all runs.
- **`case_ids` per-run** (ephemeral): pass `--case-ids` on `runs create`. Only those cases execute and **`is_enabled` is ignored** — pick a single disabled case while iterating without flipping flags on the rest.

```bash
# Run just two specific cases (works even if they're disabled)
python3 scripts/qa.py runs create PLAYBOOK_BASE_ID --playbook-id VERSION_ID \
  --case-ids c1f8...,c2d4...
```

Empty `--case-ids` ⇒ 400. Unknown IDs ⇒ 404. Omit the flag for the historical "all enabled" behaviour.

### Dry-running a candidate case (no persistence)

`qa.py dry-run start` runs the simulator + judge ONCE against an unsaved `EvalCaseCreate` payload — same pipeline as a real eval run, no rows written to `eval_cases` or `eval_runs`. Use this to:

- Validate a candidate case definition before persisting (does the simulator generate plausible user turns? does the `termination` fire? are the assertions gradable?).
- Test an instructions/skills change against one specific scenario without bumping a playbook version.

State lives in memory for ~30 minutes and is polled by dry-run ID:

```bash
DRY_RUN_ID=$(python3 scripts/qa.py dry-run start PLAYBOOK_BASE_ID \
  --playbook-id VERSION_ID \
  --case '{
    "name": "refund-poc",
    "scenario": "User asks for a refund for ORD-12345.",
    "termination": "The assistant confirms the refund will be processed",
    "max_turns": 6,
    "assertions": [{"criteria": "The assistant asks for the order number"}]
  }' \
  --instructions "You are a refund specialist. Always ask for the order number first." \
  | jq -r .dry_run_id)

# Poll until completed / failed / cancelled
python3 scripts/qa.py dry-run status $DRY_RUN_ID
# or bail out if it's clearly going wrong
python3 scripts/qa.py dry-run cancel $DRY_RUN_ID
```

If the dry-run passes and the conversation looks right, persist the case via `cases create` and move to Step 9 of the [QA practice workflow](#qa-practice-workflow-read-this-first).

### Model overrides

Three independent model knobs control different LLM calls during an eval. All default to the playbook's configured model (or the eval-system env default for simulator/judge), and all accept the same OpenRouter-compatible syntax.

| Flag | What it controls | Default |
|---|---|---|
| `--model` | The **assistant** LLM (the playbook agent under test) | Playbook's configured model |
| `--simulator-model` | The LLM that role-plays the **user** in each case | `anthropic/claude-sonnet-4` (env: `EVAL_SIMULATOR_MODEL`) |
| `--judge-model` | The LLM that grades **text-type** assertions. Structured assertions (`tool_called`, `handoff_to_agent`, etc.) run deterministic checks and ignore this. | `openai/gpt-4o` (env: `EVAL_EVALUATOR_MODEL`) |

**Syntax** (same for all three flags):

- `provider/model_id` — single model. Examples: `openai-direct/gpt-4o-mini`, `anthropic/claude-sonnet-4`.
- `primary{timeout}fallback` — primary first; on timeout (seconds) fall back. Example: `groq/llama-3.3-70b-versatile{8}openai-direct/gpt-4o-mini`.
- `modelA:50,modelB:50` — A/B experiment. Percentages must sum to 100; cases are hash-assigned to a variant by conversation_id.

Bad input ⇒ 422 at the API edge (e.g. percentages that don't sum to 100, or a bare `gpt-4o-mini` without provider prefix). Empty/whitespace ⇒ field ignored.

#### Recommended models (use these exact slugs — don't invent new ones)

OpenRouter's catalog is strict; invented slugs will 422. These are the slugs actually in use across the Studio Chat stack:

**Anthropic — Claude:**

| Slug | Notes |
|---|---|
| `anthropic/claude-sonnet-4.6` | Newest Sonnet. Default for the assistant in most scenarios. |
| `anthropic/claude-sonnet-4.5` | One rev behind 4.6. |
| `anthropic/claude-sonnet-4` | Eval-system default for the **simulator** (`EVAL_SIMULATOR_MODEL`). |
| `anthropic/claude-3.5-sonnet` | Stable older Sonnet; cheap baseline for diffs. |
| `anthropic/claude-haiku-4.5` | Newest Haiku — fast / cheap. Good for high-volume runs or the simulator when latency matters more than nuance. |

**OpenAI — GPT:**

| Slug | Notes |
|---|---|
| `openai/gpt-5.4` | Newest GPT-5 flagship. |
| `openai/gpt-5.4-mini` | GPT-5 mini. Supports `[reasoning=…]` suffix (see below). |
| `openai/gpt-5.2-chat` | Stable GPT-5 chat variant. |
| `openai/gpt-4.1-mini` | Solid mid-tier. |
| `openai/gpt-4.1-nano` | Smallest GPT-4.1 — cheap. |
| `openai/gpt-4o` | GPT-4o via the OpenRouter pool. Default for the **judge** (`EVAL_EVALUATOR_MODEL`). |
| `openai/gpt-4o-mini` | Cheap judge / assistant. |
| `openai-direct/gpt-4o` | Same model via the **direct** OpenAI provider (skips OpenRouter pool — lower latency, different billing). |
| `openai-direct/gpt-4o-mini` | Direct-provider 4o-mini. |

**Google — Gemini:**

| Slug | Notes |
|---|---|
| `google/gemini-3.1-flash-lite` | **Recommended simulator + judge** for high-volume suites: validated verdict quality, ~15x cheaper than the gpt-4o default, and supports the flex service tier (eval runs request it automatically, ~50% off). |
| `google/gemini-2.5-flash` | Newest stable Flash. |
| `google/gemini-2.5-flash-lite` | Cheaper Flash variant. |
| `google/gemini-2.0-flash-001` | Previous Flash generation. |
| `google/gemini-3-flash-preview` | Gemini 3 Flash preview — may change. |

> **Gemini caveat**: there's a known tool-calling bias in this codebase ([docs/gemini-tool-call-bias.md](https://github.com/surfingdev/kaptbase/blob/main/docs/gemini-tool-call-bias.md)). Prefer Sonnet for the **assistant** when the playbook leans heavily on tools.

#### Reasoning effort suffix (GPT-5 family)

OpenAI reasoning-capable models accept an optional `[reasoning=X]` suffix. Valid efforts: `none`, `low`, `medium`, `high`, `xhigh`. `none` disables reasoning entirely. Example:

```
openai/gpt-5.4-mini[reasoning=medium]
openai/gpt-5.2-chat[reasoning=none]
```

The suffix composes with the other syntactic forms.

### Concurrency

`--concurrency` (1..5, default `1`) fans cases out across a server-side thread pool. `1` keeps the sequential walk; higher values are useful when the case suite is large but watch for the simulator/agent provider's rate limits — 429s surface in `EvalResult.error_message`. Recommended 3–5 for ad-hoc runs.

---

## Iterating without saving: playbook overrides

The QA pain point: every prompt or skill change normally bumps a saved playbook version, which means a version-history littered with throwaway revisions and an approval step in front of every iteration. The `--instructions`, `--skills-file`, `--examples-file`, `--kb-ids`, and `--api-tools` flags on `chat` and `runs create` let you test in-memory replacements **without persisting anything**.

### When to use

- Iterating on the system prompt — try a new tone, a new rule, a new fallback — and see how the assistant responds turn-by-turn.
- Validating a draft skill (casuística) end-to-end against the full eval suite before promoting it.
- A/B comparing two prompt variants without bumping the active version.
- Reproducing a production conversation with a tweaked prompt to confirm the fix.

### Override semantics

| Flag | Replaces… |
|---|---|
| `--instructions TEXT` / `--instructions-file FILE` | Main playbook instructions (the free-text content). |
| `--skills-file FILE` | The full set of skills. Pass `[]` to disable all skills. |
| `--examples-file FILE` | Global reference examples. |
| `--kb-ids id1,id2` | Knowledge base IDs (pass `""` to disable all KBs). |
| `--api-tools t1,t2` | API tool IDs (pass `""` to disable all tools). |

Rules:

- **Each flag is independent** — omit a flag and the saved playbook field stays.
- **Replace, not merge** — lists are swapped wholesale; there's no union.
- **Conversations are forced into preview + eval mode** — overridden runs never count toward production analytics, the sticky-model cache, or chatlogs.
- **No version is created** — the saved playbook is untouched; if you like the result, edit and save it through the normal flow.
- Requires admin or API-key authentication (the same `sbs_` / `kps_` tokens the skill already uses).

### Skills file shape

`--skills-file` accepts **two shapes** — pick the one that matches what you want to do.

#### 1. Full replace (list of skill objects)

Drop the saved playbook's skills entirely and use exactly these:

```json
[
  {
    "name": "refund-flow",
    "description": "Handle refund requests with order id verification",
    "content": "First ask for the order id. Then check eligibility..."
  },
  {
    "name": "english-only",
    "description": "Force English replies",
    "content": "Reply only in English regardless of customer language."
  }
]
```

Pass `[]` to disable **all** skills.

#### 2. Surgical patch (object with `add` / `replace` / `remove`)

Keep most of the saved skills and only modify a few. Operators are applied in order: `remove` → `replace` → `add`:

```json
{
  "remove": ["legacy-skill-a", "legacy-skill-b"],
  "replace": [
    {
      "name": "refund-flow",
      "description": "Refund handling, tightened policy",
      "content": "ASK for order id BEFORE confirming any refund..."
    }
  ],
  "add": [
    {
      "name": "english-only",
      "description": "Force English replies",
      "content": "Reply only in English regardless of customer language."
    }
  ]
}
```

**Strict-validation rules** (the BE returns `422` if violated, before any LLM call):
- `remove` of a name that isn't on the saved playbook → 422.
- `replace` of a name that isn't on the saved playbook → 422 (use `add` instead).
- `add` of a name that already exists (after `remove` ran) → 422 (use `replace` instead).
- Duplicate names within a single operator list → 422.

`remove: [X]` + `add: [{name:X, ...}]` of the same name **is** allowed — after `remove` drops the saved row, the slot is free for `add`.

#### Skill object shape

Both shapes share the same skill object shape (matches `SkillOverrideInput` on the BE). Note: only the fields the LLM actually reads during skill discovery are accepted here — `trigger` lives on the saved-version skill row but is never injected into the system prompt, so the override endpoint omits it.

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Unique identifier (kebab-case recommended). Matched by name in `replace`/`remove`. |
| `description` | yes | Short summary shown to the agent during skill discovery. |
| `content` | yes | Full instructions. Macros like `{{ kb(<id>) }}` and `{{ tool(<id>) }}` are expanded — the referenced KB / API tool must already exist in the project (the override doesn't create them). |
| `examples` | no | Optional list of reference conversation examples. |
| `order` | no | Display/listing order. Auto-assigned if omitted. |

### Examples

```bash
# Quick prompt tweak via inline flag
python3 scripts/qa.py chat PLAYBOOK_BASE_ID --message "Hi" \
    --instructions "Always reply in English, be terse."

# Full file-based override for chat
python3 scripts/qa.py chat PLAYBOOK_BASE_ID --message "I want a refund" \
    --instructions-file ./draft-prompt.md \
    --skills-file ./draft-skills.json \
    --examples-file ./draft-examples.json \
    --conversation-id qa_iter_001

# Disable all skills to test the bare prompt
python3 scripts/qa.py chat PLAYBOOK_BASE_ID --message "Hello" \
    --skills-file <(echo '[]')

# Surgically modify the saved skills (patch shape)
# ./skills-patch.json:
#   { "remove": ["old-flow"], "add": [{"name": "english-only", ...}] }
python3 scripts/qa.py chat PLAYBOOK_BASE_ID --message "Hello" \
    --skills-file ./skills-patch.json

# Run the full eval suite against an unsaved prompt
python3 scripts/qa.py runs create PLAYBOOK_BASE_ID \
    --playbook-id PB_VERSION_ID \
    --instructions-file ./candidate-prompt.md
```

### Wire shape

Both endpoints accept a `playbook_override` object on the request body. The CLI builds it for you, but if you need to call the API directly:

**Full-replace form (list-shape skills):**

```json
{
  "conversation_id": "qa_iter_001",
  "user_message": "...",
  "playbook_override": {
    "content": "...full instructions...",
    "skills": [
      {"name": "...", "description": "...", "content": "..."}
    ],
    "examples": [],
    "kb_ids": ["kb-uuid-1"],
    "api_tools": []
  }
}
```

**Surgical-patch form (object-shape skills):**

```json
{
  "conversation_id": "qa_iter_001",
  "user_message": "...",
  "playbook_override": {
    "skills": {
      "remove": ["old-flow"],
      "replace": [{"name": "refund-flow", "description": "...", "content": "..."}],
      "add": [{"name": "english-only", "description": "...", "content": "..."}]
    }
  }
}
```

Any subset of these keys is valid — omitted keys keep the saved playbook value.

---

## Mocking Tools (`tool_mocks`)

By default, an eval run or a chat call invokes real tools — searches the real KB, hits the real API, sends the real Slack message. That's great for end-to-end coverage but bad for QA: it depends on real-world state, can have destructive side effects, and makes it hard to reproduce a customer complaint that involved a specific tool failure.

`tool_mocks` lets you **stub specific tools** with canned responses. Same wire shape and semantics in two places:

| Where | Field | When mocks apply |
|---|---|---|
| **Per case** (saved) | `EvalCase.tool_mocks` | Every time the case runs in any eval |
| **Per chat call** (ephemeral) | `PlaybookChatRequest.tool_mocks` | This chat request only — forced into preview+eval mode (admin only) |

Step 6 of the [QA practice workflow](#qa-practice-workflow-read-this-first) makes asking the user about mocks **mandatory** before any chat or eval run. The rest of this section covers the shape + the rules.

### What can and cannot be mocked

**Mockable** (anything that dispatches through the agent's toolset wrapper):

- **Composio integrations**: tool names follow the `TOOLKIT_ACTION` uppercase convention. Examples: `SLACK_SEND_MESSAGE`, `CAL_POST_NEW_BOOKING_REQUEST`, `CAL_CANCEL_BOOKING_VIA_UID`, `GMAIL_SEND_EMAIL`. The exact list depends on which toolkits are configured in `SUPPORTED_TOOLKITS` for the project.
- **Custom API tools**: the entries in the playbook's `api_tools`. Names match what the playbook author registered (typically `snake_case`).
- **Custom toolkit tools**: same as Composio but registered via the in-house `CUSTOM_TOOLKIT_REGISTRY`.
- **Built-in tools**: `search_knowledge_base`, `load_skill`, `list_agents`, `list_teams`, `list_kbs`.

Tool names in the mock map must match `ToolCallTrace.name` exactly — uppercase for Composio, snake_case for the rest.

**NOT mockable** (not dispatched as tool calls):

- **Agent events**: `message`, `note`, `label`, `priority`, `handoff_agent`, `handoff_team`. These are items the LLM emits inside its structured output payload, parsed downstream by the chat handler — they never go through the wrapper. To validate them, use the matching structured assertions (`HandoffAssertion`, `PrioritySetAssertion`, `TagAddedAssertion`, `PrivateNoteContainsAssertion`).
- **Enrichment tools** (`enrichment_tool_ids`): run BEFORE the agent's first turn. The wrapper doesn't exist yet at that point in the request lifecycle.

### Shape

`tool_mocks` lives on the case body. Each key is a tool name; each value is one rule or an ordered list of rules:

```json
{
  "name": "refund-when-eligible",
  "scenario": "...",
  "termination": "...",
  "tool_mocks": {
    "lookup_order": {
      "match_kind": "any",
      "return_value": {"order_id": "ORD-123", "status": "delivered", "days_since": 5}
    },
    "process_refund": {
      "match_kind": "any",
      "return_value": {"refund_id": "RFND-999", "amount": 49.99}
    }
  }
}
```

### Match modes

A rule fires only when its `match_kind` matches the call:

| `match_kind` | Fires when… | Required field |
|---|---|---|
| `any` | always | — |
| `call_ordinal` | the Nth call to this tool (1-indexed) | `call_ordinal: int` |
| `args_match` | call args ⊇ `match_args` (subset filter; missing keys are wildcards) | `match_args: dict` |

### Payload: exactly one of `return_value` or `error`

```json
{
  "tool_mocks": {
    "send_email": {"match_kind": "any", "error": "SMTP unavailable"},
    "lookup_user": {
      "match_kind": "args_match",
      "match_args": {"plan": "enterprise"},
      "return_value": {"name": "Acme Corp", "tier": "enterprise"}
    }
  }
}
```

`error` raises a tool error inside the run (the assistant sees it the same way it would see a real API failure — useful for testing error handling). `return_value` is whatever JSON the tool would normally return.

### Multiple rules per tool, first-match-wins

Pass an array to express "specific case → fallback":

```json
{
  "tool_mocks": {
    "lookup_order": [
      {"match_kind": "args_match", "match_args": {"order_id": "ORD-123"}, "return_value": {"status": "delivered"}},
      {"match_kind": "args_match", "match_args": {"order_id": "ORD-999"}, "return_value": {"status": "lost"}},
      {"match_kind": "any", "error": "Order not found"}
    ]
  }
}
```

Rules are evaluated top-to-bottom; the first match wins. The catch-all `any` rule at the end keeps the run safe if the assistant calls with an unexpected argument.

### Multi-call sequences

Use `call_ordinal` to return different values across consecutive calls:

```json
{
  "tool_mocks": {
    "search_kb": [
      {"match_kind": "call_ordinal", "call_ordinal": 1, "return_value": [{"title": "Refund policy", "snippet": "..."}]},
      {"match_kind": "call_ordinal", "call_ordinal": 2, "return_value": [{"title": "Refund timeline", "snippet": "..."}]}
    ]
  }
}
```

### Important: mocks are exhaustive per tool

Once you mock a tool, the rule list is **complete** — every call to that tool during the run must match a rule. If the assistant calls `lookup_order` a third time and no rule matches, the run **fails loudly** with `no mock matched call #3 for tool lookup_order`.

This is intentional: silently falling through to the real implementation would let production state leak into eval runs and make failures impossible to reproduce. Always include an `any` catch-all (or extra `call_ordinal` rules) if you don't know exactly how many times the assistant will call a tool.

Tools you DON'T list in `tool_mocks` are unaffected — they call the real implementation as usual.

### Combining mocks with tool assertions

`tool_called` and `tool_not_called` assertions both support `args_match` for "the assistant called X with these specific args" (or "must not call X with these args"). Combine with mocks to test fine-grained behavior:

```json
{
  "tool_mocks": {
    "send_email": {"match_kind": "any", "return_value": {"sent": true}}
  },
  "assertions": [
    {"type": "tool_called", "name": "send_email", "args_match": {"to": "support@example.com"}},
    {"type": "tool_not_called", "name": "send_email", "args_match": {"to": "ceo@example.com"}}
  ]
}
```

### Mocking during chat (no persisted case)

The same `tool_mocks` shape works on `qa.py chat` via `--tool-mocks-file`, letting you stub tool responses for a single ad-hoc chat without authoring a case. Useful in Step 7 of the [QA practice workflow](#qa-practice-workflow-read-this-first) when you're still hunting for the fix.

Semantics:

- **Admin / API-key only** — same gate as `--instructions` / `--skills-file`.
- **Forces preview + eval mode** — the conversation is excluded from chatlogs, sticky-model assignment, and production analytics. Same semantics as `--instructions`, so they compose cleanly.
- **Mocked calls are flagged in the output**: `qa.py chat` prints `[MOCKED]` next to the tool name in the `Tool calls` section so you can tell stubbed responses apart from real ones.

Example `mocks.json` reproducing a "lookup_order returns not-found, KB has no refund policy" scenario:

```json
{
  "lookup_order": {"match_kind": "any", "error": "Order not found"},
  "search_knowledge_base": {
    "match_kind": "any",
    "return_value": []
  }
}
```

Then chat:

```bash
python3 scripts/qa.py chat PLAYBOOK_BASE_ID \
  --message "Quiero un reembolso del pedido ORD-99999" \
  --tool-mocks-file ./mocks.json \
  --verbose
```

Watch the `Tool calls` section for `lookup_order [custom] [MOCKED]` and verify the assistant's response handles the error gracefully (e.g. escalates instead of fabricating an order status).

> **Note**: run-level `tool_mocks` on `qa.py runs create` is not supported — per-case `tool_mocks` lives on the case body itself. If you need deterministic mocks across a whole run, put them on each case (or use a `--case-ids` subset against cases that already carry mocks). The CLI rejects `--tool-mocks-file` on `runs create` with a clear error.

## Per-Case User Context (`user_context`)

A case can override the run-level `user_context` for its own scope. Case keys win over run keys; the special `eval_overrides` sub-namespace is shallow-merged.

```json
{
  "name": "vip-customer-flow",
  "user_context": {
    "plan": "enterprise",
    "eval_overrides": {"agent_name": "PremiumBot"}
  }
}
```

Use this when one case needs a different user identity, plan, or simulated state without affecting the rest of the run.

---

## Writing Good Test Cases

### Scenario Guidelines

The scenario tells the **simulated user** how to behave — it is the simulator's only script. A vague scenario makes the simulator improvise, and improvisation is where conversations (and verdicts) diverge between runs. **Write the scenario as a decision tree for the user, not as a description**: the assistant can react in several ways, and the scenario must say what the user does on each branch.

#### The structured scenario template

Write scenarios with these blocks (plain text, bullets — the simulator follows them faithfully):

```
PERSONA: cliente existente, apurado pero educado. Tutea. Habla español.
OBJETIVO: cancelar el pedido 1042.
DATOS: pedido=1042. Lo da SOLO si se lo piden, no en el primer mensaje.
REACCIONES:
- Si el asistente pide el ID del pedido → darlo.
- Si pide confirmación para cancelar → confirmar que sí, está seguro.
- Si ofrece alternativas (reprogramar, cambiar dirección) → rechazarlas, solo quiere cancelar.
- Si deriva a una persona → aceptar y despedirse.
- Ante cualquier otra pregunta → responder breve y neutro, sin inventar datos.
CIERRE: cuando confirmen la cancelación, agradecer y despedirse en UN mensaje.
```

Each block exists because its absence is a known flakiness source:

| Block | What breaks without it |
|---|---|
| **PERSONA** | Register/language drift between runs (a case meant for Portuguese simulated in Spanish; formal vs informal flapping) |
| **OBJETIVO** (one, observable) | The simulator wanders; the `termination` check has nothing crisp to detect. The objetivo and the `termination` field should be two views of the same fact. |
| **DATOS** (exact values + delivery policy) | The simulator invents IDs the mocks don't match, or hands over data too early — killing cases that assert "asks for the ID **before** acting". The delivery policy ("lo da solo si se lo piden" / "NUNCA lo da") is what makes precondition-dependent assertions exercisable. |
| **REACCIONES** (branch coverage) | The assistant's counter-moves are not fully predictable. Without branch instructions, the simulator improvises — agreeing to alternatives it should refuse, dropping refusals it should hold, answering questions with invented facts. **Enumerate the assistant's likely moves and the user's response to each.** |
| **Catch-all reaction** | The branch you didn't predict. "Responder breve y neutro, sin inventar datos" keeps unpredicted turns from derailing the case. |
| **CIERRE** | Farewell loops (12-turn goodbye exchanges) that burn tokens and create late-conversation noise. |

#### How to enumerate the REACCIONES branches

Read the playbook (builder skill) and list every rule that can fire on this flow — each rule is a branch the assistant might take. Typical branch set for almost any case:

1. Assistant asks for a datum → give it / refuse it (per the case's design)
2. Assistant asks for confirmation → confirm / back out
3. Assistant offers an alternative path → accept / reject
4. Assistant hands off to a human → accept and close
5. Assistant asks something unpredicted → the catch-all

A case that tests a **refusal** ("user never provides the ID") must say so emphatically and cover the assistant's insistence: *"NO sabe el número de pedido. Si se lo piden, dice que no lo encuentra. Aunque insistan, no lo da en toda la conversación."* The simulator is trained to hold refusals the scenario dictates — but only if the scenario dictates them explicitly.

#### Hard rules

- **The scenario describes the USER, never the assistant.** "El asistente deberá pedir el ID" does not belong in a scenario — that's an assertion. A scenario that scripts the assistant confuses the simulator into playing both roles.
- **One objective per scenario.** Two goals ("cancelar el pedido y de paso preguntar precios") produce conversations that satisfy assertions in unpredictable order. Split into two cases.
- **Pin the first turn with `first_message`** whenever the opening matters — it anchors the whole conversation deterministically and confines simulator variance to follow-up turns.
- **Exact data only**: every ID, amount and date the flow needs goes in DATOS with its literal value, matching the case's `tool_mocks`. The simulator won't invent identifiers — if a datum is missing, the conversation stalls.
- **Don't contradict the playbook**: a case expecting "indaga antes de derivar" while the scenario has the user demanding a human (which the playbook answers with an immediate handoff) will flip forever. Align the expectation with the playbook rule, or change the scenario trigger.
- **Mocks must mirror the real API's shape**: if the list endpoint mock includes prices, the assistant never needs the detail tool — and your `tool_called` assertion fails for the wrong reason. Mock list endpoints lean (ids + names), detail endpoints rich.

#### Worked example — vague vs structured

❌ Vague (improvisation-prone):

> "El usuario quiere cancelar un pedido."

What flaps: does the user know the ID? Give it when? Confirm when asked? Accept a reschedule offer? Every run answers these differently.

✅ Structured: the template above. Ten simultaneous runs of a suite written in this style produced **zero verdict flips** — the residual variance was infrastructure, not simulation.

### Assertion types — pick the right tool for each check

Assertions live on `EvalCase.assertions` as a list of typed objects. There are **two families**:

- **Text** (`type: "text"`) — graded by the LLM judge. Use for free-form claims about what the assistant said.
- **Structured** (everything else) — graded deterministically by walking `turn.events` and `turn.tool_calls`. No LLM call. Faster, cheaper, and immune to judge flakiness — prefer these whenever the check fits a structured shape.

The `--judge-model` flag affects only text assertions. Structured assertions ignore it.

> **Picking the right type**: every time you reach for `text` to check something the assistant *did* (called a tool, handed off, set a priority, applied a tag, wrote a private note), there's a structured variant that does it deterministically. Use `text` only for what the assistant *said* (tone, content of the message, that it mentioned a specific policy).

#### `text` — LLM-as-judge

```json
{"type": "text", "criteria": "The assistant mentions the 30-day refund policy"}
```

`type` defaults to `text`, so the legacy short form still works:

```json
{"criteria": "The assistant asks for the order number before proceeding"}
```

**The judge returns a TERNARY verdict** — `AssertionResult.verdict` is `passed`, `failed`, or **`ambiguous`** (the legacy `passed` boolean maps `ambiguous` → `true`). See [The `ambiguous` verdict](#the-ambiguous-verdict--criteria-lint) below: a criterion too vague to verify objectively doesn't get a guessed binary verdict — it gets flagged for rewrite.

**Rules for writing criteria that never come back ambiguous** (each rule maps to a real flakiness pattern found in production suites):

1. **Binary and observable.** The criterion must describe something two independent judges would always score identically: a concrete behavior, a phrase category, a countable action.
   - ✅ "El asistente menciona la política de reembolso de 30 días"
   - ✅ "El asistente incluye al menos una frase de empatía (p. ej. 'lamento lo que pasó')"
   - ❌ "El asistente responde cordial" → `ambiguous` (cualidad indefinida)
   - ❌ "El asistente usa un tono muy empático" → `ambiguous` (palabra de grado sin umbral: "muy", "bastante", "suficientemente")
2. **One check per criterion.** Split compound criteria — "hace X **y** explica Y" becomes two assertions; each shows its own verdict in the diff view. Alternatives with "o" are supported (passes if ANY branch holds) but make failures harder to read.
3. **Negations are reliable.** "El asistente NO hace X" passes when X is absent — the judge is explicitly instructed that absence alone satisfies a negated criterion. Don't avoid them.
4. **Conditional criteria need the scenario to force the condition.** "Si el usuario insulta, el asistente deriva" passes *vacuously* when the simulated user never insults — the criterion tested nothing. If you write "cuando Y, entonces X", the `scenario` must make Y actually happen.
5. **Semantic match, not literal.** The assistant doesn't need the criterion's exact words — an equivalent paraphrase in any language satisfies it. Don't write criteria that demand specific phrasings unless the phrasing itself is the requirement.
6. **The judge sees the assistant's actions.** Each assistant turn carries an `[actions: handoff_agent, label=..., note]` line in the judge's view, so criteria like "deriva la conversación" are judged against the real event — but prefer the structured assertion (`handoff`, `tag_added`, …) whenever one exists: deterministic beats judged.

#### `tool_called` — a specific tool was invoked

```json
{"type": "tool_called", "name": "search_knowledge_base", "min_count": 1}
```

Optional `args_match` narrows the match to calls whose `arguments` dict is a superset of the given keys/values:

```json
{
  "type": "tool_called",
  "name": "SLACK_SEND_MESSAGE",
  "args_match": {"channel": "#alerts"},
  "min_count": 1
}
```

`min_count` defaults to 1 — bump it when you need to assert "called at least N times" (e.g., retrieved KB info twice during a long flow).

#### `tool_not_called` — a tool was never invoked

```json
{"type": "tool_not_called", "name": "process_refund"}
```

With `args_match`, narrows to "must never be called *with these args*" (other calls to the same tool are ignored):

```json
{
  "type": "tool_not_called",
  "name": "send_email",
  "args_match": {"to": "ceo@example.com"}
}
```

Useful for negative tests: "the agent must NOT email the CEO."

#### `tool_call_sequence` — tools fired in a specific order

```json
{
  "type": "tool_call_sequence",
  "names": ["lookup_order", "check_refund_eligibility", "process_refund"],
  "strict": false
}
```

`strict: false` (default) means the listed tools must appear in order but other tool calls may interleave. `strict: true` means they must appear **contiguously** in the exact order — useful when you need to lock down "no extra calls between A and B."

#### `handoff` — *some* handoff event was emitted (mode-agnostic)

```json
{"type": "handoff"}
```

Matches either `handoff_agent` or `handoff_team`. **Standalone accounts** only ever see "the agent gave up" with no agent/team distinction — this is the only handoff assertion that makes sense there. **Kaption accounts** also have the more specific variants below.

#### `handoff_to_agent` — handoff to a specific agent (Kaption)

```json
{"type": "handoff_to_agent", "agent_id": 162}
```

Or `"any"` for "any specific agent" (i.e., assert that a `handoff_agent` event fired with *some* agent_id):

```json
{"type": "handoff_to_agent", "agent_id": "any"}
```

#### `handoff_to_team` — handoff to a specific team (Kaption)

```json
{"type": "handoff_to_team", "team_id": 7}
```

#### `no_handoff` — assert the agent did NOT hand off

```json
{"type": "no_handoff"}
```

Matches both agent and team handoffs. Useful when the playbook is supposed to resolve the issue end-to-end.

#### `priority_set` — `priority` event with a specific value

```json
{"type": "priority_set", "value": "urgent"}
```

`value` must be one of `urgent | high | medium | low`. Pairs well with playbooks that triage by severity.

#### `tag_added` — a `label` event added a specific tag

```json
{"type": "tag_added", "tag": "billing"}
```

> The agent emits these as `label` events internally, but the user-facing term is "tag" — this assertion uses `tag_added` for consistency with the rest of the eval surface.

There's also a **legacy** `assertion_tags: ["billing", "escalation"]` field on the case body that asserts a list of tags in one shot. It still works for backwards compatibility, but new cases should prefer one `tag_added` assertion per tag — they show up individually in the diff view and per-assertion result rows.

> **Tag whitelist gotcha.** The platform only applies tags that are in the playbook's supported set, which is parsed from **single-backtick-wrapped** tag values in the instructions + skills. If a `tag_added` assertion fails even though the assistant "tried" to tag, check that the tag value is wrapped in backticks somewhere in the instructions/skills — an un-backticked tag is dropped at runtime. Conversely, never wrap non-tag tokens (status values, field names, tool IDs) in single backticks: they get parsed as fake tags. When iterating on skill content via `--skills-file`, follow the same backtick policy (see the **Tagging** section of the `builder` skill).

#### `private_note_contains` — a private note's content contains a substring

```json
{
  "type": "private_note_contains",
  "substring": "asignar a Lautaro",
  "case_insensitive": true
}
```

Useful when the playbook is supposed to write specific context into a private note for the next human agent. `case_insensitive` defaults to `true`.

### The `ambiguous` verdict — criteria lint

When a text criterion hinges on an intensity qualifier ("muy", "bastante") or an undefined subjective quality ("cordial", "natural", "tono adecuado") and the conversation doesn't satisfy or violate it in an extreme, unmistakable way, the judge does NOT guess. It returns:

```json
{
  "verdict": "ambiguous",
  "explanation": "criterio subjetivo: una sola frase de empatía seguida de texto procedural",
  "rewrite_suggestion": "El asistente reconoce explícitamente la frustración del usuario con al menos una frase que valide la dificultad"
}
```

What this means in practice:

- **An ambiguous assertion never fails the case.** The case status is computed from `failed` verdicts only. Ambiguous is a *lint on the test*, not a verdict on the assistant.
- **`rewrite_suggestion` is the fix.** It's a judge-proposed replacement criterion, in the same language as the original, that is objectively verifiable and captures the apparent intent. The UI renders it in a violet hint box (run results and dry-run panel).
- **The workflow:** run the suite → collect every `ambiguous` → apply the suggested rewrites via `PATCH /eval-cases/{id}` (review them first — the judge captures *apparent* intent) → re-run. A healthy suite has zero ambiguous verdicts; each one that appears is the system telling you exactly which test to fix and how.
- A criterion that is vague but *unmistakably* satisfied or violated still gets a normal verdict — ambiguous only fires on the genuinely undecidable borderline (one formulaic "entiendo tu frustración" against "tono MUY empático" is the canonical example).

### Internal errors vs failed cases

`EvalResult.status` distinguishes `failed` (assertions failed — a verdict on the assistant) from **`error`** (eval infrastructure failed — provider 429s that survived the retry backoff, timeouts, unparseable judge output). Errors count under `EvalRun.error_cases`, never under `failed_cases`, and render amber in the UI. If a run shows internal errors, re-run it — don't read them as regressions. Eval-side LLM calls already retry with exponential backoff (up to 6 attempts, `Retry-After`-aware) before giving up.

### Combined examples

A single case can mix text and structured assertions freely. Structured assertions run first (deterministic, no LLM cost); text assertions run after.

```json
{
  "name": "refund-flow-eligible",
  "scenario": "Customer with order ORD-12345 (5 days old) wants a refund.",
  "termination": "The assistant confirms the refund will be processed",
  "max_turns": 6,
  "assertions": [
    {"type": "tool_call_sequence", "names": ["lookup_order", "process_refund"]},
    {"type": "tool_called", "name": "process_refund", "args_match": {"order_id": "ORD-12345"}},
    {"type": "tool_not_called", "name": "human_handoff"},
    {"type": "priority_set", "value": "low"},
    {"type": "tag_added", "tag": "refund-completed"},
    {"criteria": "The assistant confirms the refund amount in the response"}
  ]
}
```

A handoff-on-failure case for a standalone account:

```json
{
  "name": "refund-flow-not-eligible-handoff",
  "scenario": "Customer wants a refund for a 60-day-old order. Policy is 30 days.",
  "termination": "The assistant escalates to a human",
  "max_turns": 5,
  "assertions": [
    {"type": "handoff"},
    {"type": "tool_not_called", "name": "process_refund"},
    {"type": "private_note_contains", "substring": "fuera de política de 30 días"},
    {"criteria": "The assistant explains the 30-day policy to the customer"}
  ]
}
```

### Picking the right assertion — cheat sheet

| Question | Assertion |
|---|---|
| Did the assistant **say** X? | `text` (LLM judge) |
| Did the assistant **call** tool X? | `tool_called` |
| Did the assistant **call** tool X with these args? | `tool_called` + `args_match` |
| Did the assistant **NOT call** tool X? | `tool_not_called` |
| Did the assistant **NOT call** tool X with these args? | `tool_not_called` + `args_match` |
| Did tools fire in this order? | `tool_call_sequence` |
| Did the assistant give up? (standalone) | `handoff` / `no_handoff` |
| Did the assistant route to agent N? (Kaption) | `handoff_to_agent` |
| Did the assistant route to team N? (Kaption) | `handoff_to_team` |
| Did the assistant set conversation priority? | `priority_set` |
| Did the assistant apply tag X? | `tag_added` |
| Did the assistant write a private note containing X? | `private_note_contains` |

> **Reminder**: events (`priority`, `label`, `note`, `handoff_*`) cannot be **mocked** with `tool_mocks` because they're not tool calls — they're items in the LLM's structured output. But they CAN be **asserted** with the structured assertions above. The two features are complementary: mocks shape the inputs the agent sees during the run; assertions verify the side effects (events + tool calls) it produced.

---

## Examples

### Example: Create a Single Test Case

```bash
python3 scripts/qa.py cases create PLAYBOOK_BASE_ID --body '{
  "name": "refund-happy-path",
  "scenario": "The customer bought a product 5 days ago and wants a full refund. They have their order number ready (ORD-12345).",
  "termination": "The assistant confirms the refund will be processed",
  "first_message": "Hi, I want to return a product I bought last week",
  "max_turns": 8,
  "assertions": [
    {"criteria": "The assistant asks for the order number"},
    {"criteria": "The assistant confirms the refund amount"},
    {"criteria": "The assistant mentions the expected refund timeline"}
  ]
}'
```

### Example: Batch Create Test Cases

```bash
python3 scripts/qa.py cases batch PLAYBOOK_BASE_ID --body '{
  "cases": [
    {
      "name": "greeting-basic",
      "scenario": "A new customer visits for the first time and says hello.",
      "termination": "The assistant greets the customer and offers help",
      "max_turns": 3,
      "assertions": [
        {"criteria": "The assistant introduces itself"},
        {"criteria": "The assistant asks how it can help"}
      ]
    },
    {
      "name": "out-of-scope-question",
      "scenario": "The customer asks about something completely unrelated to the business, like the weather or sports.",
      "termination": "The assistant redirects to relevant topics or escalates",
      "max_turns": 5,
      "assertions": [
        {"criteria": "The assistant does not make up an answer about unrelated topics"},
        {"criteria": "The assistant politely redirects the conversation"}
      ]
    },
    {
      "name": "angry-customer-handoff",
      "scenario": "The customer is very angry about a delayed order. They curse and demand to speak to a manager. The order number is ORD-99999.",
      "termination": "The assistant escalates to a human agent",
      "max_turns": 6,
      "assertions": [
        {"criteria": "The assistant remains calm and professional"},
        {"criteria": "The assistant attempts to help before escalating"},
        {"criteria": "The assistant escalates to a human agent"}
      ],
      "assertion_tags": ["escalation"]
    },
    {
      "name": "pricing-inquiry",
      "scenario": "The customer wants to know the pricing for the Pro plan and asks about discounts for annual billing.",
      "termination": "The assistant provides pricing information",
      "max_turns": 5,
      "assertions": [
        {"criteria": "The assistant provides the correct Pro plan price"},
        {"criteria": "The assistant mentions annual billing discount if available"}
      ]
    }
  ]
}'
```

### Example: Run Evaluation

```bash
# First, get the playbook version to test
python3 scripts/qa.py chat PLAYBOOK_BASE_ID --list-versions

# Trigger a run against a specific version
python3 scripts/qa.py runs create PLAYBOOK_BASE_ID \
  --playbook-id PLAYBOOK_VERSION_ID

# Trigger with user context (simulate a specific user)
python3 scripts/qa.py runs create PLAYBOOK_BASE_ID \
  --playbook-id PLAYBOOK_VERSION_ID \
  --context '{"email": "vip@company.com", "plan": "enterprise"}'

# Poll status until completed (check every 15 seconds)
python3 scripts/qa.py runs status RUN_ID

# Get full results
python3 scripts/qa.py runs results RUN_ID -o eval_results.json
```

### Example: Simulate a Conversation

Chat directly with a playbook without creating test cases. Useful for ad-hoc testing.
The chat command shows the **full picture** of what the assistant did: skills loaded,
KB articles searched, tool calls made, citations used, events emitted, and agent reasoning.

```bash
# Start a new conversation
python3 scripts/qa.py chat PLAYBOOK_BASE_ID \
  --message "Hi, I need to cancel my subscription"

# Continue the same conversation (use the conversation_id from the response)
python3 scripts/qa.py chat PLAYBOOK_BASE_ID \
  --message "My account email is test@example.com" \
  --conversation-id conv_qa_12345

# Chat with user context
python3 scripts/qa.py chat PLAYBOOK_BASE_ID \
  --message "Check my order status" \
  --context '{"email": "john@example.com", "order_id": "ORD-555"}'

# Verbose mode — show full tool results and raw JSON response
python3 scripts/qa.py chat PLAYBOOK_BASE_ID \
  --message "I want a refund" --verbose
```

#### Chat Output Breakdown

The chat command prints a structured breakdown to stderr:

| Section | What it shows |
|---------|---------------|
| **Events** | Messages (stdout), labels, notes, handoffs, priority changes |
| **Tool calls** | Every tool the assistant invoked, with arguments and result summaries |
| **Citations** | KB articles referenced in the response, with source and snippet |
| **Explanation** | Agent reasoning summary (why it chose a particular path) |

**Tool call details** (always shown):
- `load_skill [custom]` — which skill was loaded (or not loaded)
- `search_knowledge_base [kb_search]` — query used, number of results, relevance scores, and content snippets
- Custom API tools — name, arguments, and result preview

**`--verbose` / `-v`** expands tool results to 500 chars and dumps the full JSON response.

### Example: Analyze Results

```python
import json

with open("eval_results.json") as f:
    results = json.load(f)

total = len(results)
passed = sum(1 for r in results if r["status"] == "passed")
failed = sum(1 for r in results if r["status"] == "failed")
errored = sum(1 for r in results if r["status"] == "error")

print(f"Results: {passed}/{total} passed ({passed/total*100:.0f}%)")
if failed:
    print(f"  Failed: {failed}")
if errored:
    print(f"  Errors: {errored}")

print("\nFailed cases:")
for r in results:
    if r["status"] != "passed":
        print(f"\n  [{r.get('case_name', r['case_id'])}] — {r['status']}")
        if r["status"] == "error":
            # Internal error (infra), not an assistant failure — re-run, don't diagnose.
            print(f"    internal error: {r.get('error_message')}")
            continue
        for a in r.get("assertion_results", []):
            verdict = a.get("verdict") or ("passed" if a["passed"] else "failed")
            print(f"    [{verdict.upper()}] {a['criteria']}")
            if verdict == "failed":
                print(f"           {a['explanation']}")

# Criteria lint: every ambiguous verdict is a test to rewrite (suite-wide, not just failed cases)
print("\nAmbiguous criteria (rewrite these):")
for r in results:
    for a in r.get("assertion_results", []):
        if a.get("verdict") == "ambiguous":
            print(f"  - [{r.get('case_name')}] {a['criteria']}")
            print(f"    sugerencia: {a.get('rewrite_suggestion')}")
```

### Example: Compare Two Versions

```python
import json

# Load results from two different runs (different playbook versions)
with open("results_v3.json") as f:
    v3 = json.load(f)
with open("results_v5.json") as f:
    v5 = json.load(f)

# Build lookup by case name
v3_by_case = {r.get("case_name", r["case_id"]): r for r in v3}
v5_by_case = {r.get("case_name", r["case_id"]): r for r in v5}

all_cases = sorted(set(v3_by_case) | set(v5_by_case))

print(f"{'Case':<30} {'v3':>8} {'v5':>8} {'Delta':>8}")
print("-" * 56)
for case in all_cases:
    r3 = v3_by_case.get(case)
    r5 = v5_by_case.get(case)
    s3 = r3["status"] if r3 else "—"
    s5 = r5["status"] if r5 else "—"
    delta = ""
    if s3 == "passed" and s5 != "passed":
        delta = "REGRESSION"
    elif s3 != "passed" and s5 == "passed":
        delta = "FIXED"
    print(f"  {case:<28} {s3:>8} {s5:>8} {delta:>8}")
```

---

## Workflows

### 1. Initial QA Setup

When setting up QA for an assistant for the first time:

1. **List playbooks** — identify the assistant and its base_id
2. **Design test cases** — cover happy paths, edge cases, error handling
3. **Batch create** — create all cases in one API call
4. **Run first eval** — establish a baseline
5. **Review results** — identify gaps in the assistant's behavior

### 2. Pre-Deploy Validation

Before deploying a new playbook version:

1. **Get the new version ID** — from the playbook version history
2. **Run eval** against the new version
3. **Compare with baseline** — check for regressions
4. **If pass rate drops** — investigate failing cases before deploying

### 3. Ongoing Monitoring

Periodically run evals to catch drift:

1. **Trigger run** against the active version
2. **Check pass rate** — compare with historical runs
3. **Investigate new failures** — read the conversation + assertion explanations
4. **Update test cases** — add new cases for issues found in production (use data-expert skill to find problematic conversations)

### 4. Triage a customer complaint

The most common request — full detail in the [QA Practice Workflow](#qa-practice-workflow-read-this-first) section at the top. Short form:

1. **data-expert** → pull the full conversation: messages, events, tool calls, model, playbook version, user_context
2. **builder** → pull the assistant content (instructions + skills) for that exact version
3. **Pin down the incorrect behaviour** — confirm with the user (offer hypotheses with hints) if it wasn't stated
4. **Root-cause** — wrong / misinterpreted / missing instruction, or wrong layer (skill description, KB, tool)
5. **Propose the fix** — minimal diff + regression risk; get user feedback before iterating
6. **REQUIRED: ask the user what to mock** — enumerate available tools, get confirmation
7. **Reproduce + iterate**: `qa.py chat --instructions ... --tool-mocks-file ...` until the bad behaviour is gone — in-memory overrides ONLY, never by saving a version. Read the full response (events, tool calls, citations, explanation), not just the assistant message.
8. **Human applies the new version** — deliver the final content, wait for confirmation + the new version ID
9. **Eval coverage**: persist case(s) sized to the fix, run only them against the new version, then offer a full-suite run to catch regressions.
