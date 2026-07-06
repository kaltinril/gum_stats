# Gum GitHub Stats Tracker

Tracks GitHub statistics (stars, subscribers, forks, open issues) for Gum and competing MonoGame UI libraries over time, and visualizes the data as charts.

> **⚠️ Historical backfill is no longer available.** `catchup.py` and `fillgaps.py` depended on GitHub's stargazers-with-timestamps API to reconstruct past star counts. As of GitHub's [stargazer API restriction](https://www.star-history.com/blog/github-stargazer-api-restriction/), that endpoint returns **404 Not Found** for any repository you don't own or collaborate on, so historical stars can no longer be reconstructed for competitor repos. Going forward, collect data day-by-day with `getCompetitorCounts.py`.

## Project Structure

| File | Description |
|---|---|
| `repos_config.py` | Single source of truth for all tracked repositories. Add, remove, or exclude repos here. |
| `getCompetitorCounts.py` | Fetches current stats from the GitHub API and appends a new row to `data.csv` for today. |
| `fillgaps.py` | **No longer available** — relied on the stargazers-timestamp API that GitHub has restricted (see below). |
| `catchup.py` | **No longer available** — relied on the stargazers-timestamp API that GitHub has restricted (see below). |
| `chartit.py` | Generates stacked bar charts with sparkline insets showing original vs. change over time. |
| `chartit2.py` | Alternate chart layout with sparklines in a dedicated row above each metric's bars. |
| `data.csv` | The collected time-series data. Each row is a snapshot date. |
| `secret.txt` | Your GitHub personal access token (not committed to git). |

## Setup

### 1. Install Python

Download from https://www.python.org/downloads/

### 2. Install dependencies

```
pip install requests pandas matplotlib numpy
```

### 3. Create `secret.txt`

Create a file called `secret.txt` in this directory containing your GitHub personal access token. This increases the API rate limit from 60 to 5,000 requests per hour.

1. Go to https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Give it a name (e.g. "gum-stats") and select the `public_repo` scope
4. Copy the token
5. Create `secret.txt` in this folder and paste the token as the only content

This file is already in `.gitignore` so it won't be committed.

Alternatively, you can set the `GITHUB_TOKEN` environment variable instead.

## Usage

### Collect today's stats

```
python getCompetitorCounts.py
```

Fetches current stats for all repos in `repos_config.py` and appends a new row to `data.csv`. Skips if today's date already has an entry.

### Fill in missed days — _no longer available_

> Kept for reference only. This depended on the stargazers-timestamp API that GitHub has restricted (see the note at the top), so it can no longer reconstruct historical star counts for competitor repos. Running it now prints an explanation and exits.

```
python fillgaps.py
```

If you forget to run the collector for a while, this catches you up by adding a row for every calendar day between the last recorded date and today.

- **Today's row** uses live current counts from the GitHub API (fully accurate).
- **Missed past days** have their stars, forks, and open issues reconstructed from timestamped GitHub data (the same technique as `catchup.py`). Subscribers (SUBS) have no timestamps, so they're carried forward from the last known value.
- Pass an optional alias to fill just one repo, e.g. `python fillgaps.py iguina` (other repos' values are carried forward, not zeroed).
- Use `--from YYYY-MM-DD` to also backfill interior gaps starting from an earlier date.
- Use `--dry-run` to preview which dates would be filled without calling the API or writing.
- Safe to re-run: dates that already exist are skipped.

Example:
```
python fillgaps.py --from 2026-01-01 --dry-run
```

### Backfill a newly added repo — _no longer available_

> Kept for reference only. This depended on the stargazers-timestamp API that GitHub has restricted (see the note at the top), so it can no longer reconstruct historical star counts for competitor repos. Running it now prints an explanation and exits.

```
python catchup.py <alias>
```

When you add a new repo to `repos_config.py`, its historical columns in `data.csv` will be empty. This script backfills stars, forks, and open issues by fetching timestamped data from the GitHub API.

- `<alias>` is the repo's alias from `repos_config.py` (e.g. `iguina`, `mgui`, `apos.gui`)
- Subscribers (SUBS) cannot be backfilled since GitHub has no timestamps for them
- Uses `secret.txt` automatically, or pass `--token YOUR_TOKEN`
- Use `--stars-only` to only backfill star counts

Example:
```
python catchup.py iguina
```

### View charts

```
python chartit.py
```
or
```
python chartit2.py
```

Both scripts read `data.csv` and display stacked bar charts (original value vs. change) with sparklines showing percent change over time. Only repos not marked as `excluded_from_chart` in `repos_config.py` are shown.

By default the chart covers all recorded data. Use `-y`/`--years` to limit it to a recent window (the "original" baseline becomes the start of that window):

```
python chartit.py            # show everything
python chartit.py -y 1       # only the last 1 year
python chartit.py -y 0.5     # only the last 6 months
```

## Adding a New Repo

1. Add an entry to the `ALL_REPOS` list in `repos_config.py`:
   ```python
   {"owner": "GitHubUser", "repo": "RepoName", "alias": "myalias", "display_name": "My Repo", "excluded_from_chart": False},
   ```
2. Run `python getCompetitorCounts.py` -- this will auto-expand the CSV header and collect the first data point
3. Historical data will start from that first data point. (Backfilling earlier history via `catchup.py` is no longer possible — see the note at the top.)

Set `excluded_from_chart` to `True` to keep collecting data but hide the repo from charts (e.g. ImGui and Nez are tracked but excluded since they aren't UI libraries).
