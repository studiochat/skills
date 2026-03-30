---
name: quality-engineer
description: >
  Test and evaluate AI assistant behavior. Create test cases, run evaluations,
  analyze results, simulate conversations, and compare playbook versions.
  Use when asked to test an assistant, create QA scenarios, run evals,
  check assertion pass rates, or verify assistant behavior.
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
```

API keys are available by request from the Studio Chat team at hey@studiochat.io.

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

# Trigger an eval run
python3 scripts/qa.py runs create PLAYBOOK_BASE_ID --playbook-id VERSION_ID [--context '{}']

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
3. **Checks termination** — an LLM judges whether the expected outcome was reached
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

---

## Writing Good Test Cases

### Scenario Guidelines

The scenario tells the **simulated user** how to behave. Write it from the user's perspective:

- Describe what the user wants, not what the assistant should do
- Include constraints: "the user is impatient," "the user doesn't have their order number"
- Keep it focused — one scenario per case

### Assertion Guidelines

Assertions are **evaluated by an LLM** after the conversation. Write them as clear, verifiable statements:

- Good: "The assistant mentions the 30-day refund policy"
- Good: "The assistant asks for the order number before proceeding"
- Bad: "The assistant is helpful" (too vague)
- Bad: "Response time is under 2 seconds" (can't be evaluated from conversation text)

### Tag Assertions

Use `assertion_tags` to verify the assistant applied specific tags during the conversation.
For example, if your assistant is configured to tag billing conversations with "billing":

```json
{
  "assertion_tags": ["billing"]
}
```

The case passes the tag assertion only if the assistant actually applied the "billing" tag.

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
        for a in r.get("assertion_results", []):
            status = "PASS" if a["passed"] else "FAIL"
            print(f"    [{status}] {a['criteria']}")
            if not a["passed"]:
                print(f"           {a['explanation']}")
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
