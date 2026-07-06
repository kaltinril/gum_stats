"""
Backfills historical data (STARS, FORKS, ISSUES) for a target repo by fetching
timestamped records from GitHub and computing cumulative counts at each date in data.csv.

Note: SUBS (subscribers) cannot be backfilled — GitHub's API has no timestamps for them.

Usage:
    python catchup.py <alias> [--token YOUR_GITHUB_TOKEN]

    alias: The repo alias from repos_config.py (e.g. "iguina", "mgui", "apos.gui", "nez")

    Token can also be set via GITHUB_TOKEN environment variable.

Example:
    python catchup.py iguina --token ghp_xxxxxxxxxxxx
"""

import argparse
import csv
import os
import requests
from datetime import datetime
from repos_config import ALL_REPOS

API_URL = "https://api.github.com/repos"
CSV_FILE = "data.csv"

# GitHub restricted the stargazers-with-timestamps API: GET /repos/{owner}/{repo}/stargazers
# now returns 404 Not Found for any repo you don't own or collaborate on. That makes
# historical star backfill impossible for competitor repos, which is this script's whole point.
# See: https://www.star-history.com/blog/github-stargazer-api-restriction/
STARGAZER_API_NOTICE = (
    "\n" + "=" * 70 + "\n"
    "NO LONGER AVAILABLE: historical star backfill has been disabled.\n"
    + "=" * 70 + "\n"
    "GitHub restricted the stargazers-timestamp API (GET .../stargazers).\n"
    "It now returns 404 Not Found for any repository you don't own or\n"
    "collaborate on, so past star counts can no longer be reconstructed\n"
    "for competitor repos.\n\n"
    "  Details: https://www.star-history.com/blog/github-stargazer-api-restriction/\n\n"
    "Going forward, collect data day-by-day with getCompetitorCounts.py.\n"
    + "=" * 70 + "\n"
)


def find_repo_by_alias(alias):
    for r in ALL_REPOS:
        if r["alias"] == alias:
            return r
    return None


def fetch_paginated(url, headers, params_extra=None):
    """Generic paginated GitHub API fetcher. Returns list of all items."""
    all_items = []
    page = 1
    per_page = 100

    while True:
        params = {"per_page": per_page, "page": page}
        if params_extra:
            params.update(params_extra)

        print(f"    page {page}...", end="", flush=True)
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining", "?")
            reset = response.headers.get("X-RateLimit-Reset", "?")
            print(f" RATE LIMITED! (remaining: {remaining}, resets: {reset})")
            break

        if response.status_code != 200:
            print(f" Error {response.status_code}: {response.text[:200]}")
            break

        data = response.json()
        if not data:
            print(f" empty")
            break

        all_items.extend(data)
        print(f" got {len(data)} (total: {len(all_items)})")

        if len(data) < per_page:
            break

        page += 1

    return all_items


def fetch_all_stargazers(owner, repo, token):
    """Fetch all stargazers with timestamps."""
    url = f"{API_URL}/{owner}/{repo}/stargazers"
    headers = {"Accept": "application/vnd.github.v3.star+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return fetch_paginated(url, headers)


def fetch_all_forks(owner, repo, token):
    """Fetch all forks with created_at timestamps."""
    url = f"{API_URL}/{owner}/{repo}/forks"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return fetch_paginated(url, headers, {"sort": "oldest"})


def fetch_all_issues(owner, repo, token):
    """Fetch all issues (open + closed) with created_at/closed_at timestamps."""
    url = f"{API_URL}/{owner}/{repo}/issues"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # state=all gets both open and closed; exclude pull requests later
    return fetch_paginated(url, headers, {"state": "all", "sort": "created", "direction": "asc"})


def parse_date(timestamp):
    """Parse a GitHub API timestamp to a date."""
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").date()


def compute_cumulative_counts(event_dates, target_dates):
    """
    Given a sorted list of event dates and target dates,
    compute cumulative count at each target date.
    """
    sorted_events = sorted(event_dates)
    counts = {}
    for target_date in target_dates:
        count = 0
        for ed in sorted_events:
            if ed <= target_date:
                count += 1
            else:
                break
        counts[target_date] = count
    return counts


def compute_open_issues_at_dates(issues, target_dates):
    """
    For each target date, compute how many issues were open at that point.
    An issue is open at date D if: created_at <= D and (closed_at is None or closed_at > D).
    Excludes pull requests (GitHub issues API includes PRs).
    """
    parsed = []
    for issue in issues:
        # Skip pull requests
        if "pull_request" in issue:
            continue
        created = parse_date(issue["created_at"])
        closed = parse_date(issue["closed_at"]) if issue.get("closed_at") else None
        parsed.append((created, closed))

    counts = {}
    for target_date in target_dates:
        open_count = 0
        for created, closed in parsed:
            if created <= target_date:
                if closed is None or closed > target_date:
                    open_count += 1
        counts[target_date] = open_count
    return counts


def column_needs_backfill(col_name):
    """Check if a column has any empty or zero values that need backfilling."""
    with open(CSV_FILE, "r", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = [c.strip() for c in rows[0]]

    if col_name not in header:
        return False

    col_idx = header.index(col_name)
    for row in rows[1:]:
        val = row[col_idx].strip() if col_idx < len(row) else ""
        if val == "" or val == "0":
            return True
    return False


def update_csv_column(col_name, counts_by_date):
    """Update a single column in data.csv with historical counts."""
    with open(CSV_FILE, "r", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = [c.strip() for c in rows[0]]

    if col_name not in header:
        print(f"  Column {col_name} not found in CSV header!")
        return 0

    col_idx = header.index(col_name)
    date_idx = header.index("DATE")

    updated = 0
    for row in rows[1:]:
        date_str = row[date_idx].strip()
        date_val = datetime.strptime(date_str, "%Y-%m-%d").date()

        if date_val in counts_by_date:
            current_val = row[col_idx].strip() if col_idx < len(row) else ""
            # Only fill in if empty or zero
            if current_val == "" or current_val == "0":
                row[col_idx] = str(counts_by_date[date_val])
                updated += 1

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return updated


def print_sample(counts, label):
    """Print a sample of counts for verification."""
    sample_dates = sorted(counts.keys())
    step = max(1, len(sample_dates) // 5)
    print(f"\n  Sample {label}:")
    for d in sample_dates[::step]:
        print(f"    {d}: {counts[d]}")


def main():
    # This script depended on the stargazers-timestamp API, which GitHub has
    # restricted. Rather than run and silently write bogus zero-star rows, it now
    # explains why it no longer works and exits without touching data.csv.
    print(STARGAZER_API_NOTICE)


if __name__ == "__main__":
    main()
