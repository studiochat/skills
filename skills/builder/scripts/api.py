#!/usr/bin/env python3
"""Authenticated API client for Studio Chat — supports all HTTP methods.

Reads STUDIO_API_TOKEN from environment variables
so credentials never appear in command output or logs.

Usage:
    api.py <path>                                       # GET
    api.py <path> --params key=value ...                # GET with query params
    api.py <path> -X POST --body '{"key": "val"}'      # POST with JSON body
    api.py <path> -X PATCH --body '{"name": "new"}'    # PATCH
    api.py <path> -X PUT --body '{"version": 2}'       # PUT
    api.py <path> -X DELETE                             # DELETE
    api.py <path> -o output.json                        # Save to file

Examples:
    # List playbooks
    api.py "/projects/$STUDIO_PROJECT_ID/playbooks"

    # Create a text KB
    api.py "/projects/$STUDIO_PROJECT_ID/knowledgebases/text" \
        -X POST --body '{"title": "FAQ", "content": "..."}'

    # Update playbook instructions
    api.py "/playbooks/PLAYBOOK_ID" \
        -X PATCH --body '{"content": "New instructions..."}'

    # Delete a KB
    api.py "/knowledgebases/KB_ID" -X DELETE

    # Set active playbook version
    api.py "/playbooks/BASE_ID/active" \
        -X PUT --body '{"version_number": 3}'

    # Train project
    api.py "/projects/$STUDIO_PROJECT_ID/train" -X POST
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlencode, urljoin


def main():
    parser = argparse.ArgumentParser(description="Studio Chat API client (all methods)")
    parser.add_argument("path", help="API path (e.g., /projects/{pid}/playbooks)")
    parser.add_argument("--params", nargs="*", default=[], help="Query params as key=value pairs")
    parser.add_argument(
        "-X", "--method", default="GET", choices=["GET", "POST", "PUT", "PATCH", "DELETE"], help="HTTP method"
    )
    parser.add_argument("--body", default=None, help="JSON request body")
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

    # Auth header — detect token type
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
