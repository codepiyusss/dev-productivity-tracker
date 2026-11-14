# Testing

Run tests with pytest.

## CLI tests

`main(argv)` returns an exit code, so CLI behaviour can be tested end to end:

```python
from src.main import main
main(["--db", str(tmp_path / "test.db"), "add", "Write docs"])
```

Use a temporary `--db` path in tests so the real database is never touched.

## Continuous integration

`.github/workflows/tests.yml` runs the full test suite on Linux and Windows, with
Python 3.12 and 3.13, for every push to `main` and every pull request. Windows is
included on purpose: it is stricter about open files, which has caught real bugs.
