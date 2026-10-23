# Markwise

A desktop app for paper exams: keep a bank of questions, build exams from it, read the scanned answer sheets and turn them into grades. Multiple-choice answers are read automatically; free-text answers are marked by hand on paper, with the points ticked in a box strip that the scan reads as well.

Markwise runs natively on Windows, needs neither Linux nor LaTeX, and is meant to be used by examiners without any technical background. Agents (for example an AI assistant that drafts questions) work with the same data through a command-line and local HTTP interface.

**Status:** phase 1 of the [plan](docs/concept.md#plan): the core package with the question format, import of existing question banks, checks and a command-line interface. The concept is in [docs/concept.md](docs/concept.md), the question format in [docs/question-format.md](docs/question-format.md). A clickable prototype of the interface (look and feel only, sample data, no logic) is in [prototype/](prototype/): open `prototype/index.html` in a browser.

## Development

```
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
```

The command-line program:

```
markwise pool init <folder> --name "My course"
markwise question new <pool> --concept <concept> --type single
markwise question list <pool> [--concept …] [--status …] [--public yes|no] [--json]
markwise check <pool> [--notes] [--json]
markwise import <earlier pool.toml> <pool folder> [--update]
markwise module init <folder> --name "…" --short-name … --pool <pool>
markwise module show <folder>
```

Tests use invented questions only; real exams, scans, participant lists and grades never go into this repository.

Developed at Hochschule Osnabrück by Prof. Dr. Nicolas Meseth.
