#!/usr/bin/env python3
"""Authenticated fetch utility for Studio Chat API.

Reads STUDIO_API_TOKEN from environment variables
so credentials never appear in command output or logs.

Usage:
    fetch.py <path> [--params key=value ...] [-o output.json]
    fetch.py <path> --method POST [--body '{"key": "val"}'] [-o output.json]

Examples:
    # Fetch analytics for January 2025
    fetch.py "/projects/$STUDIO_PROJECT_ID/conversations/analytics" \
        --params start_date=2025-01-01T00:00:00Z end_date=2025-02-01T00:00:00Z

    # Save to file
    fetch.py "/projects/$STUDIO_PROJECT_ID/conversations" \
        --params limit=100 offset=0 -o conversations.json

    # POST request (for triggering trending topics)
    fetch.py "/projects/$STUDIO_PROJECT_ID/conversations/insights/trending-topics/generate" \
        --method POST --body '{"tags": ["billing"]}'

    # Pipe to jq for quick inspection
    fetch.py "/projects/$STUDIO_PROJECT_ID/conversations/analytics" | jq '.deflection_rate'
"""

import argparse
import json
import os
import sys
from urllib.parse import urlencode, urljoin


def main():
    parser = argparse.ArgumentParser(description="Fetch data from Studio Chat API")
    parser.add_argument("path", help="API path (e.g., /projects/{pid}/conversations/analytics)")
    parser.add_argument("--params", nargs="*", default=[], help="Query params as key=value pairs")
    parser.add_argument("--method", default="GET", choices=["GET", "POST"], help="HTTP method")
    parser.add_argument("--body", default=None, help="JSON request body (for POST)")
    parser.add_argument("-o", "--output", default=None, help="Output file path (default: stdout)")
    args = parser.parse_args()

    api_url = "https://api.studiochat.io"
    api_token = os.environ.get("STUDIO_API_TOKEN")

    if not api_token:
        print("Error: STUDIO_API_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    # Build URL
    url = urljoin(api_url.rstrip("/") + "/", args.path.lstrip("/"))

    # Parse query params
    if args.params:
        params = {}
        for p in args.params:
            if "=" in p:
                k, v = p.split("=", 1)
                params[k] = v
            else:
                print(f"Warning: skipping invalid param '{p}' (expected key=value)", file=sys.stderr)
        if params:
            url = f"{url}?{urlencode(params)}"

    # Use urllib to avoid external dependencies
    import urllib.request

    # Detect token type: kps_ prefix = project API key, otherwise JWT bearer
    headers = {"Content-Type": "application/json"}
    if api_token.startswith("sbs_"):
        headers["X-API-Key"] = api_token
    else:
        headers["Authorization"] = f"Bearer {api_token}"

    body_bytes = None
    if args.body:
        body_bytes = args.body.encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers=headers,
        method=args.method,
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")

            # Pretty-print JSON
            try:
                data = json.loads(raw)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                formatted = raw

            if args.output:
                with open(args.output, "w") as f:
                    f.write(formatted)
                print(f"Saved to {args.output} ({len(formatted)} bytes)", file=sys.stderr)
            else:
                print(formatted)

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body[:500]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
