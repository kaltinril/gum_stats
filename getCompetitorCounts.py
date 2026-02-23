import requests
import os
import datetime
import csv
from repos_config import REPOS, METRICS, get_column_names

OUTPUT_FILENAME = 'data.csv'
API_URL = 'https://api.github.com/repos'


def load_token():
    """Load GitHub token from secret.txt or GITHUB_TOKEN env var."""
    secret_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secret.txt")
    if os.path.isfile(secret_path):
        with open(secret_path, "r") as f:
            token = f.read().strip()
        if token:
            return token
    return os.environ.get("GITHUB_TOKEN", "")


def get_counts_from_repo(owner, repo, token=""):
    url = f"{API_URL}/{owner}/{repo}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(url, headers=headers)
    data = response.json()

    return {
        "STARS": data['stargazers_count'],
        "SUBS": data['subscribers_count'],
        "FORKS": data['forks_count'],
        "ISSUES": data['open_issues_count'],
    }


def build_complete_header():
    return ["DATE"] + get_column_names()


def ensure_csv_header(outfile):
    """
    Ensures the CSV header matches the current config.
    If new repos were added, rewrites the file with expanded header
    and pads historical rows with empty values for the new columns.
    """
    expected_header = build_complete_header()

    if not os.path.isfile(outfile) or os.path.getsize(outfile) == 0:
        with open(outfile, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(expected_header)
        return

    # Read existing file
    with open(outfile, 'r', newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        with open(outfile, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(expected_header)
        return

    existing_header = [col.strip() for col in rows[0]]

    if existing_header == expected_header:
        return  # Nothing to do

    # Header mismatch: new columns need to be added.
    # Map old columns by name to new positions to preserve all historical data.
    old_to_new = {}
    for i, col in enumerate(existing_header):
        if col in expected_header:
            old_to_new[i] = expected_header.index(col)

    new_rows = [expected_header]
    for old_row in rows[1:]:
        new_row = [''] * len(expected_header)
        for old_i, new_i in old_to_new.items():
            if old_i < len(old_row):
                new_row[new_i] = old_row[old_i].strip()
        new_rows.append(new_row)

    with open(outfile, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

    print(f"CSV header updated: {len(existing_header)} -> {len(expected_header)} columns")


def already_recorded_today(outfile):
    """Check if today's date already has an entry in the CSV."""
    today = str(datetime.date.today())
    if not os.path.isfile(outfile):
        return False
    with open(outfile, 'r', newline='') as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if row and row[0].strip() == today:
                return True
    return False


def get_stats(token=""):
    current_date = datetime.date.today()
    row = [str(current_date)]
    for repo_info in REPOS:
        owner = repo_info["owner"]
        repo = repo_info["repo"]
        print(f"Fetching: {owner}/{repo}")
        counts = get_counts_from_repo(owner, repo, token)
        for metric in METRICS:
            row.append(str(counts[metric]))
    return row


def write_stats(row, outfile):
    with open(outfile, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row)


def main():
    ensure_csv_header(OUTPUT_FILENAME)

    if already_recorded_today(OUTPUT_FILENAME):
        print(f"Already have data for {datetime.date.today()} — skipping.")
        return

    token = load_token()
    row = get_stats(token)
    write_stats(row, OUTPUT_FILENAME)


# Make sure the code only runs when this is executed as a script, and not from an INCLUDE call
if __name__ == "__main__":
    main()
