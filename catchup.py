"""
catchup.py — NO LONGER AVAILABLE (kept for reference).

Backfilled historical data (STARS, FORKS, ISSUES) for a target repo by fetching
timestamped records from GitHub and computing cumulative counts at each date in
data.csv.

This relied on GitHub's stargazers-timestamp API, which GitHub has restricted
(see starcounts.STARGAZER_API_NOTICE): GET /repos/.../stargazers now returns 404
for any repo you don't own or collaborate on. Running this now prints an
explanation and exits without touching data.csv. The full implementation is kept
below for reference and for repos you own where the stargazer API still works.

The reusable fetch/compute/CSV helpers live in starcounts.py.

Original usage:
    python catchup.py <alias> [--token YOUR_GITHUB_TOKEN] [--stars-only]
"""

import argparse
import datetime

from repos_config import ALL_REPOS
from starcounts import (
    CSV_FILE,
    STARGAZER_API_NOTICE,
    load_token,
    find_repo_by_alias,
    read_csv,
    fetch_all_stargazers,
    fetch_all_forks,
    fetch_all_issues,
    parse_date,
    compute_cumulative_counts,
    compute_open_issues_at_dates,
    column_needs_backfill,
    update_csv_column,
)


def print_sample(counts, label):
    """Print a sample of counts for verification."""
    sample_dates = sorted(counts.keys())
    step = max(1, len(sample_dates) // 5)
    print(f"\n  Sample {label}:")
    for d in sample_dates[::step]:
        print(f"    {d}: {counts[d]}")


def main():
    # Backfilling historical stars relied on the stargazers-timestamp API, which
    # GitHub has restricted. Rather than run and write bogus zero-star rows, this
    # prints an explanation and exits. The reference implementation follows.
    print(STARGAZER_API_NOTICE)
    return

    parser = argparse.ArgumentParser(description="Backfill historical data for a repo")
    parser.add_argument("alias", help="Repo alias from repos_config.py")
    parser.add_argument("--token", help="GitHub API token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--stars-only", action="store_true", help="Only backfill stars")
    args = parser.parse_args()

    token = args.token or load_token()
    if not token:
        print("Warning: No GitHub token provided. Unauthenticated rate limit is 60 requests/hour.")
        print("  Add token to secret.txt, use --token, or set GITHUB_TOKEN env var.\n")

    repo_info = find_repo_by_alias(args.alias)
    if not repo_info:
        print(f"Error: alias '{args.alias}' not found in repos_config.py")
        print(f"Available aliases: {[r['alias'] for r in ALL_REPOS]}")
        return

    owner = repo_info["owner"]
    repo = repo_info["repo"]
    alias = args.alias

    print(f"Backfilling data for {owner}/{repo} (alias: {alias})")

    header, data_rows = read_csv(CSV_FILE)
    date_idx = header.index("DATE")
    dates = [datetime.datetime.strptime(row[date_idx].strip(), "%Y-%m-%d").date() for row in data_rows]

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
