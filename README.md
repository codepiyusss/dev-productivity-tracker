# Dev Productivity Tracker

A fast command-line tool for tracking your work. Tasks, time, goals, streaks and a
daily journal all live in one SQLite file on your own machine. There is no account,
no server and no internet connection needed.

```text
$ python -m src.main list
[3] Read Python book | low | learning | Pending
[2] Fix login bug | medium | work | Pending | #bugfix
[1] Write project docs | high | work | Pending | due 2026-12-01 | #docs #work

$ python -m src.main complete 2
Task completed.
Daily goal: [###-------] 1/3 (33.3%) - 2 to go
Streak: 1 day. Keep it going tomorrow!
```

## What it does

| Area | What you can do |
|---|---|
| **Tasks** | Add, edit, show, complete, reopen and delete tasks with priority, category, description and due date |
| **Tags and search** | Give tasks several tags, then search, filter and sort your list |
| **Reminders** | See overdue tasks and tasks due soon |
| **Time tracking** | Start and stop a timer, log time by hand, and see totals by day, category and task |
| **Goals** | Set a daily and a weekly target and watch your progress |
| **Streaks** | Track how many days in a row you complete something |
| **Analytics** | Completion rates by priority, category and tag, how long tasks have waited, and short insights |
| **Journal** | Write a daily entry (achievements, challenges, next steps), then search it by text or date range |
| **Import and export** | Export tasks to CSV or JSON, and import tasks from CSV |

Your data stays local. Existing databases are upgraded automatically when you update
the tool, and no data is lost.

## Getting started

You need Python 3. The project is developed and tested on Python 3.12.

```bash
git clone https://github.com/codepiyusss/dev-productivity-tracker.git
cd dev-productivity-tracker

python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate

pip install -r requirements.txt
```

Run every command from the project folder:

```bash
python -m src.main add "Write project docs" --priority high --due-date 2026-12-01 --tags docs,work
python -m src.main list
python -m src.main --help
```

Add `--help` after any command to see its options, for example
`python -m src.main timer --help`.

## Using it

Every example starts with `python -m src.main`. It is shortened to `tracker` below
for readability.

### Tasks

```bash
tracker add "Fix login bug" --priority medium --category work --tags bugfix
tracker list                                  # newest first
tracker list --status pending --sort due_date --ascending
tracker list --search login --tag work        # --tag can be repeated
tracker show 2                                # full details of one task
tracker edit 2 --priority high --due-date 2026-12-05
tracker edit 2 --clear-due-date
tracker complete 2
tracker reopen 2
tracker delete 2                              # asks first; add --yes to skip
```

- Priorities are `low`, `medium` or `high`.
- Due dates must be real `YYYY-MM-DD` dates. Tasks past their date show `(OVERDUE)`.

### Tags

```bash
tracker add "Write docs" --tags docs,work
tracker tag add 1 urgent
tracker tag remove 1 urgent
tracker tag list                              # every tag with its task count
tracker list --tag docs
```

Tags are lowercase, so `Work` and `work` are the same tag.

### Reminders

```bash
tracker reminders                             # overdue and due within 7 days
tracker reminders --days 14
```

### Time tracking

```bash
tracker timer start 1                         # only one timer runs at a time
tracker timer status
tracker timer stop
tracker timer log 2 1h30m --date 2026-11-08   # add time you did not track live
tracker timer list --days 7
tracker timer summary                         # by day, category and task
tracker timer delete 4                        # remove a mistaken entry
```

- Durations can be written as `45`, `45m`, `1h30m`, `1.5h` or `1:30`. A bare number means minutes.
- A timer that has been running for more than 12 hours is flagged, in case you forgot it.
- Completing a task stops its timer automatically.

### Goals and streaks

```bash
tracker goal set daily 3                      # complete 3 tasks per day
tracker goal set weekly 15                    # weeks run Monday to Sunday
tracker goal show
tracker goal clear weekly
tracker streak
```

```text
Current streak: 5 days (completed a task today)
Longest streak: 9 days (2026-10-01 to 2026-10-09)
Active days: 21
Last 14 days: [--##-#####--####] (oldest to today)
```

A streak counts days with at least one completed task. It stays alive until the end of
the next day, so it does not reset just because you have not finished anything yet today.
In the activity strip, `#` is a day with a completed task and `-` is a day without.

### Analytics and reports

```bash
tracker stats                                 # quick overview
tracker stats --detailed                      # full breakdown with insights
tracker stats --json                          # machine-readable
tracker report --output my_report.txt         # save the detailed report to a file
```

The detailed view includes completion rates by priority and tag, overdue and upcoming
tasks, goal progress, streaks, time tracked in the last 7 days, and a few plain-language
insights.

### Journal

```bash
tracker journal add --achievements "Shipped time tracking" --challenges "Edge cases" --next-steps "Write docs"
tracker journal list --limit 5
tracker journal list --search tracking --from-date 2026-11-01 --to-date 2026-11-30
tracker journal show 2026-11-08
tracker journal update 2026-11-08 --achievements "Shipped and tested time tracking"
tracker journal delete 2026-11-08
```

### Import and export

```bash
tracker export --format csv --output exports/tasks.csv
tracker export --format json --status pending --tag work
tracker export --include-time                 # adds a time_spent_seconds column

tracker import tasks.csv --dry-run            # check the file without saving
tracker import tasks.csv
```

- Only a `title` column is required to import. Optional columns are `description`,
  `priority`, `category`, `due_date`, `completed` (yes/no) and `tags` (separated by `;` or `,`).
- Files made by `export` can be imported again.
- Invalid rows are skipped and reported by line number. Tasks that already exist
  (same title, category and due date) are skipped unless you pass `--allow-duplicates`.

## Where your data is stored

Everything is saved in `data/productivity.db`, created the first time you run a command.
The path is relative to the folder you run the tool from, so run it from the project
folder. To use a different file, put `--db` before the command:

```bash
tracker --db work.db list
```

Commands exit with code 0 on success and 1 on failure (for example, a task that does not
exist), so they can be used in scripts.

## Running the tests

```bash
python -m pytest
```

## Project layout

```text
src/
  main.py          command-line interface
  models/task.py   the Task data model
  database.py      SQLite storage and automatic upgrades
  tasks.py         task management
  task_filters.py  search, filter and sort
  analytics.py     statistics and insights
  reports.py       text reports
  goals.py         daily and weekly goals
  streaks.py       completion streaks
  timetracking.py  timers and time summaries
  journal.py       daily journal
  exporter.py      CSV and JSON export
  importer.py      CSV import
  utils.py         validation and formatting helpers
tests/             pytest test suite
docs/              architecture, database, features, installation, testing
```

More detail is in the [`docs/`](docs/) folder, and the history of changes is in
[`CHANGELOG.md`](CHANGELOG.md).

## Contributing

Issues and pull requests are welcome. Please run `python -m pytest` before opening a pull
request, and add tests for new behaviour.
