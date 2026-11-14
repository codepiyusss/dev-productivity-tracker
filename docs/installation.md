# Installation

You need Python 3. The project is developed and tested on Python 3.12 and 3.13.

## Set up

```bash
git clone https://github.com/codepiyusss/dev-productivity-tracker.git
cd dev-productivity-tracker

python -m venv .venv
```

Activate the virtual environment:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (cmd): `.venv\Scripts\activate.bat`
- macOS / Linux: `source .venv/bin/activate`

Then install the dependencies:

```bash
python -m pip install -r requirements.txt
```

The only dependency is `pytest`, which is needed to run the tests. The tool itself
uses only the Python standard library.

## Check that it works

Run every command from the project folder:

```bash
python -m src.main --help
python -m src.main add "My first task" --priority high
python -m src.main list
python -m src.main doctor
```

`doctor` checks the database and reports anything that needs attention.

## Where data is stored

Your data is saved in `data/productivity.db` inside the project folder, created the
first time you run a command. Use `--db PATH` before the command to use a different
file. Backups go in `data/backups/`. These locations are ignored by git, so your
personal data is never committed.

## Run the tests

```bash
python -m pytest
```

The same tests run automatically on GitHub (Linux and Windows) for every pull request.
