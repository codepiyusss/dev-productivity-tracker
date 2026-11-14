import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def requirement_names():
    names = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0].casefold())
    return names


def python_sources():
    files = list((ROOT / "src").rglob("*.py")) + list((ROOT / "tests").rglob("*.py"))
    return "\n".join(f.read_text(encoding="utf-8-sig") for f in files if f.name != "test_repo_hygiene.py")


def test_every_requirement_is_actually_used():
    sources = python_sources()

    for name in requirement_names():
        assert re.search(rf"^\s*(import|from)\s+{re.escape(name)}\b", sources, re.M), (
            f"{name} is in requirements.txt but never imported"
        )


def test_requirements_still_include_the_test_runner():
    assert "pytest" in requirement_names()


def test_gitignore_covers_personal_data_and_generated_files():
    lines = {
        line.strip() for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    }

    for pattern in ("*.db", "data/", "backups/", "productivity_report.txt",
                    ".pytest_cache/", ".venv/", "__pycache__/", "*.tmp"):
        assert pattern in lines, f"{pattern} should be ignored"


def test_ci_workflow_runs_the_tests_on_linux_and_windows():
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")

    assert "pull_request" in workflow
    assert "ubuntu-latest" in workflow and "windows-latest" in workflow
    assert "python -m pytest" in workflow
    assert "pip install -r requirements.txt" in workflow
