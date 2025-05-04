import requests
import os
import datetime

# README: This is all you need to modify, the output file, URL if it's changed, and the REPOS you want
OUTPUT_FILENAME = 'data.csv'
API_URL = 'https://api.github.com/repos'
REPOS = [
    # [owner, repo, alias]
    ["vchelaru", "Gum", "gum"],
    ["RonenNess", "GeonBit.UI", "geonbit"],
    ["rds1983", "Myra", "myra"],
    ["ocornut", "imgui", "imgui"],
    ["Ellpeck", "MLEM", "mlem.ui"],
    ["MonoGo-Engine", "MonoGo", "MonoGo"]
]


def get_counts_from_repo(owner, repo):
    url = f"{API_URL}/{owner}/{repo}"
    response = requests.get(url)
    data = response.json()

    return f"{data['stargazers_count']}, {data['subscribers_count']}, {data['forks_count']}, {data['open_issues_count']}"


def build_single_repo_header(alias):
    return f"STARS_{alias}, SUBS_{alias}, FORKS_{alias}, ISSUES_{alias}"


def build_complete_header(repos):
    headers = ['DATE']
    for repo_info in repos:
        headers.append(build_single_repo_header(repo_info[2]))

    return ", ".join(headers)


# Check if output file exists or is empty and create it necessary
def save_header_row(repos, outfile):
    file_exists = os.path.isfile(outfile)
    should_generate = False

    # First check the file size if it exists, make sure it had a header
    if file_exists:
        size_in_bytes = os.path.getsize(outfile)
        if size_in_bytes == 0:
            should_generate = True
    else:
        should_generate = True

    if should_generate:
        with open(outfile, 'w') as file_handle:
            headers = build_complete_header(repos)
            print(headers, file=file_handle)  # I'm using print instead of write since it automatically adds a newline


def get_stats(repos):
    current_date = datetime.date.today()
    all_stats = [str(current_date)]
    for owner, repo, alias in repos:
        print(owner, repo)

        counts = get_counts_from_repo(owner, repo)
        all_stats.append(counts)

    return ", ".join(all_stats)


def write_stats(stats, outfile):
    with open(outfile, 'a') as f:
        # Read in two integers
        print(stats, file=f)  # I'm using print instead of write since it automatically adds a newline


def main():
    save_header_row(REPOS, OUTPUT_FILENAME)
    stats = get_stats(REPOS)
    write_stats(stats, OUTPUT_FILENAME)


# Make sure the code only runs when this is executed as a script, and not from an INCLUDE call
if __name__ == "__main__":
    main()
