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
