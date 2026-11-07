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

## Goals

```
python -m src.main goal set daily 3
python -m src.main goal set weekly 15
python -m src.main goal show
python -m src.main goal clear weekly
```

Progress is shown after every `complete` and in `stats --detailed`.

## Streaks

```
python -m src.main streak             # current, longest and goal streaks
python -m src.main streak --days 30   # longer activity strip
python -m src.main streak --json      # machine-readable output
```

In the activity strip, `#` marks a day with a completed task and `-` a day without.
