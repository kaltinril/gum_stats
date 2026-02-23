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
from repos_config import REPOS

API_URL = "https://api.github.com/repos"
CSV_FILE = "data.csv"


def find_repo_by_alias(alias):
    for r in REPOS:
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
    parser = argparse.ArgumentParser(description="Backfill historical data for a repo")
    parser.add_argument("alias", help="Repo alias from repos_config.py")
    parser.add_argument("--token", help="GitHub API token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--stars-only", action="store_true", help="Only backfill stars")
    args = parser.parse_args()

    # Token priority: --token flag > secret.txt > GITHUB_TOKEN env var
    token = args.token or ""
    if not token:
        secret_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secret.txt")
        if os.path.isfile(secret_path):
            with open(secret_path, "r") as f:
                token = f.read().strip()
            print(f"  Loaded token from secret.txt")
    if not token:
        token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("Warning: No GitHub token provided. Unauthenticated rate limit is 60 requests/hour.")
        print("  Add token to secret.txt, use --token, or set GITHUB_TOKEN env var.\n")

    repo_info = find_repo_by_alias(args.alias)
    if not repo_info:
        print(f"Error: alias '{args.alias}' not found in repos_config.py")
        print(f"Available aliases: {[r['alias'] for r in REPOS]}")
        return

    owner = repo_info["owner"]
    repo = repo_info["repo"]
    alias = args.alias

    print(f"Backfilling data for {owner}/{repo} (alias: {alias})")

    # Get dates from CSV
    with open(CSV_FILE, "r", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = [c.strip() for c in rows[0]]
    date_idx = header.index("DATE")
    dates = []
    for row in rows[1:]:
        date_str = row[date_idx].strip()
        dates.append(datetime.strptime(date_str, "%Y-%m-%d").date())

    print(f"  CSV has {len(dates)} data rows ({dates[0]} to {dates[-1]})")

    # Check which metrics need backfilling before making any API calls
    needs_stars = column_needs_backfill(f"STARS_{alias}")
    needs_forks = not args.stars_only and column_needs_backfill(f"FORKS_{alias}")
    needs_issues = not args.stars_only and column_needs_backfill(f"ISSUES_{alias}")

    if not needs_stars and not needs_forks and not needs_issues:
        print("\n  All columns already have data — nothing to backfill!")
        return

    print(f"\n  Needs backfill: STARS={needs_stars}, FORKS={needs_forks}, ISSUES={needs_issues}")

    # === STARS ===
    if needs_stars:
        print(f"\n  [STARS] Fetching stargazers...")
        stargazers = fetch_all_stargazers(owner, repo, token)
        print(f"  Total stargazers: {len(stargazers)}")
        if stargazers:
            star_dates = [parse_date(s["starred_at"]) for s in stargazers]
            star_counts = compute_cumulative_counts(star_dates, dates)
            print_sample(star_counts, "STARS")
            updated = update_csv_column(f"STARS_{alias}", star_counts)
            print(f"  Updated {updated} rows for STARS_{alias}")
    else:
        print(f"\n  [STARS] Already backfilled — skipping API call")

    # === FORKS ===
    if needs_forks:
        print(f"\n  [FORKS] Fetching forks...")
        forks = fetch_all_forks(owner, repo, token)
        print(f"  Total forks: {len(forks)}")
        if forks:
            fork_dates = [parse_date(f["created_at"]) for f in forks]
            fork_counts = compute_cumulative_counts(fork_dates, dates)
            print_sample(fork_counts, "FORKS")
            updated = update_csv_column(f"FORKS_{alias}", fork_counts)
            print(f"  Updated {updated} rows for FORKS_{alias}")
    elif not args.stars_only:
        print(f"\n  [FORKS] Already backfilled — skipping API call")

    # === ISSUES (open count at each date) ===
    if needs_issues:
        print(f"\n  [ISSUES] Fetching all issues (open + closed)...")
        issues = fetch_all_issues(owner, repo, token)
        real_issues = [i for i in issues if "pull_request" not in i]
        print(f"  Total issues (excl PRs): {len(real_issues)}")
        if issues:
            issue_counts = compute_open_issues_at_dates(issues, dates)
            print_sample(issue_counts, "ISSUES (open)")
            updated = update_csv_column(f"ISSUES_{alias}", issue_counts)
            print(f"  Updated {updated} rows for ISSUES_{alias}")
    elif not args.stars_only:
        print(f"\n  [ISSUES] Already backfilled — skipping API call")

    print("\n  Note: SUBS (subscribers) cannot be backfilled — GitHub has no timestamps for them.")
    print("  Done!")


if __name__ == "__main__":
    main()
