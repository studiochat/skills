---
name: kb-suggestions
description: >
  Find knowledge-base gaps for an assistant and record them as suggestions.
  Use when running the (typically hourly, per-project) job that detects what the
  KB fails to answer — frequent searches that returned nothing or only weak
  matches — and drops them into the Suggestions inbox for a human to act on.
  This is the first concrete kind of suggestion we generate. It builds on
  [data-expert](../data-expert/SKILL.md) (to read KB usage) and
  [suggestions](../suggestions/SKILL.md) (to write the findings). It does NOT
  change the assistant — that's [continuous-improvement](../continuous-improvement/SKILL.md).
---

# Knowledge-Base Gap Suggestions

Detect where an assistant's knowledge base is **failing to answer** real user
questions, and record each gap as a `kb` **suggestion**. This is a
**non-deterministic, sampling** task — you won't analyze everything; you go after
the highest-signal queries (most frequent + worst answered) and write clear,
cited suggestions a human can act on.

Auth + the `fetch.py` helper come from [data-expert](../data-expert/SKILL.md) /
[suggestions](../suggestions/SKILL.md):

```bash
export STUDIO_API_TOKEN="sbs_your_project_sandbox_key"
export STUDIO_PROJECT_ID="your-project-uuid"
FETCH="python3 ../suggestions/scripts/fetch.py"   # or ../data-expert/scripts/fetch.py
```

## What a "KB gap" is

A gap is a **question users actually ask that the KB doesn't answer well**.
Signals, strongest first:

1. **Zero-result searches** — the assistant searched the KB and got nothing.
2. **Low-score searches** — it retrieved something but the top relevance score
   is low (weak/irrelevant match) → the answer was probably wrong or vague.
3. **High frequency** — the same weak/empty query keeps coming up. Frequency ×
   weakness = priority.

The backend logs **every** KB search (query + result count + top relevance
score), so these signals are queryable directly — you don't have to crawl
conversations.

## The procedure (one run)

### 1. Pull the gap candidates
The primary source is the KB-search analytics endpoint (queries aggregated by
text, with frequency + score + zero-result count):

```bash
$FETCH "/projects/$STUDIO_PROJECT_ID/analytics/kb-searches" \
  --params max_avg_score=0.5 start_date=2026-06-01 limit=50 -o gaps.json
```
- `max_avg_score` surfaces frequent queries the KB answers **poorly or not at
  all** (queries that never returned anything have a null avg and are included).
- Each item: `{ query, count, avg_top_score, min_top_score, zero_result_count, last_seen_at }`.
- Sort/prioritize by `count` (frequency) and by how bad the score / how many
  zero-results. **Sample the top N** — don't process the long tail.

### 2. Add context (optional but recommended)
For the queries you'll turn into suggestions, enrich with
[data-expert](../data-expert/SKILL.md):
- `GET /projects/{pid}/analytics/kbs` — which KBs/items are getting cited (and
  which aren't) to understand coverage.
- `GET /projects/{pid}/conversations?search=<terms>` then the conversation
  detail to grab **concrete `conversation_id`s** where the gap showed up (the
  detail includes the KB search tool calls: the query, results and scores). Cite
  these conversations in the suggestion so a human can see real examples.
- Group near-duplicate queries by meaning (e.g. "horario", "a qué hora abren",
  "horarios de atención" = one gap). This grouping is your judgment, not a key.

### 3. De-dupe against what already exists
**Before writing anything**, list the project's current suggestions (see the
[suggestions](../suggestions/SKILL.md) skill):

```bash
$FETCH "/projects/$STUDIO_PROJECT_ID/suggestions" --params category=kb limit=100 -o existing.json
```
For each gap you found, decide:
- **Already there** (an existing suggestion is the same problem) → add a
  **follow-up** to that suggestion's `id` with the new cases (this reopens it if
  it was resolved — a regression — and bumps its occurrence count).
- **New** → create a new `kb` suggestion.

This is how we avoid duplicates: the agent matches by meaning and groups via
follow-ups. There is no automatic key.

### 4. Write the suggestion (or follow-up)
Use the [suggestions](../suggestions/SKILL.md) API. A good KB-gap suggestion:
- **title**: the missing topic, specific — "Falta info de horarios de atención".
- **description**: one line — "Se preguntó N veces y la KB no respondió bien."
- **body**: explain the gap, cite the KB it concerns and the conversations where
  it appeared, and propose what to add. Use `[[ref ...]]` macros (by id):

```bash
$FETCH "/projects/$STUDIO_PROJECT_ID/suggestions" --method POST --body '{
  "title": "Falta info de horarios de atención",
  "description": "12 búsquedas esta semana sin respuesta en la KB.",
  "body": "La base [[ref type=\"kb\" id=\"KB_UUID\" label=\"Contacto\"]] no responde \"horarios de atención\" (12 búsquedas, top score < 0.4). Visto en [[ref type=\"conversation\" id=\"CONV_1\" label=\"convo 1\"]] [[ref type=\"conversation\" id=\"CONV_2\" label=\"convo 2\"]]. Propuesta: agregar un artículo con el horario (lun-vie 9-18, GMT-3) y la política fuera de horario.",
  "category": "kb"
}'
```
For an existing one, `POST /suggestions/<id>/followups` with the new cases instead.

## State / memory between runs

You don't keep a private database — **the Suggestions inbox is the shared
state**. Each run: read the existing `kb` suggestions, and reconcile your new
findings against them (follow-up vs create). Optionally keep a short scratch file
during a single run (the `gaps.json` / `existing.json` above) to reason over;
it's disposable.

## Guardrails for good output

- **Quality over volume.** A few well-cited, real gaps beat dozens of noisy ones.
  Respect the sampling — top frequent + worst-scored only.
- **One gap per suggestion.** Don't bundle unrelated missing topics.
- **Always cite evidence** — the query/frequency/score and 1-3 real conversations.
- **Prefer a follow-up** over a near-duplicate create.
- **Don't propose the fix's implementation** here — that's
  [continuous-improvement](../continuous-improvement/SKILL.md). This skill only
  surfaces *what's missing*.
