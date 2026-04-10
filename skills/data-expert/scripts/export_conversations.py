#!/usr/bin/env python3
"""Batch export conversations with all metadata.

Paginates through all conversations matching the given filters.
All metadata (summary, sentiment, resources, skills, tags, etc.) is
included by default in every conversation — no enrichment needed.

Optionally fetches full message history with --messages (one API call
per conversation).

Usage:
    export_conversations.py [options] -o output.json
    export_conversations.py [options] --format csv -o output.csv

Examples:
    # Export all conversations from January 2025
    export_conversations.py --start 2025-01-01 --end 2025-02-01 -o jan.json

    # Export handoff conversations
    export_conversations.py --start 2025-01-01 --end 2025-02-01 \
        --handoff true -o handoffs.json

    # Export handoff conversations with full message history
    export_conversations.py --start 2025-01-01 --end 2025-02-01 \
        --handoff true --messages -o handoffs_full.json

    # Export only negative sentiment as CSV
    export_conversations.py --start 2025-01-01 --end 2025-02-01 \
        --sentiment negative --format csv -o negative.csv

    # Filter by playbook and tags
    export_conversations.py --start 2025-01-01 --end 2025-02-01 \
        --playbook-base-id abc-123 --tags billing,refund -o billing.json

    # Short conversations sorted by message count
    export_conversations.py --start 2025-01-01 --end 2025-02-01 \
        --max-messages 3 --sort-by message_count --sort-order asc -o short.json
"""

import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode, urljoin


def _api_request(base_url, token, path, params=None):
    """Make an authenticated GET request and return parsed JSON."""
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    if params:
        url = f"{url}?{urlencode(params)}"

    headers = {"Content-Type": "application/json"}
    if token.startswith(("sbs_", "kps_")):
        headers["X-API-Key"] = token
    else:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_conversations(base_url, token, project_id, filters, batch_size=100):
    """Paginate through all conversations matching filters.

    The API returns all metadata inline per conversation:
    summary, sentiment_label, sentiment_reason, resources_label,
    resources_reason, skills, tags, has_handoff, message_count, etc.
    """
    all_convs = []
    offset = 0
    total = None

    while True:
        params = {"limit": batch_size, "offset": offset}
        params.update(filters)

        data = _api_request(
            base_url,
            token,
            f"/projects/{project_id}/conversations",
            params,
        )
        convs = data.get("conversations", [])
        total = data.get("total", 0)
        all_convs.extend(convs)

        print(
            f"  Fetched {len(all_convs)}/{total} conversations...",
            file=sys.stderr,
        )

        if len(convs) < batch_size:
            break
        offset += batch_size

    return all_convs, total


def _api_post(base_url, token, path, body):
    """Make an authenticated POST request and return parsed JSON."""
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))

    headers = {"Content-Type": "application/json"}
    if token.startswith(("sbs_", "kps_")):
        headers["X-API-Key"] = token
    else:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, headers=headers, method="POST", data=data)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_messages(base_url, token, project_id, conversations, batch_size=50):
    """Fetch full message history using the batch endpoint.

    Uses POST /conversations/batch to fetch messages in batches of up to 50,
    instead of making one API call per conversation.
    """
    total = len(conversations)
    fetched = 0
    failed = 0

    # Process in batches of batch_size
    for start in range(0, total, batch_size):
        batch = conversations[start : start + batch_size]
        cids = [c.get("conversation_id") for c in batch if c.get("conversation_id")]

        if not cids:
            continue

        try:
            result = _api_post(
                base_url,
                token,
                f"/projects/{project_id}/conversations/batch",
                {"conversation_ids": cids},
            )
            # Build lookup by conversation_id
            detail_map = {}
            for detail in result.get("conversations", []):
                detail_map[detail.get("conversation_id")] = detail

            # Merge messages and citations into existing conversation dicts
            for conv in batch:
                cid = conv.get("conversation_id")
                detail = detail_map.get(cid)
                if detail:
                    conv["messages"] = detail.get("messages", [])
                    conv["citations"] = detail.get("citations", [])
                    fetched += 1
                else:
                    conv["messages"] = []
                    conv["citations"] = []

        except Exception as e:
            # Fallback: mark batch as failed
            for conv in batch:
                conv["messages"] = []
                conv["citations"] = []
            failed += len(batch)
            print(f"  Batch failed: {e}", file=sys.stderr)

        print(
            f"  Fetched messages: {min(start + batch_size, total)}/{total} ({failed} errors)",
            file=sys.stderr,
        )

    return fetched, failed


def write_json(conversations, output_path, total):
    """Write conversations to a JSON file."""
    result = {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_matched": total,
        "total_exported": len(conversations),
        "conversations": conversations,
    }
    content = json.dumps(result, indent=2, ensure_ascii=False)
    with open(output_path, "w") as f:
        f.write(content)
    return len(content)


def write_csv(conversations, output_path):
    """Write conversations to a CSV file (flattened)."""
    if not conversations:
        with open(output_path, "w") as f:
            f.write("")
        return 0

    cols = [
        "conversation_id",
        "inbox_name",
        "playbook_name",
        "playbook_version",
        "playbooks_info",
        "message_count",
        "first_message_at",
        "last_message_at",
        "first_user_message",
        "last_assistant_message",
        "has_handoff",
        "has_error",
        "tags",
        "skills",
        "avg_response_latency_ms",
        "sentiment_label",
        "sentiment_reason",
        "resources_label",
        "resources_reason",
        "summary",
        "model",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()

    for conv in conversations:
        row = {}
        for col in cols:
            val = conv.get(col, "")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            elif isinstance(val, bool):
                val = str(val).lower()
            elif val is None:
                val = ""
            row[col] = val
        writer.writerow(row)

    content = output.getvalue()
    with open(output_path, "w") as f:
        f.write(content)
    return len(content)


def main():
    parser = argparse.ArgumentParser(
        description="Export conversations with all metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Date range
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD or ISO 8601)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD or ISO 8601)")

    # Filters
    parser.add_argument("--playbook-id", help="Filter by playbook version UUID")
    parser.add_argument("--playbook-base-id", help="Filter by playbook base UUID (all versions)")
    parser.add_argument("--inbox-id", help="Filter by inbox UUID")
    parser.add_argument("--tags", help="Comma-separated tags (AND logic)")
    parser.add_argument("--handoff", choices=["true", "false"], help="Filter by handoff status")
    parser.add_argument("--winback", choices=["true", "false"], help="Filter by winback status")
    parser.add_argument("--search", help="Search by conversation ID")
    parser.add_argument("--sentiment", help="Filter by sentiment: negative,neutral,positive")
    parser.add_argument("--resources", help="Filter by resource quality: irrelevant,partial,relevant")
    parser.add_argument("--skill-name", help="Filter by skill name (conversations that loaded this skill)")
    parser.add_argument("--min-messages", type=int, help="Minimum message count")
    parser.add_argument("--max-messages", type=int, help="Maximum message count")
    parser.add_argument(
        "--sort-by",
        choices=["last_message_at", "first_message_at", "message_count"],
        help="Sort field (default: last_message_at)",
    )
    parser.add_argument("--sort-order", choices=["asc", "desc"], help="Sort direction (default: desc)")

    # Messages (the only optional extra — requires per-conversation API calls)
    parser.add_argument(
        "--messages",
        action="store_true",
        help="Include full message history (slower — one API call per conversation)",
    )

    # Output
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format (default: json)")
    parser.add_argument("--batch-size", type=int, default=100, help="Conversations per API page (1-100)")

    args = parser.parse_args()

    # Environment
    base_url = "https://api.studiochat.io"
    token = os.environ.get("STUDIO_API_TOKEN")
    project_id = os.environ.get("STUDIO_PROJECT_ID")

    if not token:
        print("Error: STUDIO_API_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    if not project_id:
        print("Error: STUDIO_PROJECT_ID not set", file=sys.stderr)
        sys.exit(1)

    # Normalize dates
    start = args.start if "T" in args.start else f"{args.start}T00:00:00Z"
    end = args.end if "T" in args.end else f"{args.end}T00:00:00Z"

    # Build filter params
    filters = {"start_date": start, "end_date": end}
    if args.playbook_id:
        filters["playbook_id"] = args.playbook_id
    if args.playbook_base_id:
        filters["playbook_base_id"] = args.playbook_base_id
    if args.inbox_id:
        filters["inbox_id"] = args.inbox_id
    if args.tags:
        filters["tags"] = args.tags
    if args.handoff:
        filters["has_handoff"] = args.handoff
    if args.winback:
        filters["has_winback"] = args.winback
    if args.search:
        filters["search"] = args.search
    if args.sentiment:
        filters["sentiment"] = args.sentiment
    if args.resources:
        filters["resources"] = args.resources
    if args.skill_name:
        filters["skill_name"] = args.skill_name
    if args.min_messages:
        filters["min_messages"] = str(args.min_messages)
    if args.max_messages:
        filters["max_messages"] = str(args.max_messages)
    if args.sort_by:
        filters["sort_by"] = args.sort_by
    if args.sort_order:
        filters["sort_order"] = args.sort_order

    print(f"Exporting conversations ({start} to {end})...", file=sys.stderr)

    # Fetch — all metadata comes inline (single efficient query per page)
    conversations, total = fetch_conversations(
        base_url, token, project_id, filters, args.batch_size
    )
    print(f"Fetched {len(conversations)} conversations (total: {total})", file=sys.stderr)

    # Optionally fetch full message history (requires per-conversation calls)
    if args.messages:
        print("Fetching message history...", file=sys.stderr)
        fetch_messages(base_url, token, project_id, conversations)

    # Write output
    if args.format == "csv":
        size = write_csv(conversations, args.output)
    else:
        size = write_json(conversations, args.output, total)

    print(
        f"Exported {len(conversations)} conversations to {args.output} ({size:,} bytes)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
