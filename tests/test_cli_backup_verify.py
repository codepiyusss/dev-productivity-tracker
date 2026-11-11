import pytest

from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "data" / "t.db"), *argv])

    _run("add", "Write docs")
    _run("backup", "create")
    _run.root = tmp_path
    _run.backup = next((tmp_path / "data" / "backups").iterdir())
    return _run


def test_verify_accepts_a_healthy_backup(run, capsys):
    capsys.readouterr()

    assert run("backup", "verify", str(run.backup)) == 0

    output = capsys.readouterr().out
    assert output.startswith("OK: ")
    assert "Contents: 1 tasks" in output


def test_verify_rejects_a_damaged_file(run, capsys):
    bad = run.root / "bad.db"
    bad.write_text("garbage" * 100)
    capsys.readouterr()

    assert run("backup", "verify", str(bad)) == 1

    output = capsys.readouterr().out
    assert "Problems found in" in output
    assert "Not a readable database" in output


def test_verify_reports_a_missing_file(run, capsys):
    capsys.readouterr()

    assert run("backup", "verify", str(run.root / "nope.db")) == 1

    assert "not found" in capsys.readouterr().out


def test_verify_does_not_change_the_file(run):
    before = run.backup.read_bytes()

    run("backup", "verify", str(run.backup))

    assert run.backup.read_bytes() == before
