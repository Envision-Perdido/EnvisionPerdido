"""I/O layer for Perdido Chamber scraper.

Handles saving events to JSON and CSV formats.
"""

import csv
import json
from pathlib import Path


def save_events_json(events: list[dict], path: str | Path) -> None:
    """Save events to a JSON file.

    Args:
        events: List of event dictionaries
        path: Output file path
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(events)} events to {path}")


def save_events_csv(events: list[dict], path: str | Path) -> None:
    """Save events to a CSV file.

    Flattens the category field (list -> semicolon-separated string).

    Args:
        events: List of event dictionaries
        path: Output file path
    """
    if not events:
        print("No events to save.")
        return

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    cols = [
        "title",
        "start",
        "end",
        "location",
        "url",
        "description",
        "uid",
        "category",
    ]

    def rowify(event):
        """Convert event dict to CSV row, flattening categories."""
        row = {col: event.get(col) for col in cols}
        if isinstance(row.get("category"), list):
            row["category"] = ";".join(filter(None, map(str, row["category"])))
        return row

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for event in events:
            writer.writerow(rowify(event))

    print(f"Saved {len(events)} events to {path}")
