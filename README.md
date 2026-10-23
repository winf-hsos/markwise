# Markwise

A desktop app for paper exams: keep a bank of questions, build exams from it, read the scanned answer sheets and turn them into grades. Multiple-choice answers are read automatically; free-text answers are marked by hand on paper, with the points ticked in a box strip that the scan reads as well.

Markwise runs natively on Windows, needs neither Linux nor LaTeX, and is meant to be used by examiners without any technical background. Agents (for example an AI assistant that drafts questions) work with the same data through a command-line interface, and later through a local HTTP interface.

> **Status (October 2026): phase 1 of the [plan](docs/concept.md#plan).** What works today is managing question pools from the command line (creating, listing, checking, importing and deleting questions, setting up modules) and the app window for setting up modules (creating a module with its question pool, opening module folders, adding pools, switching between modules) and for working with questions (search, filters, a preview with the check's findings, creating and editing questions with a live preview and checks while typing). Releasing and retiring questions, building exams, printing, scanning and grading follow; [what is not there yet](#not-there-yet) lists them with their dates. This guide grows with every step, so it always describes what Markwise can do at the time.

## Contents

- [Installation](#installation)
- [Opening the app](#opening-the-app)
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

## Opening the app

```
markwise app
```

opens Markwise in its own window (it uses the WebView2 runtime that is part of Windows 11). To get an entry in the Start menu, which you can also pin to the taskbar, run once:

```
markwise shortcut
```

The entry opens the window without a console.

### Setting up a module

On the **Modules** page, **New module** asks for:

- the **name** and a **short name** (Markwise suggests one from the capitalised words of the name; type your own if you prefer, for example `DuP`),
- the **module folder**: the folder where you keep the module's documents anyway, because the exams with names, scans and grades will go there later. It may already contain other files; Markwise only adds `module.toml`. A folder that does not exist yet is created.
- the **question pool**, in one of three ways:
  - **New pool**: an empty pool in a folder of its own, with a name and the languages of its questions (German, English or both).
  - **Existing pool**: a folder that already holds a `pool.toml`, for example a pool a colleague shared with you.
  - **Import an earlier pool**: the `pool.toml` of a question bank in the earlier YAML format, and a folder for the new pool. The questions are copied and converted; the earlier pool stays unchanged (see [Importing an existing question bank](#importing-an-existing-question-bank)).

**Browse …** next to each path opens the Windows folder dialog; you can also paste a path. Below the field Markwise says what the folder holds, for example that it will be created or already holds a pool. If something is missing or does not fit, the dialog says what to change, and nothing is created until everything fits.

The new module becomes the **current module**, shown in the top bar. Every module in the list shows its folder and its pools with the number of questions; pointing at a pool shows **Show in Explorer** and **Detach pool** (detaching leaves the pool's questions untouched). The **⋯** menu of a module offers **Add pool** (the same three ways as above), **Show in Explorer** and **Remove from list**, which only removes the entry from the list and leaves the folder as it is.

**Open folder** adds a module folder that already has a `module.toml`, for example after copying it from another computer. If the folder turns out to be a question pool, Markwise offers to create a new module with that pool instead.

To switch modules, choose one in the menu of the top bar or click **Make this the current module** in the list.

### Browsing questions

The **Questions** page lists every question in the pools of the current module. The line under the title names the pools.

- **Search** looks for every word you type in the question text, the options, the feedback and the identifier, in all languages of the pool. `led farbe` finds questions that mention both.
- **Filters** narrow the list by pool (if the module has several), concept, level, status, type, use (practice or exam) and findings of the check (with errors, with warnings, without findings). The line below says how many questions are shown out of how many; **Reset filters** clears them.
- A small symbol in front of each identifier shows the type: a filled circle for single choice, a ticked box for multiple choice, lines for free text.
- A question with errors carries a red mark in the list, one with warnings a yellow one; questions meant for exams are marked **Exam**, or **Practice and exam** if they serve both.
- **Sort by** orders the list by identifier, concept, last change (newest first), level, status, or findings (questions with errors first). Markwise remembers the order on this computer.
- When a filter or the search drops the question shown on the right, the preview empties; undoing the filter brings it back.
- **Click** a question, or move through the list with the **arrow keys**, to see it on the right as it reads on paper: the text, any code and figure, the options with the correct ones ticked and the feedback below each, then the check's findings and the metadata (concept, level, exam variants of a practice question, coverage, pool, when the file was last changed, file). **DE** and **EN** switch the language of the preview.
- **Edit** opens the question in the editor (see below). **Open in editor** opens its file in the program Windows uses for YAML files instead; after saving there, click **Reload**.

### Creating and editing questions

**New question** on the Questions page asks for the pool (if the module has several), the concept and the type; with a concept filter set, that concept is already chosen. **New concept …** in the concept list asks for a name and a short description in plain words; Markwise makes the concept's identifier from the name (shown below the field). Markwise creates the question with the next free identifier and opens it in the editor.

### Releasing, exam variants, retiring

A question is written as a **draft**. When an examiner has read it and agrees, **Release** in the head of the preview notes their name in `reviewed_by` and makes the question **reviewed**; a second examiner can **Release as well**, so that both names stand there, as § 5 (3) c of the general examination regulations asks for two examiners. A question with errors cannot be released. Changing the content of a reviewed question makes it a draft again.

The **⋯** menu next to **Edit** holds the other steps:

- **Create exam variant** (for practice questions): a new exam-only question in the same concept, noting the practice question in `variant_of`. It starts as a copy and opens in the editor, so that you can change its surface while keeping the learning goal and level.
- **Withdraw my release**: takes your name off; without any release left, the question is a draft again.
- **Retire**: the question and its file stay, but it will not appear in any new exam, and its identifier is never given again. The list shows it struck through; **Take back** makes it a draft again.
- **Delete** (drafts only): removes the file after a confirmation. Everything else is retired instead.

A tick in the list marks reviewed questions.

### Concepts

Questions are grouped by concept, and the **Concepts** page in the side menu is where you look after them. On the left it lists the concepts of the current module's pools with their names, short descriptions and number of questions; a search narrows the list, and if the module has several pools, a filter shows the concepts of one pool (**New concept** then adds to that pool). Click a concept to see it on the right:

- its **name** and **short description**, which you can change and **Save** (the identifier below them, made from the name, names the folder of the questions and stays the same);
- an overview of its questions: how many there are by level, type and status, how many are meant for practice and for exams, how many practice questions still lack an exam variant, and how many have errors or warnings;
- **Show questions** opens the question list filtered to the concept, and **New question** starts a question in it;
- a concept without questions can be **deleted**; one with questions cannot, so that nothing is lost.

**New concept** at the top asks for the pool (if the module has several), the name and the short description. Everywhere else, in the filter, the list and the preview, Markwise shows the names.

An imported question bank takes the concept names from the titles of its website's concept pages and the short descriptions from their subtitles or the first sentence of their summaries. From the command line:

```
markwise concept list "D:\Teaching\Statistics\pool"
markwise concept add "D:\Teaching\Statistics\pool" "Korrelation und Regression" --description "Zusammenhänge zwischen zwei Merkmalen"
markwise concept edit "D:\Teaching\Statistics\pool" regression --name "Lineare Regression"
```

The editor shows the form on the left and the question as it reads on paper on the right; the preview follows every keystroke.

- **Type** switches between single and multiple choice (a free-text question stays free text). **Level** is a choice of three. **Time to answer** offers 15 s, 30 s, 45 s, 1 min, 2 min and 5 min, and **Other …** for any time in minutes and seconds; points are not set here but when an exam is built. **Use** has two switches, **Practice** and **Exam**, which can both be on; one of them always stays on. A question meant only for exams can name the practice question it is a **variant of**; an exam variant is never a practice question itself, because students would then know it.
- **Deutsch** and **English** switch the language of all texts. A yellow dot on a language means a text is still missing there.
- The **question text** grows with what you type. Below it, **Add** opens a menu of what a question can carry under its text, each added in a dialog of its own:
  - **Code**: a code block with syntax highlighting. Choose the language (Python, JavaScript, Java, C, C++, C#, SQL, R, Shell, JSON) or let Markwise detect it; **Tab** indents by four spaces.
  - **Figures**: the pool's images as small previews. Click one or several; the numbers on them show the order. With two or more, choose the **layout**: one below the other, side by side, or in 2 or 3 columns. **Add image from file …** copies a PNG, SVG or JPEG file into the pool's `images` folder, under a name made from the file name, and selects it.
  - **Formula** is listed as coming.

  What a question carries appears as a small card below the text, with **Edit** or **Change** and **Remove**.
- Each **option** has a box on the left that marks it correct (for single choice, marking one unmarks the others), its text, and below it the feedback that explains why it is right or wrong. **Add option** adds one, **–** removes one.
- **More details** holds where the material is taught and the misconception the question targets.
- The **check** runs while you type; its findings appear under the preview in the language of the interface.

**Save** (or **Ctrl+S**) writes only what you changed: every other line of the file stays as it was, including comments and fields Markwise does not know. **Discard** returns to the saved state, **Back to the list** asks before it drops unsaved changes. If someone else saved the same file in the meantime, for example a colleague in a shared folder, Markwise says so and lets you either load their version or save yours over it.

A **reviewed** question goes back to **draft** when you change its content, because it then needs a new release. Every question notes who created it and who changed it last, with the date, using your name from the settings or else your Windows user name; the preview shows both.

### Markwise remembers where you were

Every page keeps its state per module when you leave it: on **Questions** the search, filters, sort order, chosen question, scroll position and an open editor, including changes you have not saved yet; on **Concepts** the search, pool filter, chosen concept and scroll position. After a restart Markwise opens on the page you used last, with its filters and selection. Unsaved changes are kept only while the window is open; when you come back to them and the file was changed elsewhere in the meantime, saving reports the conflict as usual.

### Settings

### Settings

**Settings** switches the interface between German and English, chooses the **colour scheme** (Markwise green, or Hochschule Osnabrück with its blue #009ee3; green for correct, red for errors and yellow for warnings stay the same in every scheme) and stores your name, which Markwise notes on questions you create, change or release (without a name, it takes your Windows user name). **Ctrl+B** collapses and expands the side menu. Your settings and the list of modules live in `%APPDATA%\Markwise\settings.toml`, on your computer only and never in a pool or module folder.

When the interface is German, new modules file their exams under `01 - Semester\<semester>\Klausur\`, otherwise under `…\Exam\`; `exam_path` in `module.toml` changes that.

**Exams** shows what will be there and when.

## The four things Markwise works with

| What | Where it lives | Contains |
|---|---|---|
| **Question pool** | a folder of its own, for example next to the teaching material | `pool.toml` with the pool's settings and one YAML file per question, sorted into one folder per concept. No personal data, so a pool can be shared with colleagues. |
| **Question** | `questions/<concept>/<id>.yaml` in a pool | the question text in every language of the pool, the options with feedback, the type, level, status, and whether it is meant for practice, for exams, or both |
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
markwise question list "D:\Teaching\Statistics\pool" --use exam          # questions meant for exams (also those for both)
markwise question list "D:\Modules\Statistics 1" --search "slope line"   # all pools of a module, searched
markwise question list "D:\Teaching\Statistics\pool" --findings errors     # questions the check rejects
markwise question show "D:\Teaching\Statistics\pool" r-001
```

Single fields can also be changed from the command line, with the same rules as in the window (only what changes is written; a reviewed question goes back to draft):

```
markwise question set "D:\Teaching\Statistics\pool" r-001 level apply
markwise question set "D:\Teaching\Statistics\pool" r-001 stem.en "What does the slope tell you?"
markwise question set "D:\Teaching\Statistics\pool" r-001 options.b.correct true
```

The command prints the check's findings for the question afterwards and ends with exit code 1 if there are errors.

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

The import creates the pool if it does not exist yet, converts every question, copies the images and keeps fields it does not know. Concepts get their names and short descriptions from the website's concept pages, where the earlier `pool.toml` points to them. The import reports how many questions it **created** and which concepts it **named**.

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
| `markwise question list <pool or module> [--search] [--concept] [--status] [--type] [--level] [--use practice\|exam] [--public yes\|no] [--findings errors\|warnings\|none]` | list questions, searched and filtered; a module folder lists all its pools |
| `markwise question show <pool> <id>` | print a question file |
| `markwise question release <pool> <id> [--by <name>]` | release a question as examiner; a second examiner adds their name |
| `markwise question withdraw <pool> <id> [--by <name>]` | take back your release |
| `markwise question variant <pool> <id> [--by <name>]` | create an exam variant of a practice question, as a copy to vary |
| `markwise question retire <pool> <id>` / `restore` | take a question out of new exams / back in, as a draft |
| `markwise question set <pool> <id> <field> <value>` | change one field by a dotted path (`level`, `stem.de`, `options.b.correct`); `true`, `false` and numbers are understood |
| `markwise question delete <pool> <id> --yes [--used-in-exam]` | delete a draft, retire anything else |
| `markwise check <pool> [--notes]` | check every question of a pool |
| `markwise import <old pool.toml> <pool> [--update]` | import a question bank in the earlier format |
| `markwise concept list <pool>` | list the concepts with name, description and number of questions |
| `markwise concept add <pool> <name> [--description]` | add a concept; its identifier is made from the name |
| `markwise concept edit <pool> <id> [--name] [--description]` | rename or describe a concept; identifier and folder stay |
| `markwise concept delete <pool> <id>` | delete a concept that has no questions |
| `markwise module init <folder> --name <name> --short-name <short> --pool <pool>` | create a module |
| `markwise module show <folder>` | show a module's pools and exams |
| `markwise module add-pool <folder> <pool>` | let a module draw from another pool |
| `markwise module remove-pool <folder> <pool>` | detach a pool from a module; the pool stays |
| `markwise app` | open the app window |
| `markwise shortcut [--folder <folder>]` | create the Start menu entry (or put it into another folder) |
| `markwise serve [--port 8765]` | serve the core on 127.0.0.1 for developing the interface in a browser |

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

The interface is a Svelte app in `frontend/`. Its build goes into `src/markwise/app/static/` and is part of the repository, so running Markwise needs no Node.js. To work on the interface (Node.js 20 or newer):

```
cd frontend
npm install
npm run dev          # http://localhost:5173, with markwise serve running in a second terminal
npm run build        # before committing: updates src/markwise/app/static
```

In the browser the interface reaches the core through `markwise serve`, which listens on 127.0.0.1 only and refuses requests that do not come from the interface. `markwise app --dev` opens the window on the development server instead of the build, and `--debug` allows the developer tools.

The concept is in [docs/concept.md](docs/concept.md), the question format in [docs/question-format.md](docs/question-format.md). A clickable prototype of the interface (look and feel only, sample data, no logic) is in [prototype/](prototype/): open `prototype/index.html` in a browser.

Developed at Hochschule Osnabrück by Prof. Dr. Nicolas Meseth.
