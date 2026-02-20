#!/usr/bin/env python3
"""Batch export conversations with optional enrichment.

Paginates through all conversations matching the given filters,
optionally enriches each with metrics (sentiment, summary) and/or
full message history, and writes results to JSON or CSV.

Usage:
    export_conversations.py [options] -o output.json
    export_conversations.py [options] --format csv -o output.csv

Examples:
    # Export all conversations from January 2025
    export_conversations.py --start 2025-01-01 --end 2025-02-01 -o jan.json

    # Export with sentiment and summaries
    export_conversations.py --start 2025-01-01 --end 2025-02-01 \
        --enrich metrics -o jan_with_metrics.json

    # Export only handoff conversations with full messages
    export_conversations.py --start 2025-01-01 --end 2025-02-01 \
        --handoff true --enrich messages -o handoffs.json

    # Export everything: metrics + messages, as CSV
    export_conversations.py --start 2025-01-01 --end 2025-02-01 \
        --enrich all --format csv -o full_export.csv

    # Filter by playbook and tags
    export_conversations.py --start 2025-01-01 --end 2025-02-01 \
        --playbook-base-id abc-123 --tags billing,refund -o billing.json

    # Export only negative sentiment conversations (server-side filter)
    export_conversations.py --start 2025-01-01 --end 2025-02-01 \
        --sentiment negative -o negative.json

    # Export short conversations sorted by message count
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
    if token.startswith("sbs_"):
        headers["X-API-Key"] = token
    else:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_conversations(base_url, token, project_id, filters, batch_size=100):
    """Paginate through all conversations matching filters."""
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


def enrich_with_metrics(base_url, token, project_id, conversations):
    """Add sentiment, resources, and summary to each conversation."""
    total = len(conversations)
    enriched = 0
    failed = 0

    for i, conv in enumerate(conversations):
        cid = conv.get("conversation_id")
        if not cid:
            continue

        try:
            metrics = _api_request(
                base_url,
                token,
                f"/projects/{project_id}/conversations/{cid}/metrics",
            )
            conv["metrics"] = metrics
            enriched += 1
        except urllib.error.HTTPError as e:
            if e.code == 404:
                conv["metrics"] = None
            else:
                conv["metrics"] = {"error": f"HTTP {e.code}"}
                failed += 1
        except Exception as e:
            conv["metrics"] = {"error": str(e)[:200]}
            failed += 1

        if (i + 1) % 25 == 0 or (i + 1) == total:
            print(
                f"  Enriched metrics: {i + 1}/{total} ({failed} errors)",
                file=sys.stderr,
            )
        time.sleep(0.05)  # Be gentle on the API

    return enriched, failed


def enrich_with_messages(base_url, token, project_id, conversations):
    """Add full message history to each conversation."""
    total = len(conversations)
    enriched = 0
    failed = 0

    for i, conv in enumerate(conversations):
        cid = conv.get("conversation_id")
        if not cid:
            continue

        try:
            msg_data = _api_request(
                base_url,
                token,
                f"/projects/{project_id}/conversations/{cid}/messages",
            )
            conv["messages_full"] = msg_data.get("messages", [])
            conv["citations"] = msg_data.get("citations", [])
            enriched += 1
        except urllib.error.HTTPError as e:
            conv["messages_full"] = []
            conv["citations"] = []
            if e.code != 404:
                failed += 1
        except Exception:
            conv["messages_full"] = []
            conv["citations"] = []
            failed += 1

        if (i + 1) % 25 == 0 or (i + 1) == total:
            print(
                f"  Enriched messages: {i + 1}/{total} ({failed} errors)",
                file=sys.stderr,
            )
        time.sleep(0.05)

    return enriched, failed


def filter_by_sentiment(conversations, sentiment_filter):
    """Post-filter conversations by sentiment label (requires metrics enrichment)."""
    labels = [s.strip().lower() for s in sentiment_filter.split(",")]
    filtered = []
    for conv in conversations:
        # Check top-level sentiment_label or enriched metrics
        label = conv.get("sentiment_label", "")
        if not label and conv.get("metrics"):
            label = conv["metrics"].get("sentiment_label", "")
        if label and label.lower() in labels:
            filtered.append(conv)
    return filtered


def filter_by_resources(conversations, resources_filter):
    """Post-filter conversations by resource quality label (requires metrics enrichment)."""
    labels = [r.strip().lower() for r in resources_filter.split(",")]
    filtered = []
    for conv in conversations:
        label = conv.get("resources_label", "")
        if not label and conv.get("metrics"):
            label = conv["metrics"].get("resources_label", "")
        if label and label.lower() in labels:
            filtered.append(conv)
    return filtered


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

    # Determine columns from first conversation + common metrics fields
    base_cols = [
        "conversation_id",
        "inbox_name",
        "playbook_name",
        "playbook_version",
        "message_count",
        "first_message_at",
        "last_message_at",
        "first_user_message",
        "last_assistant_message",
        "has_handoff",
        "has_winback",
        "tags",
        "avg_response_latency_ms",
        "sentiment_label",
        "resources_label",
        "model",
    ]
    metrics_cols = [
        "metrics_sentiment_label",
        "metrics_sentiment_reason",
        "metrics_resources_label",
        "metrics_resources_reason",
        "metrics_summary",
    ]
    all_cols = base_cols + metrics_cols

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_cols, extrasaction="ignore")
    writer.writeheader()

    for conv in conversations:
        row = {}
        for col in base_cols:
            val = conv.get(col, "")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            elif isinstance(val, bool):
                val = str(val).lower()
            row[col] = val

        # Flatten metrics
        metrics = conv.get("metrics") or {}
        if isinstance(metrics, dict):
            row["metrics_sentiment_label"] = metrics.get("sentiment_label", "")
            row["metrics_sentiment_reason"] = metrics.get("sentiment_reason", "")
            row["metrics_resources_label"] = metrics.get("resources_label", "")
            row["metrics_resources_reason"] = metrics.get("resources_reason", "")
            row["metrics_summary"] = metrics.get("summary", "")

        writer.writerow(row)

    content = output.getvalue()
    with open(output_path, "w") as f:
        f.write(content)
    return len(content)


def main():
    parser = argparse.ArgumentParser(
        description="Export conversations with optional enrichment",
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

    # Server-side filters (applied at API level, no enrichment needed)
    parser.add_argument(
        "--sentiment",
        help="Filter by sentiment: negative,neutral,positive (comma-separated). "
        "Applied server-side when possible, falls back to post-filter with --enrich metrics",
    )
    parser.add_argument(
        "--resources",
        help="Filter by resource quality: irrelevant,partial,relevant (comma-separated). "
        "Applied server-side when possible, falls back to post-filter with --enrich metrics",
    )
    parser.add_argument("--min-messages", type=int, help="Minimum message count")
    parser.add_argument("--max-messages", type=int, help="Maximum message count")
    parser.add_argument(
        "--sort-by",
        choices=["last_message_at", "first_message_at", "message_count"],
        help="Sort field (default: last_message_at)",
    )
    parser.add_argument("--sort-order", choices=["asc", "desc"], help="Sort direction (default: desc)")

    # Enrichment
    parser.add_argument(
        "--enrich",
        choices=["none", "metrics", "messages", "all"],
        default="none",
        help="Enrich each conversation with additional data (default: none)",
    )

    # Output
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format (default: json)")
    parser.add_argument("--batch-size", type=int, default=100, help="Conversations per API page (1-100)")

    args = parser.parse_args()

    # Environment
    base_url = os.environ.get("STUDIO_API_URL")
    token = os.environ.get("STUDIO_API_TOKEN")
    project_id = os.environ.get("STUDIO_PROJECT_ID")

    if not base_url:
        print("Error: STUDIO_API_URL not set", file=sys.stderr)
        sys.exit(1)
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

    # Server-side filters (preferred over post-filtering)
    if args.sentiment:
        filters["sentiment"] = args.sentiment
    if args.resources:
        filters["resources"] = args.resources
    if args.min_messages:
        filters["min_messages"] = str(args.min_messages)
    if args.max_messages:
        filters["max_messages"] = str(args.max_messages)
    if args.sort_by:
        filters["sort_by"] = args.sort_by
    if args.sort_order:
        filters["sort_order"] = args.sort_order

    print(f"Exporting conversations ({start} to {end})...", file=sys.stderr)

    # Fetch
    conversations, total = fetch_conversations(
        base_url,
        token,
        project_id,
        filters,
        args.batch_size,
    )
    print(f"Fetched {len(conversations)} conversations (total: {total})", file=sys.stderr)

    # Enrich
    if args.enrich in ("metrics", "all"):
        print("Enriching with metrics (sentiment, summary)...", file=sys.stderr)
        enrich_with_metrics(base_url, token, project_id, conversations)

    if args.enrich in ("messages", "all"):
        print("Enriching with full message history...", file=sys.stderr)
        enrich_with_messages(base_url, token, project_id, conversations)

    # Post-filters (fallback for enriched data — server-side filtering is preferred
    # and already applied above via query params, but enriched metrics may refine further)
    if args.sentiment and args.enrich in ("metrics", "all"):
        before = len(conversations)
        conversations = filter_by_sentiment(conversations, args.sentiment)
        print(f"Sentiment post-filter: {before} → {len(conversations)}", file=sys.stderr)

    if args.resources and args.enrich in ("metrics", "all"):
        before = len(conversations)
        conversations = filter_by_resources(conversations, args.resources)
        print(f"Resources post-filter: {before} → {len(conversations)}", file=sys.stderr)

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
