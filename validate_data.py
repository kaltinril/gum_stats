"""
validate_data.py — sanity checks for data.csv, run by the GitHub Action before it
commits new data, so a bad run can never overwrite the history.

Checks:
  - the header starts with DATE and has no duplicate columns
  - every row has a valid YYYY-MM-DD date, dates are unique and ascending
  - every non-empty value is a non-negative integer
  - with --baseline OLD.csv: no rows were lost and no existing row was changed
    (new rows may only be appended; new columns may be added for new repos)

Usage:
    python validate_data.py
    python validate_data.py --baseline previous_data.csv

Exits non-zero (and prints why) on any failure.
"""

import argparse
import csv
import datetime
import sys

from starcounts import CSV_FILE


def load(path):
    with open(path, "r", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return [], []
    header = [c.strip() for c in rows[0]]
    data = [[c.strip() for c in r] for r in rows[1:] if any(c.strip() for c in r)]
    return header, data


def validate(path):
    errors = []
    header, rows = load(path)

    if not header or header[0] != "DATE":
        errors.append("Header must start with DATE")
    if len(header) != len(set(header)):
        errors.append("Header has duplicate columns")

    previous = None
    for i, row in enumerate(rows, start=2):
        if len(row) != len(header):
            errors.append(f"Line {i}: {len(row)} cells, header has {len(header)}")
        try:
            date = datetime.datetime.strptime(row[0], "%Y-%m-%d").date()
        except ValueError:
            errors.append(f"Line {i}: bad date {row[0]!r}")
            continue
        if previous is not None and date <= previous:
            errors.append(f"Line {i}: date {date} is not after {previous}")
        previous = date
        for col, value in zip(header[1:], row[1:]):
            if value and not value.isdigit():
                errors.append(f"Line {i}: {col} = {value!r} is not a non-negative integer")

    return header, rows, errors


def compare_to_baseline(header, rows, baseline_path):
    errors = []
    old_header, old_rows = load(baseline_path)

    missing_cols = [c for c in old_header if c not in header]
    if missing_cols:
        errors.append(f"Columns removed since baseline: {missing_cols}")
    if len(rows) < len(old_rows):
        errors.append(f"Row count dropped from {len(old_rows)} to {len(rows)}")

    new_by_date = {r[0]: dict(zip(header, r)) for r in rows}
    for old_row in old_rows:
        new_row = new_by_date.get(old_row[0])
        if new_row is None:
            errors.append(f"Row {old_row[0]} is missing")
            continue
        for col, old_value in zip(old_header, old_row):
            if col in new_row and new_row[col] != old_value:
                errors.append(f"Row {old_row[0]}: {col} changed {old_value!r} -> {new_row[col]!r}")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate data.csv.")
    parser.add_argument("--file", default=CSV_FILE)
    parser.add_argument("--baseline", help="Previous data.csv; new file may only append to it.")
    args = parser.parse_args()

    header, rows, errors = validate(args.file)
    if args.baseline:
        errors += compare_to_baseline(header, rows, args.baseline)

    if errors:
        print(f"{args.file} FAILED validation:")
        for e in errors[:50]:
            print(f"  - {e}")
        sys.exit(1)

    last = rows[-1][0] if rows else "none"
    print(f"{args.file} OK: {len(rows)} rows, {len(header) - 1} columns, latest {last}")


if __name__ == "__main__":
    main()
