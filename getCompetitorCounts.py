import datetime

from repos_config import ALL_REPOS, METRICS
from starcounts import (
    CSV_FILE,
    load_token,
    get_counts_from_repo,
    ensure_csv_header,
    already_recorded_today,
    write_row,
)


def get_stats(token=""):
    """Build today's row of current counts for every tracked repo."""
    row = [str(datetime.date.today())]
    for repo_info in ALL_REPOS:
        owner, repo = repo_info["owner"], repo_info["repo"]
        print(f"Fetching: {owner}/{repo}")
        counts = get_counts_from_repo(owner, repo, token)
        for metric in METRICS:
            row.append(str(counts[metric]))
    return row


def main():
    ensure_csv_header(CSV_FILE)

    if already_recorded_today(CSV_FILE):
        print(f"Already have data for {datetime.date.today()} — skipping.")
        return

    token = load_token()
    row = get_stats(token)
    write_row(row, CSV_FILE)


if __name__ == "__main__":
    main()
