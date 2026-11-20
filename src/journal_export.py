import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List

FIELDS = ["entry_date", "achievements", "challenges", "next_steps", "created_at", "updated_at"]
SECTIONS = (
    ("achievements", "Achievements"),
    ("challenges", "Challenges"),
    ("next_steps", "Next steps"),
)
SUPPORTED_FORMATS = ("md", "json", "csv")


def _prepare(output_path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _oldest_first(entries: Iterable[Dict]) -> List[Dict]:
    return sorted(entries, key=lambda entry: entry["entry_date"])


def export_journal_json(entries: Iterable[Dict], output_path) -> str:
    """Write entries (oldest first) as a JSON list. Returns the file path."""
    path = _prepare(output_path)
    data = [{field: entry.get(field) for field in FIELDS} for entry in _oldest_first(entries)]

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    return str(path)


def export_journal_csv(entries: Iterable[Dict], output_path) -> str:
    """Write entries (oldest first) as CSV with a header row."""
    path = _prepare(output_path)

    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        for entry in _oldest_first(entries):
            writer.writerow({field: entry.get(field) or "" for field in FIELDS})

    return str(path)


def export_journal_markdown(entries: Iterable[Dict], output_path) -> str:
    """Write entries (oldest first) as a readable Markdown document.

    Sections an entry left empty are omitted.
    """
    path = _prepare(output_path)
    lines = ["# Productivity Journal", ""]
    ordered = _oldest_first(entries)

    if not ordered:
        lines.append("_No entries._")

    for entry in ordered:
        lines.append(f"## {entry['entry_date']}")
        lines.append("")
        for field, heading in SECTIONS:
            text = (entry.get(field) or "").strip()
            if text:
                lines.append(f"**{heading}**")
                lines.append("")
                lines.append(text)
                lines.append("")

    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines).rstrip("\n") + "\n")

    return str(path)


def export_journal(entries: Iterable[Dict], output_path, file_format: str) -> str:
    """Export in the requested format ('md', 'json' or 'csv')."""
    file_format = str(file_format).casefold()
    writers = {
        "md": export_journal_markdown,
        "json": export_journal_json,
        "csv": export_journal_csv,
    }

    if file_format not in writers:
        raise ValueError(
            f"Unsupported export format: {file_format}. "
            f"Choose from: {', '.join(SUPPORTED_FORMATS)}."
        )

    return writers[file_format](list(entries), output_path)
