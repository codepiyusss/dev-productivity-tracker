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

## Command reference

| Command | Purpose |
|---|---|
| `add`, `list`, `show`, `edit`, `complete`, `reopen`, `delete` | Manage tasks |
| `tag add/remove/list` | Organize tasks with tags |
| `export`, `import` | Move tasks in and out as CSV or JSON |
| `goal set/show/clear`, `streak` | Targets and consistency |
| `stats`, `report`, `reminders` | Analytics and deadlines |
| `journal add/show/list/update/delete` | Daily journal |

```
python -m src.main edit 3 --priority high --due-date 2026-12-01
python -m src.main edit 3 --clear-due-date
python -m src.main show 3
python -m src.main delete 3          # asks first; use --yes to skip
python -m src.main --db work.db list # use another database file
```

Dates must be real `YYYY-MM-DD` dates. Commands exit with code 0 on success and 1 on
failure (for example, a task that does not exist), so they can be used in scripts.

## Time tracking

```
python -m src.main timer start 3          # start a timer on task 3
python -m src.main timer status
python -m src.main timer stop
python -m src.main timer log 3 1h30m --date 2026-11-08   # add untracked time
python -m src.main timer list --days 7
python -m src.main timer summary          # by day, category and task
python -m src.main timer delete 12        # remove a mistaken entry
python -m src.main export --include-time  # add time_spent_seconds to exports
```

Only one timer runs at a time. A timer running for more than 12 hours is flagged in
`timer status`. Completing a task stops its timer automatically.
