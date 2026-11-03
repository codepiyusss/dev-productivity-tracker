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
