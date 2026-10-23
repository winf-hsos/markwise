# Markwise

A desktop app for paper exams: keep a bank of questions, build exams from it, read the scanned answer sheets and turn them into grades. Multiple-choice answers are read automatically; free-text answers are marked by hand on paper, with the points ticked in a box strip that the scan reads as well.

Markwise runs natively on Windows, needs neither Linux nor LaTeX, and is meant to be used by examiners without any technical background. Agents (for example an AI assistant that drafts questions) work with the same data through a command-line interface, and later through a local HTTP interface.

> **Status (October 2026): phase 1 of the [plan](docs/concept.md#plan).** What works today is managing question pools from the command line: creating, listing, checking, importing and deleting questions, and setting up modules. The app window, building exams, printing, scanning and grading follow; [what is not there yet](#not-there-yet) lists them with their dates. This guide grows with every step, so it always describes what Markwise can do at the time.

## Contents

- [Installation](#installation)
- [The four things Markwise works with](#the-four-things-markwise-works-with)
- [Getting started in ten minutes](#getting-started-in-ten-minutes)
- [Writing and editing questions](#writing-and-editing-questions)
- [Checking a pool](#checking-a-pool)
- [Deleting and retiring questions](#deleting-and-retiring-questions)
- [Importing an existing question bank](#importing-an-existing-question-bank)
- [Modules](#modules)
- [Command reference](#command-reference)
- [Scan test](#scan-test)
- [Not there yet](#not-there-yet)
- [Privacy](#privacy)
- [Development](#development)

## Installation

From the end of November 2026 there will be an installer that sets Markwise up in your own Windows account, without administrator rights, with an entry in the Start menu. Until then Markwise runs from a copy of this repository with Python 3.12 or newer:

```
git clone https://github.com/winf-hsos/markwise.git C:\code\markwise
cd C:\code\markwise
python -m venv .venv
.venv\Scripts\python -m pip install -e .
```

After that the program is `C:\code\markwise\.venv\Scripts\markwise.exe`. Either call it with its full path, or activate the environment once per terminal, after which plain `markwise` works:

```
C:\code\markwise\.venv\Scripts\activate
markwise --version
```

In PowerShell the activation script is `.venv\Scripts\Activate.ps1`; if the execution policy blocks it, use the full path instead. All examples below assume an activated environment.

## The four things Markwise works with

| What | Where it lives | Contains |
|---|---|---|
| **Question pool** | a folder of its own, for example next to the teaching material | `pool.toml` with the pool's settings and one YAML file per question, sorted into one folder per concept. No personal data, so a pool can be shared with colleagues. |
| **Question** | `questions/<concept>/<id>.yaml` in a pool | the question text in every language of the pool, the options with feedback, the type, level, status, and whether it is a practice question or reserved for exams |
| **Module** | `module.toml` in the folder where you keep the module's exam documents | name, short name, examination regulations, and the pools the module draws from. One pool can serve several modules. |
| **Exam** | a folder of its own below the module folder (coming in phase 2) | the frozen questions, participants, printouts, scans and results |

A typical layout:

```
Teaching material\Statistics\pool\        question pool, shareable
  pool.toml
  questions\regression\r-001.yaml
  questions\regression\r-002.yaml
  images\scatter-plot.svg

Modules\Statistics 1\                     module folder, examiners only
  module.toml
  01 - Semester\2026-27 - WS\Exam\2027-02-05 - Exam\   an exam (phase 2)
```

## Getting started in ten minutes

**1. Create a pool.** Choose a folder and a name; the languages default to German and English.

```
markwise pool init "D:\Teaching\Statistics\pool" --name "Statistics"
```

To use only one language, pass `--languages de` (or `en`). Every question then needs its texts in exactly those languages.

**2. Create a question.** Give the concept it belongs to and the type: `single` (one correct option), `multiple` (one or more correct options) or `free_text`.

```
markwise question new "D:\Teaching\Statistics\pool" --concept regression --type single
```

Markwise answers with the new identifier and the file it wrote, for example `r-001 created: …\questions\regression\r-001.yaml`. The identifier starts with the initials of the concept (`regression` → `r`) or with the prefix the concept's questions already use, and counts up.

**3. Fill in the question.** Open the file in any text editor (Notepad works, Visual Studio Code is more comfortable) and fill in the empty texts. The next section shows a complete question.

**4. Check the pool.**

```
markwise check "D:\Teaching\Statistics\pool"
```

As long as the texts are empty, the check reports errors such as `question text missing in de, en`. Once everything is filled in, it reports `0 errors`.

**5. Set up the module** that will draw its exams from the pool:

```
markwise module init "D:\Modules\Statistics 1" --name "Statistics 1" --short-name ST1 --pool "D:\Teaching\Statistics\pool"
markwise module show "D:\Modules\Statistics 1"
```

## Writing and editing questions

A complete single-choice question:

```yaml
id: r-001
concept: regression
type: single              # single | multiple | free_text
level: understand         # remember | understand | apply
status: draft             # draft | reviewed | piloted | retired
public: true              # true: practice question; false: reserved for exams
stem:
  de: |
    Was gibt die Steigung einer Regressionsgeraden an?
  en: |
    What does the slope of a regression line tell you?
options:
  - id: a
    correct: true
    text: {de: "Um wie viel sich y im Mittel ändert, wenn x um eins steigt", en: "How much y changes on average when x rises by one"}
    feedback: {de: "Richtig.", en: "Correct."}
  - id: b
    correct: false
    text: {de: "Wie stark x und y zusammenhängen", en: "How strongly x and y are related"}
    feedback: {de: "Das ist der Korrelationskoeffizient.", en: "That is the correlation coefficient."}
  # … at least four options in total
```

Things worth knowing:

- **Texts over several lines** are written as a block after `|`, indented by two spaces more than the key, as in `stem` above. Short texts can stay in quotes on one line.
- **Multiple choice** marks every correct option with `correct: true`. One correct option is allowed, so the number of correct answers cannot be guessed.
- **Feedback** explains for every option why it is right or wrong. Students see it in practice mode; in exams it is never printed.
- **Exam variants** are questions with `public: false` and `variant_of: <id of the practice question>`: the same learning goal at the same level, but a different surface. Students who understood the practice question can solve the variant; students who only memorised it cannot.
- **Optional fields:** `image` (a file name from the pool's `images` folder), `code` (a code block below the question text), `coverage` (where the material is taught), `misconception`, `session`, `reviewed_by`.
- **Free-text questions** have no options but `points`, `half_points`, `lines` (size of the answer area), `expected` and `marking_notes`.
- **Fields Markwise does not know are kept.** You may add your own fields and comments; Markwise preserves them, and when it saves a file, the parts it did not change stay exactly as they were.
- **Working together:** if a colleague changed the same file in a shared folder after Markwise loaded it, Markwise refuses to save over it instead of silently overwriting their work.

The full format, including `pool.toml`, is in [docs/question-format.md](docs/question-format.md).

To find questions, use `question list` with filters, and `question show` to print one:

```
markwise question list "D:\Teaching\Statistics\pool" --concept regression --status draft
markwise question list "D:\Teaching\Statistics\pool" --public no          # exam variants only
markwise question show "D:\Teaching\Statistics\pool" r-001
```

## Checking a pool

`markwise check <pool>` reads every question and reports three kinds of findings:

| Kind | Meaning | Examples |
|---|---|---|
| **error** | the question cannot be used in an exam | a required field is missing; the identifier differs from the file name; a language is missing; fewer than four options; a single-choice question with two correct options; an image file is missing; an exam variant that is public or points to a missing question |
| **warning** | the question should be looked at | an option much longer than the others, which may give the answer away; feedback or an expected answer missing in a language |
| **note** | worth knowing | a practice question without an exam variant; a concept without questions |

Notes are counted but not listed unless you add `--notes`. Retired questions are checked only for their identifier, concept and the basic fields, not for their content. The command ends with exit code 1 if there is at least one error, so it can be used in scripts.

## Deleting and retiring questions

```
markwise question delete "D:\Teaching\Statistics\pool" r-002 --yes
```

Without `--yes` nothing happens. A **draft** that was never in an exam is deleted, and its identifier becomes free again. **Every other question is retired instead**: its status becomes `retired` and its file stays, so that past exams and their statistics remain traceable and the identifier is never given to another question. Add `--used-in-exam` to retire a draft that was used in an exam.

## Importing an existing question bank

Question banks in the earlier YAML format (a `pool.toml` with German keys such as `fragen`, `sprachen`, and questions with `konzept`, `niveau`, `frage`, `richtig`, `optionen`) are converted with:

```
markwise import "D:\Teaching\Statistics\pool.toml" "D:\Teaching\Statistics\markwise-pool"
```

The import creates the pool if it does not exist yet, converts every question, copies the images and keeps fields it does not know. It reports how many questions it **created**.

The import can be run again at any time, for example while the old question bank is still being edited. It never overwrites a question silently, and sorts every question into one of these groups:

| Group | Meaning | What happens |
|---|---|---|
| unchanged | the source file has not changed since the last import | nothing |
| changed in source | the source changed, the Markwise copy did not | listed; taken over only with `--update` |
| updated | as above, run with `--update` | the Markwise copy is replaced |
| conflicts | the question was also edited in Markwise, or a file with its identifier already existed | nothing; decide by hand |

The import remembers what it did in the file `.import.toml` inside the pool; leave it there.

## Modules

```
markwise module init <module folder> --name "<name>" --short-name <short name> --pool <pool> [--pool <another pool>]
markwise module show <module folder>
```

`module init` writes `module.toml` into the folder. The pools are stored relative to the module folder when they are on the same drive, so module and pools can move together. `module show` lists the module's pools and every exam found below the module folder. The examination regulations are `hsos-at-2026` (§ 5 (3) of the general examination regulations of Hochschule Osnabrück) for now. The place where new exams go is set by `exam_path` in `module.toml`; edit it to follow your own filing scheme.

## Command reference

Every command accepts `--json` and then answers in JSON instead of text, for scripts and agents. `markwise <command> --help` shows the options of a command.

| Command | What it does |
|---|---|
| `markwise pool init <folder> --name <name> [--languages de,en]` | create an empty pool |
| `markwise question new <pool> --concept <concept> [--type single\|multiple\|free_text]` | create a question from the template of its type |
| `markwise question list <pool> [--concept] [--status] [--type] [--level] [--public yes\|no]` | list questions, filtered |
| `markwise question show <pool> <id>` | print a question file |
| `markwise question delete <pool> <id> --yes [--used-in-exam]` | delete a draft, retire anything else |
| `markwise check <pool> [--notes]` | check every question of a pool |
| `markwise import <old pool.toml> <pool> [--update]` | import a question bank in the earlier format |
| `markwise module init <folder> --name <name> --short-name <short> --pool <pool>` | create a module |
| `markwise module show <folder>` | show a module's pools and exams |

Exit codes: `0` success, `1` the check found errors or the import found conflicts or problems, `2` wrong input (for example a folder without `pool.toml`, or a missing `--yes`).

## Scan test

Before the first exam, a test sheet shows whether Markwise reads the ticks from the university's copier reliably. The tool for it is a script in this repository:

```
python tools\scan_test.py make work\scan-test
```

writes two test sheets, a one-page instruction sheet in German that says how to fill in which box, and the layout. Print the sheets without scaling, fill them in as the instructions say, and scan them at the copier as a PDF at 300 dpi in greyscale. Then:

```
python tools\scan_test.py read <scan.pdf> work\scan-test\results
```

prints for each sheet whether the QR code, the orientation, the student number and every box were read as expected, and saves image crops of the uncertain boxes and a control image per page. The `work` folder is never part of the repository.

## Not there yet

| What | Planned for |
|---|---|
| App window with the question views (browse, search, edit with a live preview) | 13 Nov 2026 |
| Installer for a second computer | 27 Nov 2026 |
| Building exams: blueprint, variants, exam and answer booklets as PDF | 27 Nov 2026 |
| Reading scans, deciding doubtful cases, grading multiple-choice exams | early December 2026 |
| Item analysis, exports for the examinations office, inspection copies | 15 Jan 2027 |
| Free-text questions in exams, marking on screen, a language model for reviewing questions | after the first exams in early 2027 |

## Privacy

Markwise runs on your computer and sends nothing anywhere. Question pools contain no personal data. Names, student numbers, scans and grades exist only in the exam folders below a module folder, which belongs where only authorised people have access, as exam documents do today.

This repository holds code, documentation and invented test data only. Real exams, scans, participant lists and grades never go into it.

## Development

```
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
```

The concept is in [docs/concept.md](docs/concept.md), the question format in [docs/question-format.md](docs/question-format.md). A clickable prototype of the interface (look and feel only, sample data, no logic) is in [prototype/](prototype/): open `prototype/index.html` in a browser.

Developed at Hochschule Osnabrück by Prof. Dr. Nicolas Meseth.
