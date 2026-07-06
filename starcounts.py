"""
starcounts.py — shared library for the Gum GitHub stats tracker.

Holds the functionality that was previously duplicated across (or awkwardly
cross-imported between) the individual scripts:

  - token loading                     load_token()
  - repo lookup                       find_repo_by_alias()
  - live GitHub API                   get_counts_from_repo()
  - historical GitHub API             fetch_paginated(), fetch_all_stargazers/forks/issues()
  - date math                         parse_date(), compute_cumulative_counts(),
                                      compute_open_issues_at_dates()
  - data.csv read/write helpers       read_csv(), build_complete_header(),
                                      ensure_csv_header(), already_recorded_today(),
                                      write_row(), column_needs_backfill(), update_csv_column()
  - chart data loading                load_chart_data(), parse_years_arg()

getCompetitorCounts.py, catchup.py, fillgaps.py, chartit.py and chartit2.py all
import from here so there is a single source of truth for each piece of logic.
"""

import argparse
import csv
import datetime
import os

import requests

from repos_config import (
    ALL_REPOS,
    METRICS,
    get_column_names,
    get_chart_repositories,
)

API_URL = "https://api.github.com/repos"
CSV_FILE = "data.csv"

# GitHub restricted the stargazers-with-timestamps API: GET /repos/{owner}/{repo}/stargazers
# now returns 404 Not Found for any repo you don't own or collaborate on. That makes
# historical star backfill impossible for competitor repos, which is why catchup.py and
# fillgaps.py are no longer usable.
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


# =============================================================================
# Token
# =============================================================================

def load_token():
    """Load GitHub token from secret.txt (next to this file) or GITHUB_TOKEN env var."""
    secret_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secret.txt")
    if os.path.isfile(secret_path):
        with open(secret_path, "r") as f:
            token = f.read().strip()
        if token:
            return token
    return os.environ.get("GITHUB_TOKEN", "")


# =============================================================================
# Repo config lookup
# =============================================================================

def find_repo_by_alias(alias):
    """Return the repo config dict for an alias, or None if not found."""
    for r in ALL_REPOS:
        if r["alias"] == alias:
            return r
    return None


# =============================================================================
# Live GitHub API (current counts)
# =============================================================================

def get_counts_from_repo(owner, repo, token=""):
    """Fetch the current STARS/SUBS/FORKS/ISSUES counts for a repo."""
    url = f"{API_URL}/{owner}/{repo}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(url, headers=headers)
    data = response.json()

    return {
        "STARS": data["stargazers_count"],
        "SUBS": data["subscribers_count"],
        "FORKS": data["forks_count"],
        "ISSUES": data["open_issues_count"],
    }


# =============================================================================
# Historical GitHub API (timestamped events)
#
# NOTE: fetch_all_stargazers no longer works for repos you don't own — GitHub
# restricted the endpoint (see STARGAZER_API_NOTICE). Kept for reference and for
# repos you do own/collaborate on. Forks and issues endpoints still work.
# =============================================================================

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
    """Fetch all stargazers with timestamps (restricted by GitHub for non-owned repos)."""
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


# =============================================================================
# Date math / cumulative counts
# =============================================================================

def parse_date(timestamp):
    """Parse a GitHub API timestamp (e.g. 2025-01-02T03:04:05Z) to a date."""
    return datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").date()


def compute_cumulative_counts(event_dates, target_dates):
    """Cumulative number of events on/before each target date."""
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
    For each target date, how many issues were open at that point.
    An issue is open at date D if created_at <= D and (closed_at is None or closed_at > D).
    Excludes pull requests (the issues API includes PRs).
    """
    parsed = []
    for issue in issues:
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


# =============================================================================
# data.csv read/write helpers
# =============================================================================

def read_csv(outfile=CSV_FILE):
    """Return (header, data_rows) with the header stripped of whitespace."""
    with open(outfile, "r", newline="") as f:
        rows = list(csv.reader(f))
    header = [c.strip() for c in rows[0]]
    return header, rows[1:]


def build_complete_header():
    """The full expected CSV header for the current repo config."""
    return ["DATE"] + get_column_names()


def ensure_csv_header(outfile=CSV_FILE):
    """
    Ensure the CSV header matches the current config. If new repos were added,
    rewrite the file with the expanded header and pad historical rows with empty
    values for the new columns.
    """
    expected_header = build_complete_header()

    if not os.path.isfile(outfile) or os.path.getsize(outfile) == 0:
        with open(outfile, "w", newline="") as f:
            csv.writer(f).writerow(expected_header)
        return

    with open(outfile, "r", newline="") as f:
        rows = list(csv.reader(f))

    if not rows:
        with open(outfile, "w", newline="") as f:
            csv.writer(f).writerow(expected_header)
        return

    existing_header = [col.strip() for col in rows[0]]
    if existing_header == expected_header:
        return  # Nothing to do

    # Header mismatch: map old columns by name to new positions to preserve data.
    old_to_new = {}
    for i, col in enumerate(existing_header):
        if col in expected_header:
            old_to_new[i] = expected_header.index(col)

    new_rows = [expected_header]
    for old_row in rows[1:]:
        new_row = [""] * len(expected_header)
        for old_i, new_i in old_to_new.items():
            if old_i < len(old_row):
                new_row[new_i] = old_row[old_i].strip()
        new_rows.append(new_row)

    with open(outfile, "w", newline="") as f:
        csv.writer(f).writerows(new_rows)

    print(f"CSV header updated: {len(existing_header)} -> {len(expected_header)} columns")


def already_recorded_today(outfile=CSV_FILE):
    """True if today's date already has an entry in the CSV."""
    today = str(datetime.date.today())
    if not os.path.isfile(outfile):
        return False
    with open(outfile, "r", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if row and row[0].strip() == today:
                return True
    return False


def write_row(row, outfile=CSV_FILE):
    """Append a single row to the CSV."""
    with open(outfile, "a", newline="") as f:
        csv.writer(f).writerow(row)


def column_needs_backfill(col_name, outfile=CSV_FILE):
    """True if a column has any empty or zero values that could be backfilled."""
    header, data_rows = read_csv(outfile)
    if col_name not in header:
        return False
    col_idx = header.index(col_name)
    for row in data_rows:
        val = row[col_idx].strip() if col_idx < len(row) else ""
        if val == "" or val == "0":
            return True
    return False


def update_csv_column(col_name, counts_by_date, outfile=CSV_FILE):
    """Fill empty/zero cells of a single column with historical counts by date."""
    with open(outfile, "r", newline="") as f:
        rows = list(csv.reader(f))

    header = [c.strip() for c in rows[0]]
    if col_name not in header:
        print(f"  Column {col_name} not found in CSV header!")
        return 0

    col_idx = header.index(col_name)
    date_idx = header.index("DATE")

    updated = 0
    for row in rows[1:]:
        date_val = datetime.datetime.strptime(row[date_idx].strip(), "%Y-%m-%d").date()
        if date_val in counts_by_date:
            current_val = row[col_idx].strip() if col_idx < len(row) else ""
            if current_val == "" or current_val == "0":
                row[col_idx] = str(counts_by_date[date_val])
                updated += 1

    with open(outfile, "w", newline="") as f:
        csv.writer(f).writerows(rows)

    return updated


# =============================================================================
# Chart data loading (pandas)
# =============================================================================

def parse_years_arg(description="Chart GitHub repository stats."):
    """Parse the shared -y/--years chart argument. Returns years (float) or None."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "-y", "--years",
        type=float,
        default=None,
        help="Number of years back to include (e.g. -y 1). If omitted, shows everything.",
    )
    return parser.parse_args().years


def load_chart_data(years=None):
    """
    Load data.csv for charting.

    Returns (data, repositories, metrics) where:
      - data is a DataFrame with a parsed DATE column and every charted metric
        column coerced to numeric (missing columns filled with 0),
      - repositories is {display_name: alias} for repos not excluded from charts,
      - metrics is the METRICS list.

    If years is given, only rows within that many years of the latest date are kept
    (so the chart's "original" baseline becomes the start of that window).
    """
    import pandas as pd  # local import so the API/CSV scripts don't pay for pandas

    data = pd.read_csv(CSV_FILE)
    data.columns = data.columns.str.strip()
    data["DATE"] = pd.to_datetime(data["DATE"])

    if years is not None:
        cutoff = data["DATE"].max() - pd.DateOffset(days=round(years * 365.25))
        data = data[data["DATE"] >= cutoff].reset_index(drop=True)

    repositories = get_chart_repositories()
    for prefix in repositories.values():
        for metric in METRICS:
            col = f"{metric}_{prefix}"
            if col not in data.columns:
                data[col] = 0
            else:
                data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    return data, repositories, METRICS
