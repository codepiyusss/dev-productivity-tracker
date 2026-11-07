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
