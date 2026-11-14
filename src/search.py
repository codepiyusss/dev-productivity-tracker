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
