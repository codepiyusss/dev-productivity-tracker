# Database

SQLite is used for local persistent storage.

## Tags

Tags are stored in a `task_tags` table (`task_id`, `tag`) with a composite
primary key and `ON DELETE CASCADE`. The table is created automatically on
startup (`CREATE TABLE IF NOT EXISTS`), so existing databases upgrade without
touching the `tasks` table or losing data. Tags are normalized to lowercase.

## CLI usage

```
python -m src.main add "Ship release" --tags work,urgent
python -m src.main tag add 1 backend
python -m src.main tag remove 1 urgent
python -m src.main tag list
python -m src.main list --tag work --tag backend
```

## Completion times and goals

`tasks.completed_at` stores when a task was completed. It is added to existing
databases automatically (`ALTER TABLE ... ADD COLUMN`); old rows keep `NULL`
and are not counted toward goals. Reopening a task clears the value.

Goals live in a `goals` table (`period` primary key, `target` greater than 0)
with one row each for `daily` and `weekly`. Weeks run Monday to Sunday.

## Time tracking

`time_entries` stores one row per work session (`entry_id`, `task_id`,
`started_at`, `ended_at`). A row with `ended_at IS NULL` is the running timer.
A partial unique index allows at most one such row, so two timers can never
run at once, even from two terminals. Entries are removed automatically when
their task is deleted (`ON DELETE CASCADE`). Each entry counts toward the day
it started. The table is created with `CREATE TABLE IF NOT EXISTS`, so existing
databases upgrade without data loss.

## Recurring tasks

`tasks.recurrence` holds the repeat rule (`daily`, `weekly`, `monthly`) or `NULL`
for tasks that do not repeat. The column is added to existing databases
automatically. When a repeating task is completed through `complete`, a new task
is created with the next due date: the schedule moves forward from the old due
date one step at a time until it is after today, so finishing early gives the next
regular date and finishing very late does not create overdue copies. Monthly
repeats clamp to the end of short months (Jan 31 becomes Feb 28), and the shorter
day carries forward. Reopening a completed task does not delete an occurrence that
was already created.

## Backups

`src/backup.py` works on database files, not on the live connection. Backups are
written to a `backups` folder next to the database (override with `--dir`) and are
named `productivity-YYYYMMDD-HHMMSS[-label].db`.

- **Creating:** SQLite's backup API takes a consistent snapshot even while the
  database is in use. The snapshot is built in a temporary file, verified with
  `PRAGMA integrity_check` and `PRAGMA foreign_key_check`, and then moved into place.
  A backup that fails verification is deleted, so a backup file that exists can be restored.
- **Restoring:** the backup is verified first (a bad backup changes nothing), the
  current database is saved as a `pre-restore` backup, and the backup is copied
  beside the database, verified again, and swapped in with a single rename. Backups
  made by older versions are upgraded automatically the next time the database is opened.
- **Pruning:** keeps the newest N backups. Files that are not named like backups, and
  `pre-restore` safety copies, are never deleted.

Backups contain all of your data (tasks, time entries, goals and journal), so keep
them somewhere private.
