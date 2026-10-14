# Phase 1: Automate collection and host the charts on GitHub

**Status:** merged to `main` 2026-10-14. Daily collection is live. The Pages deploy is skipped while the repo is private (the free plan has no Pages for private repos) and starts on its own once the repo is public and Pages is set to "GitHub Actions".
**Goal:** stop running the collector by hand, never lose a snapshot, and publish an
always-current chart page without running a web server. GitHub does all of it, the
same way [XnaFiddle](https://github.com/vchelaru/XnaFiddle) is hosted on GitHub Pages.

This is a proof of concept in `kaltinril/gum_stats`. Phase 2 (below) covers moving
it under the Gum project once it has run reliably for a while.

## How it works

```
 daily cron (06:17 UTC) or "Run workflow" button
        |
        v
 collect job ── getCompetitorCounts.py ── appends today's row to data.csv
        |       validate_data.py --baseline   (refuses if any row was lost or changed)
        |       git commit + push data.csv    (one commit per day = the backup)
        |       upload data.csv as a run artifact (90 days)
        v
 build job ──── validate_data.py, build_site.py ── _site/ (index.html, data.csv, data.json, repos.json)
        v
 deploy job ─── GitHub Pages
```

| Requirement | How it's met |
|---|---|
| 1. Action that updates the stars | `.github/workflows/stats.yml`, job `collect`, runs daily and on demand. Uses the workflow's built-in `GITHUB_TOKEN`, so no secret to create or rotate. |
| 2. Data stored so it can't be lost | `data.csv` stays in the repo and every daily row is its own commit, so the full history is in git and on every clone. `validate_data.py --baseline` blocks any run that would drop or edit an existing row. The collector now stops on any API error instead of writing a bad row. Each run also keeps a copy of the CSV as a 90-day artifact, and the live site serves the latest copy. |
| 3. Simple site with charts and downloads | `site/index.html`: one static page, Chart.js from a CDN. Pick a metric (stars, forks, watchers, open issues), a range (all, 1 year, 6 months, 90 days), and total / gained / % growth; toggle libraries on and off. Shows a latest-numbers table and every recorded row. Downloads: full `data.csv`, full `data.json`, and the current chart as CSV. Follows the OS light/dark setting. |
| 4. Everything stored and deployed in GitHub | Code, data, workflow and site all live in the repo; GitHub Actions runs it and GitHub Pages serves it. Nothing to host. |

Pull requests run `validate` + `build` only (no collect, no deploy), so a broken page or
a bad hand edit to `data.csv` shows up as a red check before merge.

## New and changed files

| File | Change |
|---|---|
| `.github/workflows/stats.yml` | New. Collect, build and deploy jobs. |
| `validate_data.py` | New. Header, date order and value checks, plus the append-only baseline check. |
| `build_site.py` | New. Builds `_site/` with the standard library only. |
| `site/index.html` | New. The chart page. |
| `starcounts.py` | `get_counts_from_repo` now raises on a non-200 response and has a 30 s timeout. Before, a rate-limit or 404 response crashed on a missing key with an unclear message. |
| `.gitignore` | Ignores `_site/`. |

## One-time setup (owner, in the GitHub UI)

1. **Repo visibility.** `gum_stats` is private. GitHub Pages on a private repo needs a
   paid plan (Pro, Team or Enterprise), and the published site is public either way.
   Either make the repo public (the data is all public GitHub numbers) or confirm the
   account has Pro.
2. **Settings > Pages > Build and deployment > Source: GitHub Actions.**
3. Merge the branch to `main`. The push runs build + deploy; the site appears at
   `https://kaltinril.github.io/gum_stats/`.
4. **Actions tab > "Collect stats and publish site" > Run workflow** once to confirm the
   collect job can push. If the push is refused, set
   **Settings > Actions > General > Workflow permissions** to "Read and write".

## Things to know

- **Stop running `getCompetitorCounts.py` by hand** once the Action is live, or run
  `git pull` first. A same-day local row and an Action row would conflict on push.
- Dates are UTC (the runner's clock). A run late in the US evening records the next
  day's date.
- GitHub turns off scheduled workflows after 60 days with no repository activity. The
  daily data commit counts as activity, so this only bites if collection fails for
  60 days straight. A failed run emails the repo owner.
- GitHub's scheduler can start a cron run late (minutes, sometimes an hour) under load.
  That only changes which hour the snapshot is from, not the day.
- Adding a repo is unchanged: add it to `repos_config.py` and the next run widens the
  CSV. Its chart color comes from its position in that list, and the page shows at
  most 8 charted libraries (more go to the table as "not charted").

## Verified locally

- `validate_data.py` passes on the current `data.csv` (78 rows, 40 columns).
- Baseline check rejects a duplicate date, a dropped row, and an edited historical
  value.
- `build_site.py` builds `_site/`; the page was served locally and screenshotted in
  light and dark mode with the real data.
- On GitHub (2026-10-14): manual runs pass collect (correctly skipped, since 2026-10-14 was already recorded) and build; deploy skipped while private. The first real commit-and-push from the Action is the next scheduled run.

## Phase 2: move it under Gum (later)

Vic's preference is for this to live with Gum. Once phase 1 has run unattended for a
few weeks, options to discuss with him:

- **A separate repo under `vchelaru`** (for example `vchelaru/GumStats`), like
  XnaFiddle. Simplest: move this repo as-is, and the daily bot commits stay out of
  Gum's history. Site at `vchelaru.github.io/GumStats/`.
- **Inside the Gum repo.** Put the scripts in a folder, keep `data.csv` on a separate
  `stats-data` branch so daily commits don't land on `master`, and deploy from a
  workflow there. Gum's own Pages site (if any) would need to share the deployment.
- Either way, link the page from the Gum docs or README.
