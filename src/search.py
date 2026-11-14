from typing import Dict, List

# A title match always outranks any combination of the other fields.
FIELD_WEIGHTS = (("title", 10), ("tags", 4), ("category", 3), ("description", 1))


def split_terms(query: str) -> List[str]:
    """Lowercase search words. Raises ValueError for an empty search."""
    terms = [] if query is None else str(query).casefold().split()

    if not terms:
        raise ValueError("Enter something to search for.")

    return terms


def search_tasks(tasks, query: str) -> List[Dict]:
    """Tasks matching every word in the query, best matches first.

    Words are matched anywhere (not only at the start of a word) in the
    title, tags, category and description, ignoring case. A match in the
    title counts most, then tags and category, then the description. Each
    result is {"task", "fields", "score"}; ties go to the newest task.
    """
    terms = split_terms(query)
    results = []

    for task in tasks:
        haystacks = {
            "title": task.title.casefold(),
            "tags": " ".join(task.tags).casefold(),
            "category": task.category.casefold(),
            "description": (task.description or "").casefold(),
        }
        score = 0
        matched = set()
        found_all = True

        for term in terms:
            term_found = False

            for field, weight in FIELD_WEIGHTS:
                if term in haystacks[field]:
                    term_found = True
                    matched.add(field)
                    score += weight

            if not term_found:
                found_all = False
                break

        if found_all:
            ordered = [field for field, _ in FIELD_WEIGHTS if field in matched]
            results.append({"task": task, "fields": ordered, "score": score})

    results.sort(key=lambda item: (-item["score"], -item["task"].task_id))
    return results


JOURNAL_FIELDS = ("achievements", "challenges", "next_steps")


def _snippet(text: str, term: str, length: int = 60) -> str:
    """A short excerpt of `text` around the first occurrence of `term`."""
    flat = " ".join(text.split())
    position = flat.casefold().find(term)
    start = max(position - 20, 0) if position >= 0 else 0
    excerpt = flat[start:start + length]

    return ("..." if start > 0 else "") + excerpt + ("..." if start + length < len(flat) else "")


def search_journal(entries, query: str) -> List[Dict]:
    """Journal entries matching every word, newest first.

    `entries` are dictionaries with `entry_date`, `achievements`,
    `challenges` and `next_steps`. Each result is {"entry", "fields",
    "snippet"}, where the snippet is an excerpt around the first match.
    """
    terms = split_terms(query)
    results = []

    for entry in entries:
        lowered = {
            field: (entry.get(field) or "").casefold() for field in JOURNAL_FIELDS
        }

        if not all(any(term in text for text in lowered.values()) for term in terms):
            continue

        fields = [
            field for field in JOURNAL_FIELDS
            if any(term in lowered[field] for term in terms)
        ]
        first_term = next(term for term in terms if term in lowered[fields[0]])
        results.append({
            "entry": entry,
            "fields": fields,
            "snippet": _snippet(entry.get(fields[0]) or "", first_term),
        })

    results.sort(key=lambda item: item["entry"]["entry_date"], reverse=True)
    return results
