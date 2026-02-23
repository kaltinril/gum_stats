# Gum GitHub Stats Tracker

Tracks GitHub statistics (stars, subscribers, forks, open issues) for Gum and competing MonoGame UI libraries over time, and visualizes the data as charts.

## Project Structure

| File | Description |
|---|---|
| `repos_config.py` | Single source of truth for all tracked repositories. Add, remove, or exclude repos here. |
| `getCompetitorCounts.py` | Fetches current stats from the GitHub API and appends a new row to `data.csv`. |
| `catchup.py` | Backfills historical data for a newly added repo using timestamped GitHub API data. |
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

### Backfill a newly added repo

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

## Adding a New Repo

1. Add an entry to the `REPOS` list in `repos_config.py`:
   ```python
   {"owner": "GitHubUser", "repo": "RepoName", "alias": "myalias", "display_name": "My Repo", "excluded_from_chart": False},
   ```
2. Run `python getCompetitorCounts.py` -- this will auto-expand the CSV header and collect the first data point
3. Run `python catchup.py myalias` to backfill historical data for the new repo

Set `excluded_from_chart` to `True` to keep collecting data but hide the repo from charts (e.g. ImGui and Nez are tracked but excluded since they aren't UI libraries).
