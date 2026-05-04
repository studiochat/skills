# Studio Chat API Reference

All endpoints require authentication. The `fetch.py` and `export_conversations.py` scripts handle auth automatically via `$STUDIO_API_TOKEN`.

Replace `{pid}` with `$STUDIO_PROJECT_ID` in paths.

## Contents

- [Conversation Analytics](#conversation-analytics)
- [Account Analytics](#account-analytics)
- [Aggregate Metrics](#aggregate-metrics)
- [List Conversations](#list-conversations)
- [Conversation Summaries](#conversation-summaries)
- [Conversation Detail](#conversation-detail)
- [Conversation Batch](#conversation-batch)
- [Conversation Messages (legacy)](#conversation-messages-legacy)
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
- [Resource Analytics — API Tool Usage](#resource-analytics--api-tool-usage)
- [Resource Analytics — Toolkit Usage](#resource-analytics--toolkit-usage)
- [Resource Analytics — Skill Usage](#resource-analytics--skill-usage)
- [CSAT Analytics](#csat-analytics)
- [Conversion Metrics](#conversion-metrics)
- [Custom Toolkits Reference](#custom-toolkits-reference)
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
| `playbook_id` | string | No | Filter by playbook version UUID (matches any participating playbook) |
| `playbook_base_ids` | string | No | Comma-separated playbook base UUIDs (matches conversations where any version participated) |
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
| `playbook_id` | string | No | Filter by playbook version UUID (matches any participating playbook) |
| `playbook_base_id` | string | No | Filter by playbook base UUID (matches any participating version) |
| `tags` | string | No | Comma-separated tags (AND logic) |
| `inbox_id` | string | No | Filter by inbox UUID |

**Response fields:**

```
total_conversations              int     Total conversations in range
total_scored_conversations       int     Conversations with metrics
coverage_percentage              float   % of conversations scored
sentiment_distribution           object  {negative: int, neutral: int, positive: int}
resources_distribution           object  {irrelevant: int, partial: int, relevant: int}
sentiment_shift_distribution     object  {improved: int, stable: int, degraded: int}
deflection_quality_distribution  object  {resolved: int, partial: int, actioned: int, no_response: int}
handoff_reason_distribution      object  {policy: int, user_request: int, frustration: int, bot_limitation: int}
recontact_risk_distribution      object  {low: int, medium: int, high: int}
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
| `playbook_id` | string | | Filter by playbook version UUID (matches any participating playbook, not just the last active) |
| `playbook_base_id` | string | | Filter by playbook base UUID — matches conversations where any version of this playbook participated |
| `inbox_id` | string | | Filter by inbox UUID |
| `search` | string | | Search by conversation ID |
| `has_handoff` | bool | | `true` = only escalated, `false` = only AI-resolved |
| `has_winback` | bool | | `true` = only with winback, `false` = only without |
| `tags` | string | | Comma-separated tags (AND logic — must have ALL tags) |
| `sentiment` | string | | Comma-separated: `negative`, `neutral`, `positive` (OR logic) |
| `resources` | string | | Comma-separated: `irrelevant`, `partial`, `relevant` (OR logic) |
| `sentiment_shift` | string | | Comma-separated: `improved`, `stable`, `degraded` (OR logic) |
| `deflection_quality` | string | | Comma-separated: `resolved`, `partial`, `actioned`, `no_response` (OR logic) |
| `handoff_reason` | string | | Comma-separated: `policy`, `user_request`, `frustration`, `bot_limitation` (OR logic) |
| `recontact_risk` | string | | Comma-separated: `low`, `medium`, `high` (OR logic) |
| `min_messages` | int | | Minimum message count |
| `max_messages` | int | | Maximum message count |
| `skill_name` | string | | Only conversations that loaded this skill (uses efficient EXISTS subquery) |
| `sort_by` | string | `last_message_at` | `last_message_at`, `first_message_at`, or `message_count` |
| `sort_order` | string | `desc` | `desc` or `asc` |

**Response fields per conversation:**

All metadata is returned inline — no separate enrichment calls needed.

```
conversation_id             string  Unique conversation identifier
inbox_name                  string  Channel name (e.g., "Website Chat")
playbook_name               string  Last active playbook name
playbook_version            int     Last active playbook version number
playbooks_info              array   All playbooks that participated [{id, name, version}]
message_count               int     Total messages in conversation
first_message_at            string  ISO 8601 timestamp of first message
last_message_at             string  ISO 8601 timestamp of last message
first_user_message          string  Text of the customer's first message
last_assistant_message      string  Text of the AI's last response
has_handoff                 bool    Whether conversation was escalated to human
has_error                   bool    Whether conversation had an error (timeout, agent_error)
tags                        array   List of tag strings (merged from internal + external tags)
skills                      array   Skill names loaded during the conversation (null if none)
avg_response_latency_ms     int     Average AI response time for this conversation
sentiment_label             string  "negative", "neutral", or "positive" (null if unscored)
sentiment_reason            string  Explanation of sentiment scoring (null if unscored)
resources_label             string  "irrelevant", "partial", or "relevant" (null if unscored)
resources_reason            string  Explanation of resource relevance scoring (null if unscored)
summary                     string  AI-generated conversation summary (null if unscored)
user_intent                 string  Short phrase describing what the user wanted (null if unscored)
sentiment_shift             string  "improved", "stable", or "degraded" (null if unscored)
sentiment_shift_reason      string  Explanation of sentiment shift (null if unscored)
deflection_quality          string  "resolved", "partial", "actioned", or "no_response" (null if handoff or unscored)
deflection_quality_reason   string  Explanation of deflection quality (null if handoff or unscored)
handoff_reason              string  "policy", "user_request", "frustration", or "bot_limitation" (null if no handoff or unscored)
handoff_reason_detail       string  Explanation of handoff reason (null if no handoff or unscored)
recontact_risk              string  "low", "medium", or "high" (null if unscored)
recontact_risk_reason       string  Explanation of recontact risk (null if unscored)
model                       string  LLM model used (e.g., "gpt-4o-mini")
winback_sent_at             string  ISO 8601 timestamp when winback was sent (null if not sent)
context                     object  Context dict passed to the agent (contact info, etc.)
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
skills                      array   Skill names loaded during the conversation (null if none)
user_intent                 string  Short phrase: what the user wanted (null if unscored)
sentiment_shift             string  "improved", "stable", or "degraded" (null if unscored)
deflection_quality          string  "resolved", "partial", "actioned", or "no_response" (null if handoff or unscored)
handoff_reason              string  "policy", "user_request", "frustration", or "bot_limitation" (null if no handoff or unscored)
recontact_risk              string  "low", "medium", or "high" (null if unscored)
```

**Pagination:** Response includes `total`, `limit`, `offset`.

---

## Conversation Detail

`GET /projects/{pid}/conversations/{conversation_id}`

Full detail for a single conversation: all metadata + complete message history with
tool calls + KB citations. One API call, everything included.

**Note:** `conversation_id` is the **external platform ID** (e.g., the Chatwoot or Intercom
conversation ID visible in the platform UI), not an internal database key.

**Response fields:**

All fields from the conversation list endpoint (see above), plus:

```
messages                    array   Complete message history
  role                      string  "user" or "assistant"
  content                   string  Message text content
  created_at                string  ISO 8601 timestamp
  metadata                  object  Includes: playbook_id, playbook_name, playbook_version (which playbook generated this message), response_latency_ms, labels, priority, notes, handoff, explanation
  tool_calls                array   Tool calls in this message
    id                      string  Tool call ID
    name                    string  Tool name (e.g., "search_knowledge_base")
    arguments               string  JSON arguments string
    result                  string  Tool result (null if unavailable)
    tool_type               string  "kb_search", "list_agents", "list_teams", "list_kbs", or "custom"
    enhanced_params         object  Parsed parameters for display
  is_winback                bool    Whether this is a winback follow-up message
  attachments               array   Attachments (images, documents)
citations                   array   KB sources referenced across the conversation
  citation_id               string  Unique citation ID
  kb_id                     string  Knowledge base ID
  item_id                   string  KB item ID (null if unavailable)
  content                   string  Citation content excerpt
  file_name                 string  Source file name (null if N/A)
```

---

## Conversation Batch

`POST /projects/{pid}/conversations/batch`

Full detail for multiple conversations in a single request. Metadata is fetched in one query;
messages are fetched per conversation.

**Note:** `conversation_ids` are **external platform IDs** (same as the detail endpoint above).

**Request body:**

```json
{
  "conversation_ids": ["conv-1", "conv-2", "conv-3"]
}
```

Maximum 50 conversation IDs per request. Non-existent IDs are silently skipped.

**Response:**

```
conversations               array   List of ConversationDetail objects (same structure as above)
```

---

## Conversation Messages (legacy)

`GET /projects/{pid}/conversations/{conversation_id}/messages`

Message history + citations for a single conversation. Does NOT include conversation metadata
or per-message token usage. **Prefer the detail endpoint above** for new integrations.

**Response fields:**

```
messages                    array   Ordered list of messages
  role                      string  "user" or "assistant"
  content                   string  Message text content
  created_at                string  ISO 8601 timestamp
citations                   array   KB sources referenced
  citation_id               string  Citation ID
  kb_id                     string  Knowledge base ID
  content                   string  Citation content
```

---

## Conversation Metrics

`GET /projects/{pid}/conversations/{conversation_id}/metrics`

Quality metrics for a single conversation. Returns `null` fields if not yet scored.

**Response fields:**

```
sentiment_label             string  "negative", "neutral", or "positive"
sentiment_reason            string  LLM explanation of sentiment score
resources_label             string  "irrelevant", "partial", or "relevant" (null if no tools used)
resources_reason            string  LLM explanation of resource quality
summary                     string  2-3 sentence conversation summary including tools/KBs used
user_intent                 string  Short phrase describing what the user wanted
sentiment_shift             string  "improved", "stable", or "degraded"
sentiment_shift_reason      string  LLM explanation of sentiment shift
deflection_quality          string  "resolved", "partial", "actioned", or "no_response" (null if handoff)
deflection_quality_reason   string  LLM explanation of deflection quality
handoff_reason              string  "policy", "user_request", "frustration", or "bot_limitation" (null if no handoff)
handoff_reason_detail       string  LLM explanation of handoff reason
recontact_risk              string  "low", "medium", or "high"
recontact_risk_reason       string  LLM explanation of recontact risk
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

## Resource Analytics — API Tool Usage

### API Tool Analytics

`GET /projects/{pid}/analytics/api-tools`

Aggregated usage metrics for custom API tool executions.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `api_tool_id` | string | | Filter by specific API tool UUID |
| `start_date` | string | | Start date (`YYYY-MM-DD`) |
| `end_date` | string | | End date (`YYYY-MM-DD`) |
| `limit` | int | 50 | Max recent items (1-500) |
| `offset` | int | 0 | Pagination offset for recent items |
| `search` | string | | Search in input_params, output_result, conversation_id, error_message |

**Response fields:**

```
total_calls             int     Total executions
successful_calls        int     Successful executions
failed_calls            int     Failed executions
avg_duration_ms         float   Average execution time (ms), null if no data
tool_config             object  {method, url} — only present when api_tool_id is set
time_series             array   Daily buckets
  date                  string  YYYY-MM-DD
  count                 int     Total calls that day
  success_count         int     Successful calls that day
  avg_duration_ms       float   Avg duration that day (null if none)
recent                  array   Recent executions (paginated)
  id                    string  Log entry UUID
  tool_name             string  API tool name
  input_params          object  Request parameters sent
  output_result         object  Response received
  request_meta          object  HTTP metadata (status, headers)
  success               bool    Whether execution succeeded
  error_message         string  Error details (null if success)
  duration_ms           int     Execution time (ms)
  created_at            string  ISO 8601 timestamp
  conversation_id       string  Conversation that triggered it (null if manual)
```

### API Tool Sparklines

`GET /projects/{pid}/analytics/api-tools/sparklines`

Lightweight batch endpoint returning per-tool daily counts for sparkline charts.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | int | 14 | Trailing days (1-90) |

**Response:** `dict[tool_id → SparklineItem]`

```
{tool_id}               object
  total                 int     Total calls in period
  series                array   Daily data points
    date                string  YYYY-MM-DD
    count               int     Calls that day
```

---

## Resource Analytics — Toolkit Usage

### Toolkit Analytics

`GET /projects/{pid}/analytics/toolkits`

Aggregated usage metrics for integration toolkit action executions.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `toolkit_slug` | string | | Filter by toolkit slug |
| `action_name` | string | | Filter by specific action |
| `start_date` | string | | Start date (`YYYY-MM-DD`) |
| `end_date` | string | | End date (`YYYY-MM-DD`) |
| `limit` | int | 50 | Max recent items (1-500) |
| `offset` | int | 0 | Pagination offset for recent items |
| `search` | string | | Search in input_params, output_result, conversation_id, action_name, error_message |
| `param_filter` | string | | Filter by input_params JSON `key:value` (e.g., `ticket_type_id:67`) |

**Response fields:**

```
total_calls             int     Total executions
successful_calls        int     Successful executions
failed_calls            int     Failed executions
avg_duration_ms         float   Average execution time (ms), null if no data
by_action               array   Breakdown by action name
  action_name           string  Action slug
  count                 int     Total calls
  success_count         int     Successful calls
by_param                array   Breakdown by input param value (only when param_filter key is set)
  value                 string  Parameter value
  count                 int     Occurrences
time_series             array   Daily buckets
  date                  string  YYYY-MM-DD
  count                 int     Total calls that day
  success_count         int     Successful calls that day
recent                  array   Recent executions (paginated)
  id                    string  Log entry UUID
  toolkit_slug          string  Toolkit identifier
  action_name           string  Action that was executed
  input_params          object  Parameters sent to the action
  output_result         object  Response from the action
  success               bool    Whether execution succeeded
  error_message         string  Error details (null if success)
  duration_ms           int     Execution time (ms)
  created_at            string  ISO 8601 timestamp
  conversation_id       string  Conversation that triggered it (null if manual)
```

### Toolkit Sparklines

`GET /projects/{pid}/analytics/toolkit-calls/sparklines`

Lightweight batch endpoint returning per-toolkit daily counts for sparkline charts.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | int | 14 | Trailing days (1-90) |

**Response:** `dict[toolkit_slug → SparklineItem]`

```
{toolkit_slug}          object
  total                 int     Total calls in period
  series                array   Daily data points
    date                string  YYYY-MM-DD
    count               int     Calls that day
```

---

## Resource Analytics — Skill Usage

`GET /projects/{pid}/analytics/skills`

Skill load events: totals, success/failure, time series, and recent items.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `skill_name` | string | | Filter by specific skill name |
| `start_date` | string | | YYYY-MM-DD format |
| `end_date` | string | | YYYY-MM-DD format |
| `search` | string | | Search in skill_name, conversation_id, error_message |
| `limit` | int | 50 | Max recent items (1-500) |
| `offset` | int | 0 | Skip N recent items |

**Response fields:**

```
total_calls                 int     Total skill loads
successful_calls            int     Successful loads
failed_calls                int     Failed loads
time_series                 array   Daily buckets
  date                      string  YYYY-MM-DD
  count                     int     Loads that day
  success_count             int     Successful loads that day
recent                      array   Most recent skill loads
  id                        string  Log entry ID
  skill_name                string  Name of the skill
  success                   bool    Whether the load succeeded
  error_message             string  Error message if failed (null otherwise)
  created_at                string  ISO 8601 timestamp
  conversation_id           string  Conversation that triggered the load (null if N/A)
```

---

### Skill Sparklines

`GET /projects/{pid}/analytics/skills/sparklines`

Lightweight per-skill daily counts for sparkline charts.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | int | 14 | Trailing window (1-90 days) |

**Response:** Dictionary keyed by skill name.

```
{skill_name}:
  total                     int     Total loads in window
  series                    array   Daily data points
    date                    string  YYYY-MM-DD
    count                   int     Loads that day
```

---

## CSAT Analytics

`GET /projects/{pid}/csat/analytics`

Aggregate CSAT for a project: KPIs, 1–5 distribution, time series, and a paginated
ratings table. Sourced from the Intercom CSAT enrichment — projects without an
enrichment config respond with `is_configured=false` and zeroed fields.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `start_date` | string | now − 7d | ISO 8601 datetime (UTC if no offset) |
| `end_date` | string | now | ISO 8601 datetime |
| `tags` | string | — | Comma-separated tags (AND logic) |
| `tag_filter` | string | — | JSON-encoded TagExpr (AND/OR/NOT). Takes precedence over `tags` when set |
| `playbook_base_id` | string | — | Filter to one assistant (all versions) |
| `ratings_limit` | int | 10 | Page size for the ratings table (1–200) |
| `ratings_offset` | int | 0 | Pagination offset into `total_rated` |
| `max_rating` | int | — | Drill-down: only return ratings ≤ this value (1–5) in the table. KPIs, distribution, and time series stay on the unfiltered dataset |

**Response fields:**

```
is_configured           bool    False when no Intercom CSAT config exists for the project
total_rated             int     Conversations with a rating in the window
csat_score_pct          float   % of rated convos with rating in {4, 5}
dsat_score_pct          float   % of rated convos with rating in {1, 2}
eligible_deflected      int     Deflected conversations in window (denominator for response_rate_pct)
response_rate_pct       float   % of eligible convos that were rated
rating_distribution     dict    Map of "1"…"5" → count
positive_count          int     Convos with rating in {4, 5}
neutral_count           int     Convos with rating == 3
negative_count          int     Convos with rating in {1, 2}
time_series             array   Per-bucket CSAT — see below
time_granularity        string  "day" or "hour"
ratings                 array   Paginated rows for the ratings table
ratings_offset          int     Echo of the offset the page starts at
```

Each `time_series` entry:

```
date                  string  Bucket label (ISO date or ISO hour)
total                 int     Ratings received in the bucket
positive              int     Ratings in {4, 5}
neutral               int     Ratings == 3
negative              int     Ratings in {1, 2}
csat_pct              float?  % positive of total (null when total=0)
eligible              int     Eligible deflected convos in the bucket
response_rate_pct     float?  % of eligible that were rated (null when eligible=0)
```

Each `ratings` row:

```
conversation_id       string  External platform conversation id (links to the detail view)
rating                int     1..5
remark                string? Verbatim left by the rater (often null)
rated_at              datetime?
tags                  array   Conversation tags
first_message_at      datetime?
```

**Errors:** `400` on invalid `start_date`/`end_date` ordering or malformed
`tag_filter`. `404` when the project does not exist for the caller's account.

---

## Conversion Metrics

Per-project, user-defined enrichments that track external conversion events
(e.g. sales) tied to a conversation. Definitions are managed from the FE; events
are pushed in by an external service. The data-expert skill is **read-only** —
the create/update/delete and ingest endpoints are not exposed here.

### List Conversion Metrics

`GET /projects/{pid}/conversion-metrics`

Returns all definitions for a project, ordered by `created_at` ascending.

Each item:

```
id                    string   UUID
project_id            string
slug                  string   Per-project unique, lowercase + hyphens
name                  string   Human label (e.g. "Venta")
description           string?
value_label           string   Unit rendered alongside `value` (e.g. "USD", "ARS")
enabled               bool     False = ingest rejected with 409
created_at            datetime
updated_at            datetime
ingest_url_path       string   Relative POST path the upstream cron uses
last_event_at         datetime? MAX(events.created_at) — integration heartbeat
```

### Get Conversion Metric

`GET /projects/{pid}/conversion-metrics/{slug}`

Same shape as one item from the list endpoint. Responds `404` when the slug
doesn't exist for the project.

### Conversion Metric Analytics

`GET /projects/{pid}/conversion-metrics/{slug}/analytics`

Dashboard payload for one metric. Mirrors the structure of `csat/analytics` —
KPIs + time series + paginated events table.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `start_date` | string | now − 7d | ISO 8601 datetime |
| `end_date` | string | now | ISO 8601 datetime |
| `tags` | string | — | Comma-separated tags (AND logic) |
| `tag_filter` | string | — | JSON-encoded TagExpr (AND/OR/NOT). Takes precedence over `tags` |
| `playbook_base_id` | string | — | Filter to one assistant (all versions) |
| `events_limit` | int | 25 | Page size for the events table (1–200) |
| `events_offset` | int | 0 | Pagination offset into `total_events_filtered` |

**Response fields:**

```
is_configured                 bool    False when no metric with that slug exists for the project
definition                    object  Echo of the metric definition (see list response)
total_events                  int     Events in window matching filters
total_value                   float   Sum of event.value (use definition.value_label for the unit)
avg_value                     float   total_value / total_events (0 when total_events=0)
converting_conversations      int     Distinct conversations with ≥1 event in window
eligible_conversations        int     Deflected conversations in window — denominator for conversion_rate_pct
conversion_rate_pct           float   converting_conversations / eligible_conversations × 100
avg_value_per_conversation    float   total_value / converting_conversations
time_granularity              string  "day" or "hour"
time_series                   array   Per-bucket trend — see below
events                        array   Paginated rows for the events table
events_offset                 int     Echo of the offset the page starts at
total_events_filtered         int     Total rows matching the filters (denominator for paging)
```

Each `time_series` entry:

```
date                       string  Bucket label
event_count                int     Events in the bucket
total_value                float   Sum of values in the bucket
converting_conversations   int     Distinct conversations with ≥1 event in the bucket
```

Each `events` row:

```
id                  int      Internal event id
conversation_id     string   External platform conversation id (always set — ingest rejects unmatched)
match_value         string   Original platform id used at ingest
idempotency_key     string   Caller-supplied stable key for the underlying event
value               float    Numeric value
occurred_at         datetime When the event happened (UTC)
metadata            dict?    Free-form JSON the cron attached at ingest
tags                array    Conversation tags
```

**Errors:** `400` on invalid date ordering or malformed `tag_filter`. When the
slug doesn't exist the response is `200` with `is_configured=false` (so the FE
can render its empty state) — check that flag before reading any other field.

---

## Custom Toolkits Reference

Custom toolkits are project-scoped integrations with third-party APIs. Each toolkit has a unique slug used in analytics endpoints (`toolkit_slug` parameter) and usage logs.

### Registered Toolkits

| Toolkit | Slug | Auth Type | Description |
|---------|------|-----------|-------------|
| Slack | `SLACK` | api_key (bot token) | Send messages to Slack channels |
| Intercom Tickets | `INTERCOM_TICKETS` | api_key | Create Intercom support tickets |

### Slack — Tools

| Tool Slug | Description |
|-----------|-------------|
| `SLACK_SEND_MESSAGE` | Send a message to a Slack channel |

**Parameters for `SLACK_SEND_MESSAGE`:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `channel` | string | Yes | Slack channel ID (pre-configured from channel list) |
| `message` | string | Yes | Message text to send |

### Intercom Tickets — Tools

| Tool Slug | Description |
|-----------|-------------|
| `INTERCOM_TICKETS_CREATE_TICKET` | Create a new Intercom support ticket |

**Parameters for `INTERCOM_TICKETS_CREATE_TICKET`:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `ticket_type_id` | string | Yes | Intercom ticket type ID (pre-configured from type list) |
| `contact_email` | string | Yes | Email of the contact to associate the ticket with |
| `title` | string | Yes | Ticket title |
| `description` | string | No | Ticket body/description |
| *(dynamic)* | varies | varies | Custom attributes defined per ticket type in Intercom |

### Using Toolkit Slugs in Analytics

When querying resource analytics, use the toolkit slug and tool slug as filters:

```bash
# All Slack usage
fetch.py "/projects/$STUDIO_PROJECT_ID/analytics/toolkits" --params toolkit_slug=SLACK

# Specific Slack action
fetch.py "/projects/$STUDIO_PROJECT_ID/analytics/toolkits" \
  --params toolkit_slug=SLACK action_name=SLACK_SEND_MESSAGE

# All Intercom ticket creations
fetch.py "/projects/$STUDIO_PROJECT_ID/analytics/toolkits" \
  --params toolkit_slug=INTERCOM_TICKETS action_name=INTERCOM_TICKETS_CREATE_TICKET

# Intercom tickets filtered by ticket type
fetch.py "/projects/$STUDIO_PROJECT_ID/analytics/toolkits" \
  --params toolkit_slug=INTERCOM_TICKETS param_filter=ticket_type_id:67
```

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
