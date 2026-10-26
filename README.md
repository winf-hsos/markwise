# Markwise

A desktop app for paper exams: keep a bank of questions, build exams from it, read the scanned answer sheets and turn them into grades. Multiple-choice answers are read automatically; free-text answers are marked by hand on paper, with the points ticked in a box strip that the scan reads as well.

Markwise runs natively on Windows, needs neither Linux nor LaTeX, and is meant to be used by examiners without any technical background. Agents (for example an AI assistant that drafts questions) work with the same data through a command-line interface, and later through a local HTTP interface.

> **Status (October 2026): phase 1 of the [plan](docs/concept.md#plan).** What works today is managing question pools from the command line (creating, listing, checking, importing and deleting questions, setting up modules) and the app window for setting up modules (creating a module with its question pool, opening module folders, adding pools, switching between modules) and for working with questions (search, filters, a preview with the check's findings, creating and editing questions with a live preview and checks while typing). Releasing and retiring questions, exam variants that inherit the settings of their parent, the languages of a pool, and an optional check by a language model are there as well. Building exams, printing, scanning and grading follow; [what is not there yet](#not-there-yet) lists them with their dates. This guide grows with every step, so it always describes what Markwise can do at the time.

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

The new module becomes the **current module**, shown in the top bar. Every module in the list shows its folder and its pools with their languages (DE, EN) and number of questions; pointing at a pool shows **Languages**, **Show in Explorer** and **Detach pool** (detaching leaves the pool's questions untouched).

**Languages of a pool.** All questions of a pool are written in the same languages, so the language is set at the pool, not at the single question. **Languages** at the pool changes them. A language you add needs texts in every question afterwards; until they are written, the check reports them as missing, and Markwise tells you how many questions are affected. A language you drop is no longer shown or checked, but its texts stay in the files, so that nothing is lost if you add it again. The **⋯** menu of a module offers **Add pool** (the same three ways as above), **Show in Explorer** and **Remove from list**, which only removes the entry from the list and leaves the folder as it is.

**Open folder** adds a module folder that already has a `module.toml`, for example after copying it from another computer. If the folder turns out to be a question pool, Markwise offers to create a new module with that pool instead.

To switch modules, choose one in the menu of the top bar or click **Make this the current module** in the list.

### Browsing questions

The **Questions** page lists every question in the pools of the current module. The line under the title names the pools.

- **Search** looks for every word you type in the question text, the options, the feedback and the identifier, in all languages of the pool. `led farbe` finds questions that mention both.
- **Filters** narrow the list by pool (if the module has several), concept, level, status, type, use (practice or exam), findings of the check (with errors, with warnings, without findings) and time to answer (15 s to 5 min, another time, or none yet). Each filter opens a list of check boxes, so that you can choose several values: within one filter a question has to match one of them, across filters all of them, so *Understand* and *Apply* with *Draft* shows the drafts on either level. **Show all** in the list clears that filter. The line below says how many questions are shown out of how many; the crossed-out funnel next to it clears all filters at once.
- A small symbol in front of each identifier shows the type: a filled circle for single choice, a ticked box for multiple choice, lines for free text.
- A question with errors carries a red mark in the list, one with warnings a yellow one; questions meant for exams are marked **Exam**, or **Practice and exam** if they serve both.
- **Sort by** orders the list by identifier, concept, last change (newest first), level, status, or findings (questions with errors first). Markwise remembers the order on this computer.
- **Exam variants stand below the question they vary**, indented and in the order of their identifiers, whatever the list is sorted by; the parent shows how many variants it has. The small arrow to the left of a question with variants folds them away and shows them again; the button with the two arrows above the list does so for all questions at once. Markwise remembers what is folded. A variant whose parent is filtered out stands on its own with a note which question it varies.
- The **bar chart** symbol next to the number of questions shows or hides a short overview of the questions the filters and search let through: the total answering time (retired questions left out), how many have no time yet, how many exam variants there are and how many practice questions still lack one, and as bars how many there are of each type, level, status, use, finding and time to answer. It shows at a glance what is still missing. Clicking a bar adds its value to the filter, clicking it again takes it out. Markwise remembers on this computer whether the overview is open.
- When a filter or the search drops the question shown on the right, the preview empties; undoing the filter brings it back.
- **Click** a question, or move through the list with the **arrow keys**, to see it on the right as it reads on paper: the text, any code and figure, the options with the correct ones ticked and the feedback below each, then the check's findings and the metadata (concept, level, exam variants of a practice question, coverage, pool, when the file was last changed, file). **DE** and **EN** switch the language of the preview.
- **Edit** opens the question in the editor (see below). **Open in editor** opens its file in the program Windows uses for YAML files instead; after saving there, click **Reload**.

### Creating and editing questions

**New question** on the Questions page asks for the pool (if the module has several), the concept and the type; with a concept filter set, that concept is already chosen. **New concept …** in the concept list asks for a name and a short description in plain words; Markwise makes the concept's identifier from the name (shown below the field). Markwise creates the question with the next free identifier and opens it in the editor.

### Releasing, exam variants, retiring

A question is written as a **draft**. When an examiner has read it and agrees, **Release** in the head of the preview notes their name in `reviewed_by` and makes the question **reviewed**; a second examiner can **Release as well**, so that both names stand there, as § 5 (3) c of the general examination regulations asks for two examiners. A question with errors cannot be released. Changing the content of a reviewed question makes it a draft again.

The **⋯** menu next to **Edit** holds the other steps:

- **Create exam variant** (for practice questions, multiple choice and free text alike): a new exam-only question in the same concept, named after its parent with `-v1`, `-v2` and so on (`cp-005-v1`), and noting the parent in `variant_of`. Its texts start as a copy and open in the editor, so that you can change its surface while keeping the learning goal.

  A variant **inherits the settings of its parent**: type, level, time to answer, where the material is taught and the misconception, and for a free-text question the lines for the answer and whether half points are allowed. A free-text variant suits a calculation of the same kind with other numbers: change the numbers in the text and the expected answer, and everything else stays as in the parent. With the language model switched on, **Propose other numbers** in the editor of a free-text variant does that for you: the model chooses new numbers of a similar size, works out the result again and proposes the question text, expected answer and marking notes in every language of the pool. Its calculation is shown above the proposals, step by step, so that you can check it before applying anything. They are not copied but read from the parent, so a change there reaches every variant. In the editor these settings are marked **inherited from cp-005** and shown in a lighter style; choosing another value gives the variant its own, marked with **inherit again** to go back to the parent's. A variant is always meant for exams only, never for practice.
- **Withdraw my release**: takes your name off; without any release left, the question is a draft again.
- **Retire**: the question and its file stay, but it will not appear in any new exam, and its identifier is never given again. The list shows it struck through; **Take back** makes it a draft again.
- **Delete** (drafts only): removes the file after a confirmation. Everything else is retired instead. If the question has exam variants, Markwise asks what becomes of them: **Delete with its variants** deletes them as well (a released variant is retired instead), **Keep the variants** makes them exam questions of their own. They then get an ordinary identifier (the next free number of the concept, so `cp-005-v1` becomes, say, `cp-018`), and the settings they inherited so far are written into their own file.

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
- The tabs above the question text show the pool's languages (**Deutsch**, **English** or just one of them) and switch the language of all texts. A yellow dot on a language means a text is still missing there. **Change the pool's languages** on the right leads to the Modules page, where they are set.
- The **question text** grows with what you type. Texts are read as Markdown, as on the course websites: `**bold**`, `*italic*` and `` `code` `` work, a single line break is only a space, and a blank line starts a new paragraph; list items, code blocks and a line ending in two spaces keep their line breaks. Below it, **Add** opens a menu of what a question can carry under its text, each added in a dialog of its own:
  - **Code**: a code block with syntax highlighting. Choose the language (Python, JavaScript, Java, C, C++, C#, SQL, R, Shell, JSON) or let Markwise detect it; **Tab** indents by four spaces.
  - **Figures**: the pool's images as small previews. Click one or several; the numbers on them show the order. With two or more, choose the **layout**: one below the other, side by side, or in 2 or 3 columns. **Add image from file …** copies a PNG, SVG or JPEG file into the pool's `images` folder, under a name made from the file name, and selects it.
  - **Formula** is listed as coming.

  What a question carries appears as a small card below the text, with **Edit** or **Change** and **Remove**.
- Each **option** has a box on the left that marks it correct (for single choice, marking one unmarks the others), its text, and below it the feedback that explains why it is right or wrong. **Add option** adds one, **–** removes one.
- With the language model switched on (see [Help from a language model](#help-from-a-language-model)), **Check with AI** next to the language tabs hands the whole question to the model, with all its options and feedback in every language of the pool and its figures as images, and does everything in one go:
  - it checks the question as a whole: is the text clear without the options, does every option answer what the text asks, are the options clear and mutually exclusive, are exactly the marked options correct, does one stand out by length, detail or wording, are the wrong ones plausible, and does each feedback fit (for a free-text question: the question text, the expected answer and the marking notes); with figures, it also checks that text, options and figure fit together, for example that values and labels agree;
  - it gets the errors and warnings Markwise's own check shows for the question (an option that is much longer than the others, a missing text and so on) and says for each what to do about it, proposing the change itself where a text can fix it;
  - it reports a text written in the wrong language (German in the English field, say);
  - it judges whether the level (remember, understand, apply) fits what the question and its options demand, and if not, says why and proposes another level, which you apply like a text (for an exam variant this sets its own level instead of the inherited one);
  - it proposes better wordings and fills in what is missing: texts in a language that is still empty, missing feedback, an empty wrong option;
  - if the question has fewer options than the pool requires, it proposes as many new wrong options as are missing, each with feedback and the misconception it plays on.

  While the model works, which usually takes a few seconds, a veil with a spinner lies over the editor, so that the question does not change meanwhile. Then the proposals appear below the language tabs, under a bar with **Apply all** that stays in view while you scroll through them; **Apply missing only** next to it fills only the texts that are still empty. The findings come first, naming the part they concern. Below them each proposed text shows the old one struck through, marked **DE** or **EN** in a pool with several languages, with **Apply** for that part alone; a new wrong option has **Add**. The model never changes which options are correct; if a mark looks wrong, it says so. Nothing is saved until you save.
- **More details** holds where the material is taught and the misconception the question targets.
- The **check** runs while you type; its findings appear under the preview in the language of the interface.

**Save** (or **Ctrl+S**) writes only what you changed: every other line of the file stays as it was, including comments and fields Markwise does not know. **Discard** returns to the saved state, **Back to the list** asks before it drops unsaved changes. If someone else saved the same file in the meantime, for example a colleague in a shared folder, Markwise says so and lets you either load their version or save yours over it.

A **reviewed** question goes back to **draft** when you change its content, because it then needs a new release. Every question notes who created it and who changed it last, with the date, using your name from the settings or else your Windows user name; the preview shows both.

### Markwise remembers where you were

A page you have opened stays open in the background while you work on another one, so switching back finds it exactly as you left it: on **Questions** the search, filters, sort order, chosen question, scroll position and an open editor, including changes you have not saved yet; on **Concepts** the search, pool filter and chosen concept; on **Exams** the open exam, the search and filters for adding questions, and a question being edited.

Markwise reads the questions of a module once and keeps them in memory for all pages. After you save a question, it reads them again in the background, while every page keeps showing what it has, and then updates the list, the concept counts and the checks of an open exam. **Reload** on the Questions page reads them anew, for changes made outside Markwise. After a restart Markwise opens on the page you used last, with its filters and selection. Unsaved changes are kept only while the window is open; when you come back to them and the file was changed elsewhere in the meantime, saving reports the conflict as usual.

### Settings

**Settings** switches the interface between German and English and stores your name, which Markwise notes on questions you create, change or release (without a name, it takes your Windows user name). **Ctrl+B** collapses and expands the side menu. Your settings and the list of modules live in `%APPDATA%\Markwise\settings.toml`, on your computer only and never in a pool or module folder.

When the interface is German, new modules file their exams under `01 - Semester\<semester>\Klausur\`, otherwise under `…\Exam\`; `exam_path` in `module.toml` changes that.

### Help from a language model

Markwise can ask a language model from OpenAI to check question texts and to propose wrong answers. It is off until you switch it on, and it needs an API key of your own from OpenAI (platform.openai.com, under API keys; using it costs a little per request).

1. In **Settings**, under **Language model**, switch on **Help from a language model**.
2. Paste the key into **OpenAI API key** and click **Check and save**. Markwise asks OpenAI whether the key works and only then stores it, in the Windows credential store (Control Panel → Credential Manager → Windows Credentials, entry *Markwise*), never in a file. **Remove key** deletes it from there.

   If the environment variable `OPENAI_API_KEY` is set on your computer, Markwise offers that key first, showing only its beginning and end; **Use this one** checks it and stores it the same way.
3. Under **Model**, choose one of the models your key may use. Markwise suggests a small, inexpensive one; a larger model checks more thoroughly but takes longer and costs more. For questions with figures the model has to read images, as the models of the gpt-4o, gpt-4.1 and gpt-5 series do; Markwise sends figures as PNG images (SVG figures rendered first) of at most 1280 pixels, and says so if the chosen model cannot read them.

The editor then shows **Check with AI** (see [Creating and editing questions](#creating-and-editing-questions)), and for a free-text exam variant **Propose other numbers**. Only the text, figures, code, options and feedback (or, for a free-text question, the expected answer and marking notes) of the question you are working on are sent, and only when you press one of the buttons; never names, participants, scans or grades, and never who wrote the question. The model's answer is a suggestion: nothing changes until you apply it and save.

### Putting an exam together

The **Exams** page lists the exams of the current module, newest first. **New exam** asks for the title, the date, the language the exam is set in (one per exam) and where the answers go:

- **Answer sheet**: a separate sheet with the tick boxes of all questions; only the sheet is scanned.
- **Below the questions**: the boxes stand right below each question in the booklet; the whole booklet is scanned.

Markwise creates a folder for the exam in the module, in the semester the date falls in (`01 - Semester\2026-27 - WS\Klausur\2026-12-10 - Probeklausur` with a German interface), and writes the exam into `exam.toml` there.

Clicking an exam opens it. At the top are its title, date, language, answer form and examiners (names separated by commas), all changeable; a new title or date renames the exam's folder, and a date in another semester moves it there, with everything printed so far. Below them are the number of questions, the points and the total answering time. On the left, **Add questions** shows the questions of the module's pools with search and the usual filters, at first only those meant for exams; The plus puts a question at the end of the exam. Questions already in the exam have a light green background and a minus instead, which takes them out again. On the right the exam shows its questions in order as the printed booklet shows them, in the exam's language: number and points, what kind of answer is expected, the text, code and figures, the options with empty boxes, or the lines and point strip of a free-text question. Above each question are its points, suggested as one point per minute of answering time (rounded to half points, at least one) and changeable, and a minus to take it out. Every change is saved at once.

To change the order, grab a question by the dotted handle at the left of its bar. While you hold it, the exam folds into one line per question, so that even a long exam fits on the screen; the others make room where the question would land, and that place already shows the number it will have. Near the upper or lower edge the exam scrolls by itself. Letting go unfolds the exam with the question in view and briefly framed; Escape puts everything back. A question from the list on the left can be dragged the same way straight to its place in the exam. With the handle focused, the arrow keys move the question up and down. The folded exam lines up so that the grabbed question stays right under the pointer, also when the folded list is much shorter than the unfolded one.

An exam can be divided into **sections** such as "Teil A: Auswahlfragen" and "Teil B: Rechnen". **Section** at the top of the exam adds one: the first opens the exam, so that every question belongs to it; any further one comes at the end and is dragged by its handle to where it begins. A section runs from its heading to the next one, the questions are numbered straight through. Each heading shows its title and an optional note for the students, both editable in place, and the points and time of its questions; while a question is being dragged, the points of the sections follow it. The minus removes a heading, its questions stay. In the booklet, each section starts with its title, its points and its note, and never stands alone at the foot of a page; the cover lists the sections with their points, and the answer key has the headings too. A section without a title or without questions is pointed out, and an empty one is left out of the booklet. A question without an answering time is marked "no time". The eye next to a question, in the exam or among the questions to add, shows it in a dialog with its correct answers, feedback, findings and details, in the exam's language; **Edit** there opens the editor. The pencil next to a question, in the exam or among the questions to add, opens it in the editor right there; **Save and back to the exam** saves what was changed and returns to the exam as it was (if saving fails, for example because the file was changed elsewhere, the editor stays open with the message), and what was saved shows at once in the exam's list and checks.

The exam checks itself as you go and says what needs a look: a question meant for practice only, a question with errors or without a text in the exam's language, a retired one, two variants of the same practice question, points of zero, fewer than two examiners. An exam with errors cannot be printed.

### Printing an exam

**Print** at the top of an exam asks how many copies to make (as many as participants, plus a few spare) and typesets them as PDF into the folder `Druck` of the exam (`Print` for an exam in English):

- With an **answer sheet**: `Klausurheft.pdf`, the question booklet, which is not scanned and is the same for everyone; `Antwortbogen.pdf`, one numbered answer sheet per copy with the tick boxes of all multiple-choice questions and, on its own page, an answer area with lines and a grey point strip "for examiners only" for each free-text question.
- With the boxes **below the questions**: `Klausurheft mit Antworten.pdf`, one numbered booklet per copy, in which each multiple-choice question has its tick boxes right below it and each free-text question its lines and point strip.
- `Lösungsschlüssel.pdf`, the answer key: every question with its correct options, and the expected answer and marking notes of the free-text questions.
- `layout.json`: where every box landed on every page, for reading the scans later.

Every page that is scanned carries four corner marks and a QR code with the exam, the page and the number of the copy; the first page of each copy has the tick grid for the student number and a field for the name. Copies have an even number of pages, so that double-sided printing starts each copy on a new sheet. A choice question is never split across two pages. Each print replaces the last one in the folder; a PDF still open in another program stops it with a message. Once printed, the dialog lists the PDFs of the last print to open.

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

To use only one language, pass `--languages de` (or `en`). Every question then needs its texts in exactly those languages; `markwise pool languages` changes them later.

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
- **Exam variants** are questions with `public: false` and `variant_of: <id of the practice question>`: the same learning goal at the same level, but a different surface. Their file holds only their own texts and any setting they set themselves; type, level, time, coverage, misconception, lines and half points otherwise come from the parent. Students who understood the practice question can solve the variant; students who only memorised it cannot.
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

A draft with exam variants is only deleted together with a decision about them: `--variants delete` deletes or retires them as well, `--variants detach` makes them questions of their own with new identifiers and with the settings they inherited written into their files. Without `--variants` the command lists the variants and changes nothing.

## Importing an existing question bank

Question banks in the earlier YAML format (a `pool.toml` with German keys such as `fragen`, `sprachen`, and questions with `konzept`, `niveau`, `frage`, `richtig`, `optionen`) are converted with:

```
markwise import "D:\Teaching\Statistics\pool.toml" "D:\Teaching\Statistics\markwise-pool"
```

The import creates the pool if it does not exist yet, converts every question, copies the images and keeps fields it does not know. Texts wrapped by hand in the earlier files, so that they read well in an editor, become one line per paragraph; a pool imported before that can be tidied with `markwise pool unwrap <pool>` (it first counts, `--yes` rewrites), which keeps questions the import wrote and nobody changed counting as untouched. Concepts get their names and short descriptions from the website's concept pages, where the earlier `pool.toml` points to them. The import reports how many questions it **created** and which concepts it **named**.

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
| `markwise pool languages <pool> [de,en]` | show the languages of a pool, or change them |
| `markwise pool unwrap <pool> [--yes]` | count, and with `--yes` join, text lines that were wrapped by hand into paragraphs |
| `markwise question new <pool> --concept <concept> [--type single\|multiple\|free_text]` | create a question from the template of its type |
| `markwise question list <pool or module> [--search] [--concept] [--status] [--type] [--level] [--use practice\|exam] [--public yes\|no] [--findings errors\|warnings\|none]` | list questions, searched and filtered; a module folder lists all its pools |
| `markwise question show <pool> <id>` | print a question file |
| `markwise question release <pool> <id> [--by <name>]` | release a question as examiner; a second examiner adds their name |
| `markwise question withdraw <pool> <id> [--by <name>]` | take back your release |
| `markwise question variant <pool> <id> [--by <name>]` | create an exam variant of a practice question (`<id>-v1`, …): its texts as a copy to vary, its settings inherited |
| `markwise question retire <pool> <id>` / `restore` | take a question out of new exams / back in, as a draft |
| `markwise question set <pool> <id> <field> <value>` | change one field by a dotted path (`level`, `stem.de`, `options.b.correct`); `true`, `false` and numbers are understood |
| `markwise question delete <pool> <id> --yes [--used-in-exam] [--variants delete\|detach]` | delete a draft, retire anything else; for a question with variants, delete them too or detach them |
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
| `markwise llm key [--key <key>] [--from-env]` | check an OpenAI API key and store it in the Windows credential store; `--from-env` takes it from `OPENAI_API_KEY`, without either it is asked for without showing it |
| `markwise llm models` | list the models the stored key may use |
| `markwise llm use [--model <model>] [--off]` | switch the language model on (and choose the model) or off |
| `markwise assist review <pool> <id> [--lang de]` | let the model check the question with its answers and complete it; prints findings, proposed texts per field and language, and new wrong options if some are missing; changes nothing |
| `markwise assist numbers <pool> <id>` | let the model propose other numbers for a free-text calculation, with its worked-out answer; changes nothing |
| `markwise exam new <module> --title <title> --date <YYYY-MM-DD> [--lang de\|en] [--answers sheet\|inline]` | create an exam in its folder below the module |
| `markwise exam add <exam> <pool> <id> [--points]` | add a question; its points follow from its time unless given |
| `markwise exam remove <exam> <id>` | take a question out of the exam |
| `markwise exam section <exam> --title <title> [--note <text>] [--before <id>]` | add a section that starts before a question, or at the end |
| `markwise exam section <exam> --remove <section>` | remove a section; its questions stay |
| `markwise exam rename <exam> [--title <title>] [--date <YYYY-MM-DD>]` | give an exam a new title or date; its folder follows |
| `markwise exam show <exam>` | show an exam with its questions, points and what the check finds |
| `markwise exam print <exam> [--booklets N]` | typeset N numbered copies, the answer key and `layout.json` into the exam's print folder |
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
| Exams: freezing, booklets personalised from the participant list, shuffling, drawing questions by a blueprint | 27 Nov 2026 |
| Reading scans, deciding doubtful cases, grading multiple-choice exams | early December 2026 |
| Item analysis, exports for the examinations office, inspection copies | 15 Jan 2027 |
| Marking free-text answers on screen; more help from a language model (drafting expected answers, other providers and local models) | after the first exams in early 2027 |

## Privacy

Markwise runs on your computer and sends nothing anywhere, unless you switch on the language model; then the text and figures of the question you are working on go to OpenAI when you press **Check with AI** or **Propose other numbers**, and nothing else. Question pools contain no personal data. Names, student numbers, scans and grades exist only in the exam folders below a module folder, which belongs where only authorised people have access, as exam documents do today.

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

The logo, a white tick on a green rounded square, is drawn by `python tools\make_icon.py`, which writes the favicon of the interface and the Windows icon `src/markwise/app/markwise.ico`.

The concept is in [docs/concept.md](docs/concept.md), the question format in [docs/question-format.md](docs/question-format.md). A clickable prototype of the interface (look and feel only, sample data, no logic) is in [prototype/](prototype/): open `prototype/index.html` in a browser.

Developed at Hochschule Osnabrück by Prof. Dr. Nicolas Meseth.
