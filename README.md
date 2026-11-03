# Dev Productivity Tracker

## Exporting tasks

```
python -m src.main export --format csv --output exports/tasks.csv
python -m src.main export --format json --status pending --tag work
```

CSV tags are stored in one column separated by `;`.

## Importing tasks

```
python -m src.main import tasks.csv --dry-run
python -m src.main import tasks.csv
```

Only a `title` column is required. Optional columns: `description`, `priority`,
`category`, `due_date` (YYYY-MM-DD), `completed` (yes/no), `tags` (separated by `;` or `,`).
Files produced by `export` can be imported back. Invalid rows are skipped and reported by
line number; tasks that already exist (same title, category and due date) are skipped unless
`--allow-duplicates` is given. Imported tasks receive new IDs and creation dates.
