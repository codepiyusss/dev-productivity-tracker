# Testing

Run tests with pytest.

## CLI tests

`main(argv)` returns an exit code, so CLI behaviour can be tested end to end:

```python
from src.main import main
main(["--db", str(tmp_path / "test.db"), "add", "Write docs"])
```

Use a temporary `--db` path in tests so the real database is never touched.
