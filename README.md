# Dev Productivity Tracker

## Exporting tasks

```
python -m src.main export --format csv --output exports/tasks.csv
python -m src.main export --format json --status pending --tag work
```

CSV tags are stored in one column separated by `;`.
