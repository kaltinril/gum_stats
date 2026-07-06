"""
Single source of truth for all tracked GitHub repositories.
To add a new library, append a dict to the ALL_REPOS list below.
Both getCompetitorCounts.py and chartit.py import from this file.
"""

ALL_REPOS = [
    {"owner": "vchelaru", "repo": "Gum", "alias": "gum", "display_name": "Gum", "excluded_from_chart": False},
    {"owner": "RonenNess", "repo": "GeonBit.UI", "alias": "geonbit", "display_name": "GeonBit.UI", "excluded_from_chart": False},
    {"owner": "rds1983", "repo": "Myra", "alias": "myra", "display_name": "Myra", "excluded_from_chart": False},
    {"owner": "ocornut", "repo": "imgui", "alias": "imgui", "display_name": "ImGui", "excluded_from_chart": True},
    {"owner": "Ellpeck", "repo": "MLEM", "alias": "mlem.ui", "display_name": "MLEM", "excluded_from_chart": False},
    {"owner": "MonoGo-Engine", "repo": "MonoGo", "alias": "MonoGo", "display_name": "MonoGo", "excluded_from_chart": False},
    # New libraries
    {"owner": "prime31", "repo": "Nez", "alias": "nez", "display_name": "Nez", "excluded_from_chart": True},
    {"owner": "Apostolique", "repo": "Apos.Gui", "alias": "apos.gui", "display_name": "Apos.Gui", "excluded_from_chart": False},
    {"owner": "RonenNess", "repo": "Iguina", "alias": "iguina", "display_name": "Iguina", "excluded_from_chart": False},
    {"owner": "Videogamers0", "repo": "MGUI", "alias": "mgui", "display_name": "MGUI", "excluded_from_chart": False},
]

METRICS = ["STARS", "SUBS", "FORKS", "ISSUES"]

# Validate alias uniqueness
_aliases = [r["alias"] for r in ALL_REPOS]
assert len(_aliases) == len(set(_aliases)), "Duplicate alias detected in repos_config!"


def get_column_names():
    """Return full list of expected CSV column names (excluding DATE)."""
    cols = []
    for r in ALL_REPOS:
        for m in METRICS:
            cols.append(f"{m}_{r['alias']}")
    return cols


def get_chart_repositories():
    """Return dict of {display_name: alias} for repos not excluded from chart."""
    return {
        r["display_name"]: r["alias"]
        for r in ALL_REPOS
        if not r["excluded_from_chart"]
    }
