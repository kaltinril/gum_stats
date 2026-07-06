"""
Fills in missing daily rows in data.csv so you don't have to remember to gather
stats every day. If you skip a day, a week, or a whole month, running this once
backfills every missing calendar day up to today.

How each metric is filled:
  - Today's row:        live current counts from the GitHub API (fully accurate).
  - Missed past days:    STARS, FORKS, ISSUES are reconstructed from timestamped
                         GitHub events (stargazers, forks, issues) — same technique
                         as catchup.py. SUBS has no timestamps, so it's carried
                         forward from the last known value.

By default it fills from the last recorded date up to today. Use --from to also
backfill interior gaps starting at an earlier date.

Usage:
    python fillgaps.py [--token YOUR_GITHUB_TOKEN] [--from YYYY-MM-DD] [--dry-run]

    Token can also come from secret.txt or the GITHUB_TOKEN environment variable.

Examples:
    python fillgaps.py
    python fillgaps.py --from 2026-01-01
    python fillgaps.py --dry-run
"""

import argparse
import csv
import datetime

from repos_config import ALL_REPOS, METRICS
from getCompetitorCounts import (
    OUTPUT_FILENAME,
    ensure_csv_header,
    get_counts_from_repo,
    load_token,
)
from catchup import (
    STARGAZER_API_NOTICE,
    fetch_all_stargazers,
    fetch_all_forks,
    fetch_all_issues,
    parse_date,
    compute_cumulative_counts,
    compute_open_issues_at_dates,
)

CSV_FILE = OUTPUT_FILENAME


def read_csv():
    with open(CSV_FILE, "r", newline="") as f:
        rows = list(csv.reader(f))
    header = [c.strip() for c in rows[0]]
    return header, rows[1:]


def existing_dates(data_rows, date_idx):
    dates = set()
    for row in data_rows:
        if row and row[date_idx].strip():
            dates.add(datetime.datetime.strptime(row[date_idx].strip(), "%Y-%m-%d").date())
    return dates


def last_known_values(header, data_rows):
    """Last non-empty value seen for every column, walking rows top to bottom."""
    date_idx = header.index("DATE")
    last = {}
    # Rows are appended chronologically, but sort by date to be safe.
    ordered = sorted(
        (r for r in data_rows if r and r[date_idx].strip()),
        key=lambda r: r[date_idx].strip(),
    )
    for row in ordered:
        for i, col in enumerate(header):
            if i < len(row):
                val = row[i].strip()
                if val != "" and val != "0":
                    last[col] = val
    return last


def daterange(start, end):
    """Inclusive list of dates from start to end."""
    days = (end - start).days
    return [start + datetime.timedelta(days=i) for i in range(days + 1)]


def main():
    # This script depended on the stargazers-timestamp API, which GitHub has
    # restricted. Rather than run and silently write bogus zero-star rows (as it
    # did before), it now explains why it no longer works and exits without
    # touching data.csv.
    print(STARGAZER_API_NOTICE)
    return

    parser = argparse.ArgumentParser(
        description="Backfill missing daily rows in data.csv up to today."
    )
    parser.add_argument(
        "alias",
        nargs="?",
        help="Only fill this repo alias from repos_config.py (e.g. iguina). "
             "Omit to fill every repo.",
    )
    parser.add_argument("--token", help="GitHub API token (or use secret.txt / GITHUB_TOKEN)")
    parser.add_argument(
        "--from",
        dest="from_date",
        help="Fill starting from this date (YYYY-MM-DD). Default: the last recorded date. "
             "Use an earlier date to also backfill interior gaps.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which dates would be filled without calling the API or writing.",
    )
    args = parser.parse_args()

    # Which repos to fill: one specific alias, or all of them.
    if args.alias:
        target_repos = [r for r in ALL_REPOS if r["alias"] == args.alias]
        if not target_repos:
            print(f"Error: alias '{args.alias}' not found in repos_config.py")
            print(f"Available aliases: {[r['alias'] for r in ALL_REPOS]}")
            return
        print(f"Filling only: {args.alias}\n")
    else:
        target_repos = ALL_REPOS

    token = args.token or load_token()
    if not token:
        print("Warning: No GitHub token provided. Unauthenticated rate limit is 60 requests/hour.")
        print("  Add token to secret.txt, use --token, or set GITHUB_TOKEN env var.\n")

    # Make sure the header matches the current repo config before we touch rows.
    ensure_csv_header(CSV_FILE)
    header, data_rows = read_csv()
    date_idx = header.index("DATE")

    have = existing_dates(data_rows, date_idx)
    if not have:
        print("data.csv has no dated rows yet — run getCompetitorCounts.py first.")
        return

    today = datetime.date.today()
    last_recorded = max(have)

    if args.from_date:
        start = datetime.datetime.strptime(args.from_date, "%Y-%m-%d").date()
    else:
        # Default: the day after the last recorded date (fill forward gaps only).
        start = last_recorded

    # Every calendar day in range that we don't already have.
    candidate_dates = daterange(start, today)
    missing = sorted(d for d in candidate_dates if d not in have)

    if not missing:
        print(f"No gaps to fill — data.csv is current through {last_recorded} (today is {today}).")
        return

    intermediate = [d for d in missing if d < today]
    need_today = today in missing

    print(f"Last recorded date: {last_recorded}")
    print(f"Today: {today}")
    print(f"Missing dates to fill ({len(missing)}):")
    for d in missing:
        kind = "live" if d == today else "backfill"
        print(f"    {d}  [{kind}]")

    if args.dry_run:
        print("\nDry run — no API calls made, nothing written.")
        return

    last = last_known_values(header, data_rows)

    # === Fetch what we need ===
    # Live current counts (only if we're adding today's row).
    live_counts = {}
    if need_today:
        print("\nFetching live current counts for today's row...")
        for r in target_repos:
            print(f"  {r['owner']}/{r['repo']}")
            try:
                live_counts[r["alias"]] = get_counts_from_repo(r["owner"], r["repo"], token)
            except Exception as e:
                print(f"    Failed: {e}")
                live_counts[r["alias"]] = None

    # Historical backfill of STARS / FORKS / ISSUES for intermediate missed days.
    # SUBS is carried forward (no timestamps available).
    backfill = {}  # alias -> {metric -> {date -> count}}
    if intermediate:
        print(f"\nBackfilling {len(intermediate)} past day(s) from timestamped events...")
        for r in target_repos:
            owner, repo, alias = r["owner"], r["repo"], r["alias"]
            print(f"\n  {owner}/{repo} (alias: {alias})")
            per_metric = {}

            print("    [STARS] fetching stargazers...")
            stargazers = fetch_all_stargazers(owner, repo, token)
            star_dates = [parse_date(s["starred_at"]) for s in stargazers]
            per_metric["STARS"] = compute_cumulative_counts(star_dates, intermediate)

            print("    [FORKS] fetching forks...")
            forks = fetch_all_forks(owner, repo, token)
            fork_dates = [parse_date(f["created_at"]) for f in forks]
            per_metric["FORKS"] = compute_cumulative_counts(fork_dates, intermediate)

            print("    [ISSUES] fetching issues...")
            issues = fetch_all_issues(owner, repo, token)
            per_metric["ISSUES"] = compute_open_issues_at_dates(issues, intermediate)

            backfill[alias] = per_metric

    # === Build the new rows ===
    # Iterate ALL_REPOS (not just the targeted ones): the targeted repo gets fresh
    # live/backfilled values, while every other repo carries its last known value
    # forward. This avoids injecting artificial zeros into the untargeted columns
    # of a newly inserted row (chartit.py treats blanks as 0).
    new_rows = []
    for d in missing:
        row = [""] * len(header)
        row[date_idx] = str(d)
        for r in ALL_REPOS:
            alias = r["alias"]
            for metric in METRICS:
                col = f"{metric}_{alias}"
                if col not in header:
                    continue
                col_idx = header.index(col)

                if d == today and live_counts.get(alias) is not None:
                    value = live_counts[alias][metric]
                elif d < today and alias in backfill and metric in backfill[alias]:
                    # STARS/FORKS/ISSUES are reconstructed; SUBS falls through to carry-forward.
                    if metric == "SUBS":
                        value = last.get(col, "")
                    else:
                        value = backfill[alias][metric][d]
                else:
                    # Fallback (e.g. today's live fetch failed): carry forward.
                    value = last.get(col, "")

                row[col_idx] = str(value)
        new_rows.append(row)

    # === Merge, sort by date, rewrite ===
    all_rows = data_rows + new_rows
    all_rows.sort(key=lambda r: r[date_idx].strip())

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(all_rows)

    print(f"\nDone — added {len(new_rows)} row(s) to {CSV_FILE}.")
    print("Note: SUBS on backfilled past days is carried forward (GitHub has no timestamps for it).")


if __name__ == "__main__":
    main()
