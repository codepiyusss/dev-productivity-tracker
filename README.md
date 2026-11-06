# Dev Productivity Tracker

## Exporting tasks

```
python -m src.main export --format csv --output exports/tasks.csv
python -m src.main export --format json --status pending --tag work
```

CSV tags are stored in one column separated by `;`.

## Analytics

```
python -m src.main stats              # quick overview
python -m src.main stats --detailed   # full breakdown with insights
python -m src.main stats --json       # machine-readable output
python -m src.main report             # save the detailed report to a file
```
