# Studio Chat API Reference

All endpoints require authentication. The `fetch.py` and `export_conversations.py` scripts handle auth automatically via `$STUDIO_API_TOKEN`.

Replace `{pid}` with `$STUDIO_PROJECT_ID` in paths.

## Contents

- [Conversation Analytics](#conversation-analytics)
- [Account Analytics](#account-analytics)
- [Aggregate Metrics](#aggregate-metrics)
- [List Conversations](#list-conversations)
- [Conversation Summaries](#conversation-summaries)
- [Conversation Messages](#conversation-messages)
- [Conversation Metrics](#conversation-metrics)
- [Trigger Metrics Scoring](#trigger-metrics-scoring)
- [Trending Topics](#trending-topics)
- [Playbooks](#playbooks)
- [Playbook Active Version](#playbook-active-version)
- [Playbook Settings](#playbook-settings)
- [Knowledge Bases](#knowledge-bases)
- [Knowledge Base Items](#knowledge-base-items)
- [Eval Cases](#eval-cases)
- [Eval Runs](#eval-runs)
- [Projects](#projects)
- [Project Settings](#project-settings)
- [Schedule](#schedule)
- [API Tools](#api-tools)
- [Analyst Conversations](#analyst-conversations)

---

## Conversation Analytics

`GET /projects/{pid}/conversations/analytics`

Aggregated conversation metrics with time series and breakdowns by playbook/tag.

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `start_date` | string | Yes | ISO 8601 datetime (e.g., `2025-01-01T00:00:00Z`) |
| `end_date` | string | Yes | ISO 8601 datetime |
| `playbook_id` | string | No | Filter by specific playbook version UUID |
| `playbook_base_ids` | string | No | Comma-separated playbook base UUIDs (all versions) |
| `tags` | string | No | Comma-separated tags (AND logic — must match ALL) |

**Response fields:**

```
total_conversations         int     Total conversations in range
total_messages              int     Total messages across all conversations
conversations_with_handoff  int     Conversations escalated to human
conversations_without_handoff int   Conversations resolved by AI
deflection_rate             float   % resolved without handoff
avg_messages_per_conversation float Average messages per conversation
avg_response_latency_ms     int     Average AI response time (ms)
winback_sent_count          int     Winback messages sent
winback_answered_count      int     Winbacks that got a reply
winback_conversion_rate     float   % of winbacks answered
by_playbook                 array   Breakdown per playbook (name, deflection_rate, totals)
by_tag                      array   Breakdown per tag (tag, deflection_rate, totals)
time_series                 array   Daily/hourly buckets with totals + latency stats
time_granularity            string  "day" or "hour"
```

Each `time_series` entry includes:
- `timestamp`, `total_conversations`, `conversations_with_handoff`
- `avg_response_latency_ms`, `min_response_latency_ms`, `max_response_latency_ms`, `p99_response_latency_ms`

---

## Account Analytics

`GET /account/conversations/analytics`

Account-wide metrics across ALL projects/assistants.

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `start_date` | string | Yes | ISO 8601 datetime |
| `end_date` | string | Yes | ISO 8601 datetime |

**Response fields:**

```
total_conversations         int     Account-wide total
total_messages              int     Total messages
total_ai_messages           int     Messages sent by AI (used for time-saved calc)
conversations_with_handoff  int     Escalated conversations
conversations_without_handoff int   AI-resolved conversations
deflection_rate             float   % resolved without handoff
avg_messages_per_conversation float Average per conversation
by_assistant                array   Per-assistant breakdown (name, totals, deflection_rate)
time_series                 array   Daily buckets with totals
```

**Time saved formula:** `total_ai_messages × 5 minutes`

---

## Aggregate Metrics

`GET /projects/{pid}/conversations/metrics/aggregate`

Sentiment and resource-quality distributions across scored conversations.

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `start_date` | string | Yes | ISO 8601 datetime |
| `end_date` | string | Yes | ISO 8601 datetime |
| `playbook_id` | string | No | Filter by playbook version UUID |
| `playbook_base_id` | string | No | Filter by playbook base UUID |
| `tags` | string | No | Comma-separated tags (AND logic) |
| `inbox_id` | string | No | Filter by inbox UUID |

**Response fields:**

```
total_conversations         int     Total conversations in range
total_scored_conversations  int     Conversations with metrics
coverage_percentage         float   % of conversations scored
sentiment_distribution      object  {negative: int, neutral: int, positive: int}
resources_distribution      object  {irrelevant: int, partial: int, relevant: int}
```

---

## List Conversations

`GET /projects/{pid}/conversations`

Paginated list of customer conversations with comprehensive filtering.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | 1-100 conversations per page |
| `offset` | int | 0 | Skip N conversations |
| `start_date` | string | | ISO 8601 start datetime |
| `end_date` | string | | ISO 8601 end datetime |
| `playbook_id` | string | | Filter by playbook version UUID |
| `playbook_base_id` | string | | Filter by playbook base UUID (all versions) |
| `inbox_id` | string | | Filter by inbox UUID |
| `search` | string | | Search by conversation ID |
| `has_handoff` | bool | | `true` = only escalated, `false` = only AI-resolved |
| `has_winback` | bool | | `true` = only with winback, `false` = only without |
| `tags` | string | | Comma-separated tags (AND logic — must have ALL tags) |
| `sentiment` | string | | Comma-separated: `negative`, `neutral`, `positive` (OR logic) |
| `resources` | string | | Comma-separated: `irrelevant`, `partial`, `relevant` (OR logic) |
| `min_messages` | int | | Minimum message count |
| `max_messages` | int | | Maximum message count |
| `sort_by` | string | `last_message_at` | `last_message_at`, `first_message_at`, or `message_count` |
| `sort_order` | string | `desc` | `desc` or `asc` |

**Response fields per conversation:**

```
conversation_id             string  Unique conversation identifier
inbox_name                  string  Channel name (e.g., "Website Chat")
playbook_name               string  Playbook that handled this conversation
playbook_version            int     Version number of the playbook
message_count               int     Total messages in conversation
first_message_at            string  ISO 8601 timestamp of first message
last_message_at             string  ISO 8601 timestamp of last message
first_user_message          string  Text of the customer's first message
last_assistant_message      string  Text of the AI's last response
has_handoff                 bool    Whether conversation was escalated to human
has_winback                 bool    Whether a winback message was sent
tags                        array   List of tag strings
avg_response_latency_ms     int     Average AI response time for this conversation
sentiment_label             string  "negative", "neutral", or "positive" (null if unscored)
resources_label             string  "irrelevant", "partial", or "relevant" (null if unscored)
summary                     string  AI-generated conversation summary (null if unscored)
model                       string  LLM model used (e.g., "gpt-4o-mini")
```

**Pagination:** Response includes `total`, `limit`, `offset`. Use `offset += limit` to page.

---

## Conversation Summaries

`GET /projects/{pid}/conversations/summaries`

Lightweight list of conversation summaries for batch scanning. Returns slim objects without full conversation data.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | 1-100 summaries per page |
| `offset` | int | 0 | Skip N entries |
| `start_date` | string | | ISO 8601 start datetime |
| `end_date` | string | | ISO 8601 end datetime |
| `sentiment` | string | | Comma-separated: `negative`, `neutral`, `positive` |
| `resources` | string | | Comma-separated: `irrelevant`, `partial`, `relevant` |
| `tags` | string | | Comma-separated tags (AND logic) |
| `playbook_base_id` | string | | Filter by playbook base UUID |
| `has_handoff` | bool | | Filter by handoff status |
| `sort_by` | string | `last_message_at` | `last_message_at`, `first_message_at`, or `message_count` |
| `sort_order` | string | `desc` | `desc` or `asc` |

**Response fields per summary:**

```
conversation_id             string  Unique conversation identifier
summary                     string  AI-generated summary (null if unscored)
sentiment_label             string  "negative", "neutral", or "positive" (null if unscored)
resources_label             string  "irrelevant", "partial", or "relevant" (null if unscored)
first_user_message          string  Customer's first message
tags                        array   List of tag strings
has_handoff                 bool    Whether escalated to human
message_count               int     Total messages
last_message_at             string  ISO 8601 timestamp of last message
```

**Pagination:** Response includes `total`, `limit`, `offset`.

---

## Conversation Messages

`GET /projects/{pid}/conversations/{conversation_id}/messages`

Full message history for a single conversation.

**Response fields:**

```
messages                    array   Ordered list of messages
  role                      string  "user" or "assistant"
  content                   string  Message text content
  created_at                string  ISO 8601 timestamp
citations                   array   KB sources referenced
  id                        string  Citation ID
  source                    string  KB name
  title                     string  Source document title
```

---

## Conversation Metrics

`GET /projects/{pid}/conversations/{conversation_id}/metrics`

Quality metrics for a single conversation. Returns `null` fields if not yet scored.

**Response fields:**

```
sentiment_label             string  "negative", "neutral", or "positive"
sentiment_reason            string  LLM explanation of sentiment score
resources_label             string  "irrelevant", "partial", or "relevant"
resources_reason            string  LLM explanation of resource quality
summary                     string  One-paragraph conversation summary
scored_at                   string  ISO 8601 when scoring happened
message_count_at_scoring    int     Messages present when scored
```

---

## Trigger Metrics Scoring

`POST /projects/{pid}/conversations/{conversation_id}/metrics/analyze`

Manually trigger quality scoring for a conversation. Requires >= 2 messages. Empty request body.

Returns the same metrics object as the GET endpoint.

---

## Trending Topics

### Check Status

`GET /projects/{pid}/conversations/insights/trending-topics/status`

| Param | Type | Description |
|-------|------|-------------|
| `playbook_base_ids` | string | Comma-separated playbook base UUIDs |
| `tags` | string | Comma-separated tags |

Returns `status` ("completed", "pending", "none") and the `analysis` object if available.

### Start Analysis Job

`POST /projects/{pid}/conversations/insights/trending-topics/generate`

**Request body (optional):**
```json
{"playbook_base_ids": ["uuid1"], "tags": ["billing"]}
```

Returns `job_id` and `status: "pending"`. Returns `409` if analysis exists for today.

### Poll Job Progress

`GET /projects/{pid}/conversations/insights/trending-topics/job/{job_id}`

```
id                string    Job UUID
status            string    "pending", "running", "completed", "failed"
progress          int       0-100 percentage
step              string    Current step name
progress_message  string    Human-readable progress
analysis_id       string    Set when completed
started_at        string    ISO 8601
completed_at      string    ISO 8601 (null while running)
```

### Get Analysis Results

`GET /projects/{pid}/conversations/insights/trending-topics/analysis/{analysis_id}`

**Analysis fields:**

```
id                          string  Analysis UUID
analysis_date               string  Date of analysis
total_conversations         int     Total conversations analyzed
conversations_analyzed      int     Conversations in scope
start_date                  string  Analysis window start
end_date                    string  Analysis window end
topics                      array   Identified topic clusters
  name                      string  Topic name
  description               string  Topic description
  insight                   string  Actionable insight
  conversation_count        int     Conversations in this topic
  percentage                float   % of total
  sentiment                 string  Overall sentiment
  sentiment_breakdown       object  {positive: int, neutral: int, negative: int}
  handoff_count             int     Escalations for this topic
  handoff_rate              float   % escalated
  conversation_ids          array   All conversation IDs
  example_conversations     array   Sample conversations with summaries
```

---

## Playbooks

### List Playbooks

`GET /projects/{pid}/playbooks`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `include_deleted` | bool | false | Include soft-deleted playbooks |
| `include_versions` | bool | false | Include all versions of each playbook |

**Response:** Array of playbook objects:

```
id                  string  Playbook version UUID
base_id             string  Playbook base UUID (stable across versions)
name                string  Playbook name
version_number      int     Version number
content             string  Full playbook instructions
kb_ids              array   Linked knowledge base UUIDs
model               string  LLM model (e.g., "gpt-4o-mini")
is_deleted          bool    Whether soft-deleted
inboxes             array   Deployed inboxes [{id, name}]
```

### Get Playbook

`GET /playbooks/{playbook_id}`

Returns full playbook details including `content` (instructions), `kb_ids`, `model`, `version_number`.

### Get Playbook History

`GET /playbooks/{playbook_id}/history`

Returns version history array:

```
id                  string    Version UUID
version_number      int       Version number
name                string    Playbook name at that version
created_at          string    ISO 8601
updated_at          string    ISO 8601
```

### Get Playbook Version

`GET /playbooks/{playbook_id}/versions/{version_number}`

Returns the full playbook content for a specific historical version.

---

## Playbook Active Version

### Get Active Version

`GET /playbooks/{base_id}/active`

**Note:** Uses `base_id`, not `playbook_id`.

```
base_id             string    Playbook base UUID
version_number      int       Currently active version number
playbook            object    Full playbook object for active version
```

### Get Active Version History

`GET /playbooks/{base_id}/active/history`

**Note:** Uses `base_id`, not `playbook_id`.

Returns deployment timeline:

```
items               array     Ordered by most recent first
  version_number    int       Version that was activated
  activated_at      string    ISO 8601 when it became active
  activated_by      string    User who activated it (null for system)
```

---

## Playbook Settings

`GET /playbooks/{playbook_id}/settings`

Returns settings (or null if not configured):

```
is_disabled         bool      Kill switch (true = playbook turned off)
url_shortener       object    URL shortening configuration
winback             object    Winback messaging settings
```

---

## Knowledge Bases

### List Knowledge Bases

`GET /projects/{pid}/knowledgebases`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `include_final_delete` | bool | false | Include permanently deleted KBs |
| `include_playbook_usage` | bool | false | Include which playbooks use each KB |

**Response per KB:**

```
id                  string    KB UUID
title               string    KB name
kb_type             string    TEXT, FAQ, SNIPPETS, FILE, NOTION, GDRIVE, INTERCOM
status              string    ACTIVE, ADDED, EDITED, DELETED
content             string    (for TEXT/FILE types)
faq_items           array     (for FAQ type) [{questions: [...], answer: "..."}]
snippet_items       array     (for SNIPPETS type) catalog items
used_by_playbooks   array     (if include_playbook_usage=true) [{id, name}]
```

**KB status meanings:**
- `ACTIVE` — Trained and live in the assistant
- `ADDED` — New, pending training
- `EDITED` — Modified, needs retraining
- `DELETED` — Soft-deleted

### Get Knowledge Base

`GET /knowledgebases/{kb_id}`

Returns full KB content. Content fields depend on type.

---

## Knowledge Base Items

`GET /knowledgebases/{kb_id}/items/{item_id}`

Get metadata for a specific item within a KB.

```
item_id             string    Item UUID
item_type           string    snippet, faq, notion, intercom, gdrive
title               string    Item title
url                 string    Source URL (null for non-linked items)
```

---

## Eval Cases

### List Eval Cases

`GET /playbooks/{base_id}/eval-cases`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled_only` | bool | false | Return only enabled test cases |

**Note:** Uses playbook `base_id`.

**Response:** Array of eval cases:

```
id                  string    Case UUID
input               string    Test input message
expected_output     string    Expected response pattern
tags                array     Classification tags
enabled             bool      Whether case is active
```

### Get Eval Case

`GET /eval-cases/{case_id}`

Returns a single eval case with full details.

### Export Eval Cases (YAML)

`GET /playbooks/{base_id}/eval-cases/export-yaml`

Returns `yaml_content` string with all cases in YAML format for version control.

---

## Eval Runs

### List Eval Runs

`GET /playbooks/{base_id}/eval-runs`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number (1-indexed) |
| `page_size` | int | 10 | Results per page (1-100) |

**Note:** Uses playbook `base_id`.

**Response:**

```
items               array     Eval run objects
total               int       Total runs
page                int       Current page
page_size           int       Items per page
total_pages         int       Total pages
```

### Get Eval Run

`GET /eval-runs/{run_id}`

Returns full eval run with individual case results, scores, and pass/fail status.

---

## Projects

### List Projects

`GET /projects`

Returns all projects for the account with retraining status.

```
id                  string    Project UUID
name                string    Project name
account_id          string    Owner account UUID
needs_retraining    bool      Whether KBs need retraining
```

### Get Project

`GET /projects/{pid}`

Returns a single project with retraining status.

---

## Project Settings

`GET /projects/{pid}/settings`

```
project_id          string    Project UUID
settings            object
  personality_tone  string    "professional" (default), or custom tone
  user_enrichment_url string  URL for customer data enrichment (null if not set)
```

---

## Schedule

`GET /projects/{pid}/schedule`

```
id                  string    Schedule UUID
enabled             bool      Whether office hours are active
timezone            string    IANA timezone (e.g., "America/New_York")
weekly_schedule     object    Per-day schedules
  monday..sunday    object    {enabled: bool, slots: [{start: "09:00", end: "17:00"}]}
overrides           array     Date overrides
  id                string    Override UUID
  date              string    Date (YYYY-MM-DD)
  is_available      bool      false = closed for the day
  label             string    Description (e.g., "Christmas")
```

---

## API Tools

### List API Tools

`GET /projects/{pid}/api-tools`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `include_playbook_usage` | bool | false | Include which playbooks use each tool |

Returns custom HTTP integrations configured for the project.

### Get API Tool

`GET /projects/{pid}/api-tools/{tool_id}`

Returns full tool configuration: URL, method, headers, parameters.

---

## Analyst Conversations

Internal Analyst conversations (separate from customer conversations).

### List Analyst Conversations

`GET /analyst/conversations`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max conversations to return |
| `offset` | int | 0 | Pagination offset |

Returns `conversations` array and `total` count.

### Get Analyst Messages

`GET /analyst/conversations/{conversation_id}/messages`

Returns parsed messages with tool calls and explanations.
