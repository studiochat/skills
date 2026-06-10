---
name: continuous-improvement
description: >
  The proactive loop for shipping a behaviour change to an assistant — adding or
  changing a policy in the instructions or casuísticas (skills). Use when the request
  is "necesitamos que el asistente haga X", "agregá esta política", "cambiá el tono",
  "sumá una casuística para Y", or when a trend surfaced by data (trending topic,
  recurring handoffs, a monitor/alert) justifies an improvement. Drives the loop:
  clarify the policy → decide WHERE it lives (base instruction vs casuística vs KB vs
  example) → minimal draft → validate with in-memory overrides → ship via approvals
  → eval coverage. This is the feature/change-request counterpart to the
  quality-engineer skill (which is the reactive bug-report loop from a conversation ID).
---

# Continuous Improvement

Ship a behaviour change to an assistant: add or change a policy in the instructions or
the casuísticas (skills), validate it without polluting version history, push it through
the approval gate, and close the loop with eval coverage. All API calls are authenticated
automatically via environment variables. The API base URL (`https://api.studiochat.io`) is
hardcoded in the scripts.

This skill is the **proactive** counterpart to [quality-engineer](../quality-engineer/SKILL.md):

| | Entry point | Shape |
|---|---|---|
| **quality-engineer** | a `conversation_id` where the assistant misbehaved | reactive — bug report → root cause → fix |
| **continuous-improvement** | a desired policy/behaviour (a request, or a trend in the data) | proactive — change request → ship a feature |

It owns almost no new mechanics: the building blocks live in [builder](../builder/SKILL.md)
(how to write a casuística, edit instructions, create a KB / example block / tool) and the
validation lives in [quality-engineer](../quality-engineer/SKILL.md) (in-memory overrides,
`dry-run`, mocks, eval cases). What's unique here is **the decision and iteration process** —
above all **Step 2: where does the policy live?**

## Key Terminology

**Assistants and playbooks are the same concept.** In the API, the term "playbook" is used
everywhere — but users refer to them as "assistants," "bots," or "agents." When the user
mentions any of these, they mean a playbook.

**Instructions vs casuísticas (skills):**
- **Instructions** (`content` on the playbook) — the base system prompt, injected into *every*
  conversation the assistant handles.
- **Casuísticas / skills** — per-scenario instruction blocks loaded on demand via `load_skill`,
  and only when the conversation matches the skill's **`description`** (the trigger). Their
  `content` is invisible to the LLM until that happens.

**Playbook IDs:**
- `playbook_base_id` — stable ID across all versions of an assistant. Use this for skill/version management.
- `playbook_id` — ID of a specific version.

## Setup

```bash
export STUDIO_API_TOKEN="sbs_your_api_key_here"
export STUDIO_PROJECT_ID="your-project-uuid"
```

API keys are available by request from the Studio Chat team at hey@studiochat.io.

---

## Continuous Improvement Workflow (read this first)

The loop has **two entry points** that converge on the same flow:

- **A) Explicit request** — "agregá esta política", "quiero que el asistente haga X",
  "cambiá el tono", "sumá una casuística de Y".
- **B) Data-driven** — a pattern that surfaced through [data-expert](../data-expert/SKILL.md):
  a trending topic, handoffs that keep repeating, a monitor or alert that fired. The
  improvement is justified by the data, not by an explicit ask.

```
Policy / trend → Placement decision → Minimal draft → Validated change → Approved version → Eval coverage
```

There are **four user checkpoints** where you MUST stop: clarifying the policy (Step 1, if
ambiguous), feedback on the draft (Step 3), the mock question (Step 4), and waiting for the
human to approve each change (Step 5) — plus the full-suite offer at the end (Step 6). Don't
barrel through them.

### Step 1 — Clarify the policy (USER CHECKPOINT if unclear)

End this step with explicit agreement on **what the assistant must / must not do**, and the
**edge cases**. Concretely:

- What's the desired behaviour, in one sentence?
- When does it apply — always, or only in certain situations? (this directly feeds Step 2)
- What must it NOT do / what are the boundaries?
- If it came from **data**, bring the evidence: pull the conversations / trending topic /
  monitor run with [data-expert](../data-expert/SKILL.md) so the policy is grounded in real
  cases, not a hunch. A handful of real transcripts makes the placement and the draft far
  more accurate.

Don't move forward on a vague ask ("que sea más amable"): pin it to observable behaviour
("que salude por el nombre cuando viene en el `user_context`, y que no use más de un emoji
por mensaje").

### Step 2 — Decide WHERE the policy lives (the heart of this skill)

Everything the assistant reads at runtime lives in one of a few layers. Putting a policy in
the wrong one is the most common mistake — a global rule buried in a casuística silently never
fires; a one-off scenario stuffed into the base instructions bloats every conversation and
invites regressions.

**The deciding question is scope: does the policy affect EVERY conversation, or only the
conversations that match a trigger?**

| Scope | Goes in | Why | Examples |
|---|---|---|---|
| **Global** — applies to every conversation the assistant handles | **Base instruction** (`content`) | It's always in the prompt, so it always applies | tono · usar / no usar emojis · política de tagging global · formato de respuesta · idioma · reglas de marca |
| **Segmented** — only when a specific situation occurs (fired by the casuística's `description`/trigger) | **Casuística (skill)** — new or edit an existing one | It loads only for the conversations that match the trigger | derivación (solo en conversaciones con derivación) · robo de tarjeta (solo cuando hablan de robo de tarjeta) · reembolsos · un flujo de producto puntual |

The test is literally: **"¿esto tiene que pasar en TODAS las conversaciones, o solo en las que
disparan el trigger de la descripción?"** All-conversations → instruction. Triggered-segment →
casuística.

#### New casuística vs edit an existing one

Once you've decided it's a casuística:

- **An existing casuística already covers that segment** (its `description` already fires on
  those conversations) → **edit it**: extend its `content`. Don't create a second skill that
  competes for the same trigger.
- **No existing casuística covers the segment** → **create a new one**. Its `description` is
  what makes it load — write it to capture exactly the situation that should trigger it (the
  LLM picks skills off `name` + `description`, never the `content`). A casuística with a vague
  description never loads, no matter how good its content is.

#### When it's neither instruction nor casuística

Some policies belong in a different layer entirely — see [builder](../builder/SKILL.md) for the mechanics:

| The change is really… | Layer | Note |
|---|---|---|
| **Factual info that changes over time** (precios, horarios, una política que se actualiza seguido) | **Knowledge base** (or a correction note on a KB item) | Don't hard-code volatile facts into the prompt — put them where they can be searched and updated without a version bump. |
| **Tone / style shown by example** | **Example block** via `{{ examples: ID }}` | Never paste sample conversations into instruction/skill prose — always a block. |
| **A real-world action** (mandar un Slack, crear un booking) | **API tool / toolkit action** | Wire it with the macro; the object must exist first. |
| **A global tagging policy** | **Base instruction**, with each tag value in single backticks | The whitelist is parsed from backticked tag values — see builder's Tagging section. |

State your placement decision and the reason before drafting — it's the call most worth
getting agreement on.

### Step 3 — Minimal draft + regression risk (USER CHECKPOINT)

Write the smallest change that implements the policy, and present it before iterating:

- **what changes** — which instruction / which casuística (new or edited), as a minimal diff.
- **what to wire** — a policy almost always implies a **building block**, not just prose: an
  inline example, a KB search, a Slack notification, an API call, a handoff. **Offer the macros
  proactively** — the user often won't think to ask. See [Editing isn't just writing — wire the
  building blocks](#editing-isnt-just-writing--wire-the-building-blocks).
- **why** it sits in that layer (the Step 2 decision).
- **regression risk — sized by scope.** This is where placement and blast radius connect:
  - A **base-instruction** change touches *every* conversation → wide blast radius → it needs
    broader eval coverage in Step 6.
  - A **casuística** change only affects its triggered segment → contained blast radius.
  - Pick placement by **scope correctness first** — never demote a genuinely global rule into a
    casuística just to shrink the blast radius (it won't fire everywhere it should). The scope
    just tells you how much coverage the change demands.

Keep the diff tight: broad rewrites are how regressions sneak in. Then wait for feedback — the
user often knows constraints invisible in the data (business rules, upcoming changes, tone).

### Step 4 — Validate with in-memory overrides (USER CHECKPOINT: mocks)

**Iterate the same way QA does — never save a throwaway playbook version to test.** Everything
runs through the [quality-engineer](../quality-engineer/SKILL.md) override flow: `qa.py chat`
and `qa.py runs create` with `--instructions` / `--instructions-file` / `--skills-file` (full
replace or surgical `add`/`replace`/`remove` patch). Nothing is persisted, no version is bumped,
no approval is generated yet.

**Before chatting / before any eval run, ask the user what to mock** (this is required, same as
QA Step 6) — enumerate the playbook's tools so they can pin down deterministic conditions.

Then:

1. **Establish the baseline** — reproduce *current* behaviour with no overrides, so you can
   prove the policy isn't already satisfied.
2. **Apply the draft** — override the instructions (global policy) or patch the skills (new /
   edited casuística) and re-run the same scenarios. For a new casuística, **confirm it actually
   loads**: watch the `load_skill` call in the `qa.py chat --verbose` output. If it doesn't fire,
   the `description` is the problem, not the content (Step 2).
3. **Dry-run a candidate eval case** (optional) — `qa.py dry-run start` validates a case is
   gradable before you persist it.

Iterate `--instructions` / `--skills-file` / mocks until the new behaviour is reliable **and**
you've spot-checked that adjacent scenarios still behave (a quick regression pass over whatever
shares the layer you touched).

### Step 5 — Ship through the approval gate (USER CHECKPOINT: wait for approvals)

This is the "CI" of continuous-improvement — and the one place it differs from QA's pure
hand-off. When the change is validated, **push it via [builder](../builder/SKILL.md)**:

- a global policy → `PATCH /playbooks/BASE_ID/latest` (fetch the latest first, apply on top).
- a new / edited casuística → the skill endpoints (`POST`/`PATCH …/skills/...`).

**Every instruction or skill modification you push generates an approval — one per change —
that a human must approve before it goes live.** Sandbox (`sbs_`) callers get a `202` with
`{"approval_id": "...", "status": "pending", "message": "Request queued for admin approval."}`
instead of an immediate write. So:

- Push **one change per logical edit** so each approval is reviewable on its own (don't bundle a
  tone change and a new refund casuística into one opaque diff).
- **Describe every approval right after the 202** — the reviewer reads your text, not the payload:

  ```bash
  python3 scripts/api.py "/approvals/APPROVAL_ID/description" -X PATCH --body '{
    "description": "WHAT changes and WHY, plus the before → after in plain language."
  }'
  ```

  Include the policy being added/changed, what motivated it (the user ask, the trend, the
  conversation), and the observable before → after. Pending-only (409 once reviewed).
- **Confirm each change with the user before pushing it** (builder confirms every write anyway),
  then **wait for the human to approve** the queued change(s) and for the **new version to go
  live**. Get the new version ID.
- Don't author eval runs against the change assuming it'll be approved — wait for it to be live.

### Step 6 — Eval coverage (USER CHECKPOINT: full-suite offer)

Close the loop with [quality-engineer](../quality-engineer/SKILL.md), scaling coverage to the
scope from Step 3:

1. **Author the case(s)** — a scenario that exercises the new behaviour, a `termination`,
   structured assertions for what must (not) happen, and the same `tool_mocks` you used to
   validate so the case is deterministic.
   - A **casuística** change → at least one case that triggers the segment (and one adjacent
     case that must *not* trigger it, to prove the trigger is scoped right).
   - A **base-instruction** change → cases across several flows, since it touches everything.
2. **Run only the new case(s)** against the new (approved) version — no overrides now, the
   change is live; test the real thing.
3. **Offer a full-suite run (USER CHECKPOINT)** — especially for base-instruction changes,
   offer to run the whole eval suite against the new version to catch regressions elsewhere.
   It costs time and tokens, so it's the user's call — but always offer.

---

### Cheat sheet — which mechanism for which question

| Question | Mechanism |
|---|---|
| "Is this a real, grounded need?" | data-expert — pull the trend / conversations behind it |
| "Does this apply to every conversation, or just a segment?" | The Step 2 scope test → instruction vs casuística |
| "Is there already a casuística for this segment?" | builder — list skills; edit it instead of adding a rival |
| "Will the new casuística even load?" | `qa.py chat --verbose` → watch the `load_skill` call (it's the `description` that fires it) |
| "Does the draft work without breaking neighbours?" | `qa.py chat` / `runs create` with `--instructions` / `--skills-file` overrides — no save |
| "Is my new eval case gradable?" | `qa.py dry-run start` |
| "How does the change ship?" | Push via builder → approval per change → human approves → version goes live |
| "Did the change land without regressions?" | `qa.py runs create` against the new version — offer the full suite |

---

## Editing isn't just writing — wire the building blocks

Changing instructions or a casuística means **assembling building blocks**, not transcribing
prose. The assistant gets its power from the macros and behaviours you wire into the text; a
policy written as plain paragraphs when it should fire a tool, search a KB, or show an example is
a half-built change. **As you draft (Step 3), read the policy for the signals below and OFFER to
wire the right block** — the user frequently won't know to ask for it, so it's on you to propose it.

### Macros — reference an object (the object must exist first)

These are the four inline macros the compiler understands. The object has to exist **before** you
reference it (no save-time validation — a dangling macro silently degrades to literal text), so
offering one often spawns a quick sub-task in [builder](../builder/SKILL.md) to create it.

| When the policy implies… | Offer to wire | Macro | Built via (builder) |
|---|---|---|---|
| "answer from our info", "look this up", "según nuestra política de X" | a **KB search** | `{{ kb(KB_ID) }}` | Knowledge Bases |
| "here's how a good reply sounds", a tone/style to imitate, a sample turn | an **inline example** | `{{ examples: BLOCK_ID }}` | Example Blocks — *the only way to add examples; never paste sample turns into prose* |
| "notify the team", "avisá por Slack", "escalá al canal de guardia" | a **toolkit action** | `{{ custom_tool: short_name }}` | Toolkit Actions — *the toolkit must be connected by the user first; you can't connect it* |
| "check the order", "call our API", "consultá el estado de X" | a **custom API tool** | `{{ tool(TOOL_ID) }}` | API Tools |

### Behaviours — instructed in prose (events the assistant emits, no macro)

These aren't macros — you wire them by **telling the assistant when to do it** inside the
instruction/casuística:

| When the policy implies… | Wire by instructing… |
|---|---|
| "derivá a un humano", "escalá", "que lo tome una persona" | a **handoff** — describe the exact trigger condition |
| "etiquetá como X", a tagging rule | a **tag** — name the value in single backticks so it's whitelisted (see builder's Tagging) |
| "marcá urgente", triage by severity | a **priority** set |
| "dejá nota para el próximo agente" | a **private note** |

### The proactive ask (this is the behaviour the user expects)

Don't wait to be told. When the policy *type* commonly pairs with a block, **ask**:

> User: "Necesito una casuística de emergencias."
> You (Step 1/3): "Dale. Una pregunta: cuando se dispara una emergencia, ¿querés que el asistente
> **mande un Slack** al equipo de guardia, además de responderle al cliente? Si sí, lo dejo cableado
> en la casuística."

If yes → check the Slack toolkit is connected (`GET /custom-toolkits`; if not, ask the user to
connect it — you can't), create the tool configuration in [builder](../builder/SKILL.md), and embed
`{{ custom_tool: short_name }}` in the casuística `content` at the step that handles the emergency —
next to the instruction describing *when* and *what* to send. The casuística is now a wired flow
("detectá la emergencia → respondé con calma → `{{ custom_tool: notify_guardia_x1y2z }}` → derivá"),
not just a paragraph of advice.

Same reflex for the others: a "explicá la política de reembolsos" casuística should probably
`{{ kb(...) }}` the refund policy rather than hard-code it; a "manejá reclamos con este tono"
casuística should carry an `{{ examples: ... }}` block, not a described tone.

> **Validate the wiring, not just the words (Step 4).** After embedding a macro, run `qa.py chat
> --verbose` and confirm it actually fired — the `search_knowledge_base` / tool call shows up in the
> output, and `[MOCKED]` tells you a stub answered. A macro that points at a missing object just
> vanishes at runtime; the verbose run is how you catch it before shipping.

---

## Worked example — "no quiero que el bot prometa reembolsos fuera de política"

1. **Clarify** — desired: when an order is outside the 30-day window, the assistant explains the
   policy and escalates instead of promising a refund. Edge case: what if the user is a VIP?
   (ask). Grounded by 3 real conversations from data-expert where it over-promised.
2. **Placement** — this only matters in **refund** conversations, not all of them → **casuística**.
   A `reembolsos` skill already exists and its `description` fires on refund talk → **edit it**,
   don't add a rival.
3. **Draft** — add to the `reembolsos` content: "Antes de confirmar un reembolso, verificá la
   ventana de 30 días. Fuera de ventana: explicá la política y derivá; nunca prometas el
   reembolso." Regression risk: contained to the refund segment.
4. **Validate** — ask what to mock (`lookup_order` with a 60-day-old order). Baseline reproduces
   the over-promise; with the `--skills-file` patch it explains + hands off. Confirm the
   `reembolsos` skill loaded in the verbose output.
5. **Ship** — `PATCH …/skills/reembolsos` via builder → 202 approval queued → human approves →
   new version live, grab the version ID.
6. **Evals** — one case: 60-day order → assert `handoff` + `tool_not_called process_refund` +
   text "explica la política de 30 días". Run it against the new version; offer the full suite.

Contrast with a **global** change — "de ahora en más, máximo un emoji por mensaje": that's every
conversation → **base instruction**, pushed via `PATCH /playbooks/BASE_ID/latest`, and it warrants
eval cases across several flows because its blast radius is the whole assistant.

---

## Cross-skill map

This skill orchestrates three others — reach for them rather than re-deriving:

- **[data-expert](../data-expert/SKILL.md)** — ground the policy in real conversations / trends (entry point B, Step 1).
- **[builder](../builder/SKILL.md)** — the mechanics of every layer: editing instructions, skill CRUD, KBs, example blocks, tools, and the macro/tagging rules. Also where the change is pushed (Step 5).
- **[quality-engineer](../quality-engineer/SKILL.md)** — in-memory overrides + mocks to validate (Step 4) and eval cases to cover (Step 6). It's also the *reactive* sibling: if the change is driven by a specific bad conversation rather than a policy, start there instead.
