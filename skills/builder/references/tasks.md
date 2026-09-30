# Tasks — proactive work an assistant is assigned

A **task** is concrete, finite work an assistant is sent to drive to completion inside one
conversation: *collect these three documents*, *schedule the visit*, *regularize this debt*.
It is not part of the assistant's standing instructions and it is not a skill.

> A skill **waits** for the situation that matches it. A task is **already running** from the
> moment it is assigned, and the assistant is the one who opens it.

Tasks may need to be enabled for your account. Where they aren't, the dashboard hides the whole
surface and the task endpoints answer `403` — check before promising it.

---

## 1. Where a task lives

| | Where | Editing it |
|---|---|---|
| **The catalog** | `playbooks.tasks` on the playbook **VERSION** | A task is text, so editing one **creates a new version** — exactly like editing a skill |
| **Which task a conversation pursues** | the conversation's single slot | set per conversation, at assignment time — never here |

One live task per conversation, enforced in the database. Assigning a second one while the
first is `in_progress` is a **409**. Re-assigning the *same* task is a no-op, so retries are safe.

A task is three fields and nothing else:

```json
{ "id": "tsk_7f3ab2c19d04", "name": "cobrar-deuda", "instructions": "…" }
```

- `id` — minted by the backend on **write**, stable across renames and versions. This is what
  every integration references. Never invent one; send a task without `id` to create it.
- `name` — kebab-case, unique within the assistant. It is a label, not a trigger.
- `instructions` — prose. This is the entire design surface. Everything below is about writing it.

### Reading and writing the catalog

```bash
# Read (the ids live here — you need them to edit or assign)
python3 scripts/api.py "/playbooks/BASE_ID/latest" | jq '.tasks'

# Write — FULL REPLACEMENT of the array, creates a version, queued for approval
python3 scripts/api.py "/playbooks/BASE_ID/latest" -X PATCH --body '{
  "tasks": [
    {"id": "tsk_7f3ab2c19d04", "name": "cobrar-deuda", "instructions": "…"},
    {"name": "validar-identidad", "instructions": "…"}
  ]
}'
```

**`tasks` is a full replacement.** Read the current array first and resend it whole with your
edit applied — a PATCH carrying only the task you're adding **deletes every other one**. Keep
each existing task's `id`: drop it and the backend mints a new one, which orphans every
integration and every open run pointing at the old id. Send `"tasks": []` to turn the assistant
back into a plain reactive one.

---

## 2. Writing the instructions

The body is prose, not structured criteria — deliberately. A flat list of success/failure
conditions cannot express *"insist for three days, then stop"*, and that branch is most of what
a real task is.

**A task worth writing has this shape:**

1. **The outcome, first, in one line.** What has to be true for this to be over.
2. **The steps, in order**, as things to *get*, not things to *say*. One per line.
3. **Both terminations marked with the pills** — `{{success}}` and `{{failure}}` (§3).
4. **The give-up rule in prose**: how long to insist, how many times, what makes it not worth
   continuing. This is the only place that rule exists — no config field carries it.
5. **Nothing about tone, language, brand or formatting.** Those are in the base instructions and
   still apply. A task that re-states them just spends tokens and invites contradictions.

```
Conseguir los tres documentos que el equipo de fraude necesita para validar la cuenta:
foto del DNI (frente y dorso), selfie sosteniendo el DNI, y comprobante de domicilio
de los últimos 90 días.

Pedilos de a uno, en ese orden. Cuando manden uno, confirmá que se ve completo y legible
antes de pedir el siguiente; si está cortado o borroso, pedí que lo manden de nuevo
explicando qué se ve mal.

Si dicen que no tienen comprobante de domicilio a nombre propio, sirve uno a nombre de
un conviviente más una foto de algo que los vincule (contrato, factura compartida).

Cuando los tres estén recibidos y legibles, {{success}}.

Si dicen explícitamente que no van a mandar la documentación, o si pasaron tres días
desde el primer pedido sin que hayan mandado ninguno, {{failure}}.
```

### What the assistant is *already* told — don't write it again

The runtime wraps every task with a fixed block. The assistant already knows to:

- move the task forward in **every** reply, this one included;
- answer what the person actually said **first**, then take the next step in the same message;
- take real steps, not announcements — never *"cuando terminemos también te voy a pedir…"*;
- **open with the task**: no *"¿en qué te puedo ayudar?"*, because that hands the agenda back;
- one step at a time, never the whole checklist at once;
- follow the person if they go somewhere else, resolve it, and come back;
- use its skills normally (`load_skill`) — the task says WHAT to get done, not how to talk;
- report `status` + `reason` on every turn.

Writing any of that into the task text is wasted prose. Spend it on the domain instead: what
counts as a valid document, what to do when they push back, which exception is acceptable.

### Common mistakes

| Mistake | Why it hurts |
|---|---|
| A task that is really a topic (*"atender consultas de facturación"*) | That's a **skill**. A task has to be able to finish. |
| No `{{failure}}` | The task never ends. It stays `in_progress` forever, holds the conversation's only slot, and keeps qualifying for follow-ups until `task_nudge_max` runs out. |
| No `{{success}}` | The assistant has no sentence that means "done" and will keep pushing past the goal. |
| Success and failure in a `Criterios:` block at the end | Works, but weakly — the pill belongs **inside the sentence that describes the condition**, so the model reads the branch and its outcome as one thought. |
| A whole checklist in one paragraph | The assistant dumps it in one message. Write the steps as steps. |
| Restating tone/brand rules | Contradicts the base instructions sooner or later. |
| Two tasks that overlap | Only one can run at a time per conversation; overlapping tasks means whoever assigns has to guess. |

---

## 3. The outcome pills: `{{success}}` and `{{failure}}`

They are **not** conditions the platform evaluates. They expand, at prompt-build time, into a
fixed instruction about the status field the assistant reports every turn:

| You write | The model reads |
|---|---|
| `{{success}}` | `the task is DONE (report task.status = "done")` |
| `{{failure}}` | `the task has FAILED (report task.status = "failed")` |

That's the whole mechanism, and it is why the wording is fixed: however you phrase the sentence
around the pill, the instruction the model gets is identical.

**Write them inline, in the sentence that states the condition:**

```
✅  Cuando los tres documentos estén recibidos y legibles, {{success}}.
✅  Si pasaron tres días desde el primer pedido sin respuesta, {{failure}}.
✅  Si el cliente dice que ya pagó, verificá con {{ tool(TOOL_ID) }}; si figura pagado, {{success}}.

❌  Criterio de éxito: los tres documentos.        (no pill — nothing marks the terminal state)
❌  {{success}} = documentos completos            (reads as an assignment, not as a branch)
```

Use as many as the task has branches. A collections task can perfectly have three `{{success}}`
(paid now / promised and scheduled / already paid) and two `{{failure}}` (refuses / no answer in
three days). That branching is exactly why this is prose instead of a criteria list.

### What the status actually does

Every turn, the assistant reports `{"status": "in_progress" | "done" | "failed", "reason": "…"}`.
The server stamps the task's `id` and `name` onto it, records it on the run, and returns it in
the `task` block of the chat response.

- **Terminal is terminal.** `done` / `failed` closes the run, frees the conversation's slot and
  removes it from follow-up eligibility for good.
- **It is self-reported.** Nothing verifies it independently. For a compliance-grade case, treat
  `done` as the assistant's claim, and check the artifacts (the uploaded files, the tool call)
  separately.
- **A dropped block doesn't reset anything.** If the model omits the field on a turn, the last
  known status stands.

---

## 4. Macros work inside a task

A task's instructions share the macro namespace with instructions and skills. All of these
expand, and the resources they reference are wired into the turn from turn zero (no `load_skill`
needed):

`{{ kb(KB_ID) }}` · `{{ tool(TOOL_ID) }}` · `{{ custom_tool: short_name }}` ·
`{{ examples: BLOCK_ID }}` · `{{ integration(TOOLKIT) }}` · `{{ context: path | fallback }}`

See **Template macros (the "pills")** in `SKILL.md` for what each one does. The object has to
exist first — a macro pointing at a missing id silently degrades to literal text.

### Per-conversation parameters: `inputs` and `{{ input: }}`

The task text is the same for everyone; what differs per person — the amount owed, the questions
to ask — travels as **`inputs`** when the task is assigned or started (§7). `inputs` is a
free-form JSON object, yours to shape. It is stored on the task run for as long as the task lives
and shown to the assistant in its task block on every turn, one `key: value` line per top-level
key. Read a value in the task text with the value pill:

```
Preguntale al cliente, de a una, las preguntas de {{ input: preguntas | las preguntas pendientes }}.
El saldo adeudado es {{ input: deuda.monto | N/A }}.
```

Grammar: a dotted path and an optional `| fallback`. A missing or empty value renders the
fallback, or the literal `N/A` when there is none — the pill never errors, so a wrong path is
only visible as `N/A` in the prompt.

`inputs` is **not** `context`. `context` is the channel's per-turn view of the conversation
(`{{ context: }}`); `inputs` is what the assigner chose for this run (`{{ input: }}`). They never
overlap, so nothing a channel sends can shadow an input. Re-assigning a task that is already
running is a no-op and does **not** rewrite its `inputs`.

> **Gotcha — tags don't whitelist from a task.** The closed list of tags the assistant may emit
> is parsed from backticked tokens in the **base instructions and skills only**; a task's text is
> not scanned. A tag that appears only inside a task is silently dropped from the output. If a
> task needs to tag (`` `promesa_de_pago` ``), declare that tag in the base instructions too.

---

## 5. When the customer goes quiet

A task is a job, not a message: silence doesn't finish it. A scheduled job periodically looks at
every conversation carrying a live task and decides whether to follow up. Follow-ups go out
through the channel the conversation is on, so that channel has to support outbound messages.

**The pacing is arithmetic, not judgment.** A run isn't even considered until the conversation
has been quiet for `delay × 3^follow-ups-already-sent`. With the default 60-minute delay that's
**1h → 3h → 9h** at the earliest — the job runs periodically, so a follow-up lands some time
after its floor, not on it. Only runs that clear that floor get a (cheap) model call asking whether a
message right now actually serves the task — which is what catches *"te pago el viernes"* and
*"no me contacten más"*.

Never candidates: handed-off, preview and eval conversations, and conversations with no messages.

Two settings, on the assistant (playbook-level, **not** versioned — changing them creates no new
version, but the write is still queued for approval):

```bash
python3 scripts/api.py "/playbooks/PLAYBOOK_ID/settings" -X PATCH --body '{
  "task_nudge_delay_minutes": 60,
  "task_nudge_max": 2
}'
```

| Setting | Default | What it is |
|---|---|---|
| `task_nudge_delay_minutes` | `60` | The base delay. **This is the urgency dial** — set it to 15 and the schedule becomes 15m / 45m / 2h15. There is no separate urgency field. |
| `task_nudge_max` | `2` | Ceiling on follow-ups. A **backstop**, not the give-up rule — the task's own `{{failure}}` should normally fire first. |

> `proactive_webhook_url` (and its signing secret) still appear in the settings payload but are
> **no longer read**. Proactive starts go through a channel — see `channel_id` in §7. Don't set it.

Only a **delivered** follow-up counts against `task_nudge_max`; deciding not to write costs
nothing. Both counters show up on the task log.

---

## 6. Trying it before it ships

The preview runs the real thing minus delivery: assign the task, then run a turn with **no user
message**, which is exactly what a production proactive start sends. Use the version you are
editing, so a task that only exists in a draft is testable before it goes live.

```bash
# 1. Assign. The conversation doesn't have to exist yet — that's the point of
#    keeping assignment out of the chat completion.
python3 scripts/api.py "/playbooks/BASE_ID/conversations/preview-001/task" \
  --params version=7 -X POST --body '{"task_id": "tsk_7f3ab2c19d04"}'

# 2. The turn nobody asked for: empty user_message, the task drives it.
python3 scripts/api.py "/playbooks/BASE_ID/versions/7/preview/chat" -X POST --body '{
  "conversation_id": "preview-001",
  "user_message": ""
}'

# 3. Keep going with real replies, same conversation_id, to see it progress.
```

Read the `task` block that comes back on every turn (`status` + `reason`) — that is the
assistant's own read on where it is.

**What to check, in this order:**

1. **Does the first message open the task?** If it opens with *"¿en qué te puedo ayudar?"*, the
   instructions are describing the task instead of starting it.
2. **One step, not the whole list.** If it dumps every requirement at once, the steps aren't
   written as steps.
3. **Does it reach `done`?** Play the cooperative customer through to the end. If `status` stays
   `in_progress` after the goal is met, the `{{success}}` sentence isn't where the conversation
   actually lands.
4. **Does it reach `failed`?** Play the refusing customer. A task that can't fail will chase
   forever.
5. **Does it survive a detour?** Ask something off-topic mid-task. It should answer, then come
   back.
6. **Does it still sound like the assistant?** Tone comes from the base instructions; if the
   task changed the voice, it's carrying prose it shouldn't.

Preview conversations never qualify for follow-ups, and `?version=` accepts the draft version —
both on purpose.

---

## 7. The rest of the surface, in one line each

Building is the part above. These exist and are worth knowing about when someone asks:

- **Assign in production** — `POST /playbooks/{base_id}/conversations/{conversation_id}/task`
  with `{"task_id": "…", "inputs": {…}}` (`inputs` optional, see §4). Creates the conversation
  row if it doesn't exist. 409 if another task is live, 400 on an unknown id.
- **Read a conversation's task** — `GET` on the same path. Returns `task` (status + reason) and
  the live run's `inputs`.
- **Proactive start** — open a conversation nobody started and speak first. See below.
- **The task log** (every run, with its status, follow-up count and last reason) —
  `GET /projects/{project_id}/task-runs`, filterable by `status`, `task_id`,
  `playbook_base_id`, `conversation_id`.

### Proactive start

`POST /playbooks/{base_id}/conversations/start` (optional `?version=`, default the active one).
Studio Chat assigns the task, writes the opening line, and asks a **channel** registered on the
account to open the conversation on its platform. The channel answers with the platform's
conversation id, which becomes the Studio Chat id — use it with `/chat` from then on.

```bash
python3 scripts/api.py "/playbooks/BASE_ID/conversations/start" -X POST --body '{
  "task_id": "tsk_7f3ab2c19d04",
  "channel_id": "CHANNEL_ID",
  "address": {"channel": "intercom", "contact_id": "5f3c1a9e2b4d", "admin_id": "8291043"},
  "inputs": {"deuda": {"monto": "$14.320"}},
  "user": "CUSTOMER_ID"
}'
```

| Field | Required | What it is |
|---|---|---|
| `task_id` | yes | The task, from this assistant's catalog |
| `channel_id` | unless `deliver: false` | The channel that opens the conversation (Channels in the dashboard). It must support starting conversations and route an inbox to this assistant |
| `address` | unless `deliver: false` | Who to reach and how. **Opaque** — forwarded to the channel verbatim, so its shape is the channel's contract (Intercom: the contact; WhatsApp: the phone plus an approved template) |
| `transport` | no | How the channel reaches the person when it has more than one way — e.g. Intercom `inapp` (Messenger, the default) or `email`. Omit for the channel's default |
| `conversation_id` | no (yes with `deliver: false`) | Pass it when the id is known in advance (WhatsApp: the contact). Leave it out where the platform mints it on send (Intercom) |
| `inputs` | no | The task's per-conversation parameters (§4). Never sent to the channel |
| `context` | no | The opening turn's context, like `context` on `/chat`. Not persisted |
| `user` | no | The customer identity to bind, so the first turn can already read `{{ user: id }}` |
| `opening` | no | `assistant` (default) — the assistant writes the first message. `channel` — the channel opens with what `address` specifies (a WhatsApp template outside the 24h window) and the assistant picks up on the reply |
| `deliver` | no | `false` is the dry run: generates the opener and assigns the task without contacting any channel. Needs `conversation_id`; not available with `opening: "channel"` |

Response (`201`): `conversation_id`, `task`, `message` (the opener), `delivered`, `adopted` (the
id came back from the channel), `transport`.

Errors:

- `400` — task not in the catalog; `channel_id` isn't a channel of this account, can't start
  conversations, doesn't route to this assistant, or doesn't offer the requested `transport`.
  All checked **before** anything is written.
- `403` — tasks aren't enabled for the account.
- `409` — a task is already running on that conversation, or the id the channel returned already
  belongs to another conversation.
- `422` — missing `address` or `channel_id` with delivery on; missing `conversation_id` on a dry
  run; a dry run with `opening: "channel"`.
- `502` — the channel couldn't be reached or couldn't open the conversation.

**Not idempotent.** Calling it twice sends a second opening message to a real person. Use
`deliver: false` to check what the assistant would say.
