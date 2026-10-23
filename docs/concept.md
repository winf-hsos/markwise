# Markwise: concept

Status: draft, October 2026. The decisions taken so far are listed at the end.

## What Markwise is for

Examiners who set paper exams with multiple-choice and free-text questions today juggle several tools: a document for the questions, a word processor for the exam booklet, a spreadsheet for the points, and, for automatic marking, a tool such as Auto Multiple Choice that only runs well on Linux. Markwise brings this into one Windows app with a calm, intuitive interface. It covers the whole way from the question to the grade:

0. choose or set up a module,
1. write and maintain the module's questions,
2. put an exam together from them,
3. print personalised booklets and answer sheets,
4. read the scanned answer sheets,
5. decide the doubtful cases,
6. grade, analyse and export.

## Components

| Component | Technology | Role |
|---|---|---|
| App window | Python with pywebview (uses the WebView2 runtime built into Windows) | a real desktop window with a Start menu entry, not a browser tab |
| User interface | HTML, CSS and JavaScript built with a component framework (proposal: Svelte), shipped as static files | the interface; no Node.js needed at run time |
| Core | Python package | all logic: reading and checking questions, building exams, reading scans, grading. The interface only calls the core. |
| Question pool | a folder with `pool.toml` and one YAML file per question, free of personal data; exportable and importable as a ZIP file | the single source of the questions. The folder can be local, on OneDrive or Teams, or on a network drive, so that colleagues can share a pool. No Git is needed. |
| Module folder | `module.toml` in the folder where the examiner keeps the module's exams; every exam in a folder of its own below it | which pools a module draws from, its examination regulations, and its exams with participants, scans and grades |
| Search index | SQLite, stored locally for each user (never in the shared folder) | fast search and statistics; rebuilt from the files at any time |
| Typesetting | Typst, used as a Python package | exam booklets, answer booklets, answer keys, marking guides, inspection copies as PDF |
| Scan reading | PyMuPDF (pages from the scanner's PDF) and OpenCV (corner marks, QR codes, tick boxes) | reading ticks and point strips |
| Agent interface | a command-line program (`markwise check`, `build`, `grade`, `question create/update/delete`, all with JSON output) and, while the app runs, a local HTTP interface on 127.0.0.1 | lets an AI agent maintain questions and run steps with the same rules as the interface |
| Installation | an installer (PyInstaller and Inno Setup) from the end of November 2026, when a colleague starts testing on a second computer; until then a Python environment for the author | |
| Languages | the interface in German and English, switchable, German by default | |

## Modules

Everything starts with a module, and **Modules** is the first entry of the menu. Markwise keeps two kinds of folders apart, because questions can be shared and exams cannot:

- A **question pool** holds questions and nothing else. It contains no personal data, so it can sit in a shared folder and be passed on as a ZIP file. One pool can serve several modules; a pool on artificial intelligence, for example, feeds the exams of two modules.
- A **module** (for example "Digitization and Programming") is a `module.toml` in the folder where the examiner keeps the module's exam documents anyway. It names the pools the module draws from and the examination regulations, and every exam of the module gets a folder of its own below it. Everything with names, scans and grades lives there.

```
LiFi Project/pool/              question pool, shareable
  pool.toml                     name, languages, concepts, number of options
  questions/<concept>/<id>.yaml
  images/

Digitization and Programming/   module folder, access for examiners only
  module.toml                   name, short name, regulations, pools, where new exams go
  01 - Semester/2026-27 - WS/Exam/2027-02-05 - Exam/
    exam.toml                   frozen: questions, shuffling, weights, examiners
    participants.csv
    print/  scans/  results/
```

The examiner sets up a module once: name and short name (shown in lists and on the printed booklets), the module folder, the pools, the examination regulations (grading profile), and a pattern for where new exams go, so that they follow the examiner's own filing scheme. Markwise finds the exams of a module by looking for `exam.toml` below the module folder. Regulations sit with the module because modules of different degree programmes follow different rules.

**Where the folders live.** The module folder belongs where only authorised people have access, as exam documents do today. The pool can sit anywhere the people who write questions can reach it.

**Import and export.** "Export" writes a pool as a ZIP file; "Import" unpacks such a file into a folder of the examiner's choice. Exams are never part of an export. "Open folder" adds an existing pool or module, for example after copying it from another computer. Markwise remembers the opened pools and modules locally for each user.

**Importing an existing question bank.** Questions kept in the YAML format of the earlier exam workflow (a `pool.toml` with German keys, one file per question) are converted once with `markwise import`. Fields Markwise does not know are kept in the converted files. A second import of the same source adds new questions and lists questions that changed in the source, but never overwrites a question silently.

**The current module** is shown in a slim header above every page, with a menu to switch to another module and the folder path on the right. The side menu stays the same for every module: Modules, Questions, Exams, and at the bottom the general settings (interface language, the examiner's name).

## Questions

**Types.** `single` (one correct answer), `multiple` (one or more correct answers) and `free_text`.

**Fields of every question.** An identifier assigned by the app (for example `aa-015`), the concept it belongs to, the cognitive level, the status, whether it is meant for practice, for exams or for both, the languages (German and English side by side), the question text with optional code, image or formula, and for exam variants the practice question they are a variant of. The format is described in [question-format.md](question-format.md).

**Status.** `draft`, `reviewed`, `piloted` (used in an exam and unremarkable in the item analysis) and `retired`. Identifiers are never reused.

**Multiple choice.** At least four options, each with a short justification of why it is right or wrong.

**Free text.** Whether half points are allowed (set per question), the size of the answer area, the expected answer, and marking notes for partial credit.

**Time, not points.** Every question records how long answering it takes (15 s to 5 min as usual steps, or any other time). Points belong to an exam: building an exam suggests them from the times and the exam's duration, the examiners adjust them, and freezing the exam fixes them. How difficult a question is, the item analysis measures after an exam instead of anyone guessing it beforehand.

**Who wrote it.** A question records who created it and who changed it last, with the date, because several examiners may work on one pool in a shared folder. There is one point strip per question; a second marking is not supported inside Markwise.

**Working with questions.**
- Browse, search and filter by concept, level, status, type, public or exam, language.
- Create from a template per type; edit with a live preview that looks exactly like the printed question. Saving overwrites the file and keeps fields, comments and layout Markwise does not edit; there is no version history.
- Deleting a question that has never been in an exam removes the file after a confirmation. A question that has been in an exam is retired instead, so that past exams and their statistics stay traceable.
- Rules are checked while typing (for example at least four options, no option that gives itself away by its length).
- Review: a question becomes `reviewed` once examiners have read it; who released it is recorded in the file (`reviewed_by`). Editing a reviewed question sets it back to `draft`.
- When two people edit the same question in a shared folder at the same time, Markwise notices on saving that the file changed in the meantime and shows both versions instead of silently overwriting the other person's work.
- Statistics per question from past exams: difficulty, discrimination, how often each wrong option was chosen.
- Export of the public questions for a practice platform.

## Exams

**Shuffling.** Chosen per exam, in one of three ways: an individual order of questions and options for every participant, four fixed groups A to D, or the same order of questions for everyone with the options shuffled per participant. The QR code tells Markwise which order a booklet has.

**Putting an exam together.** Choose a blueprint (how many questions per concept and level), let Markwise draw the questions or choose them by hand, and check the blueprint and the rules (for example no two variants of the same practice question). Preview the booklet, then **freeze** the exam.

For multiple-choice exams under § 5 (3) of the general examination regulations, freezing also records what the regulations require beforehand: at least two examiners who chose the material, the weight of every question and the correct answers. Markwise warns when fewer than two examiners are entered, and it never gives negative points across a question.

**Frozen exams are self-contained.** Every exam gets its own folder below the module folder. On freezing, Markwise copies the full content of every question into it, together with the settings. Later the folder receives booklets, answer key, scans and results. An exam therefore stays complete and traceable even if its questions are changed or deleted in the pool afterwards. Each examiner keeps the module folder safe, as they keep their exam documents today.

**Participants.** Import the list of registered participants from the export of the examination system (name and student number, as CSV or Excel). On the first import Markwise asks which column is which and remembers it. Names and results live only in the exam's folder, never in the question pool.

**Personalised or anonymous answer booklets.** Both are possible, personalised is the default.
- *Personalised* (default): one answer booklet per registered participant, generated from the imported list. Name and student number are printed on the cover, and the QR code on every page already belongs to that participant, so nothing has to be read from handwriting.
- *Anonymous*: answer booklets without a name. The cover carries a tick grid for the student number, which the scan reads; a handwritten name field is there for the examiner, not for the scan. Uncertain digits go into the doubtful cases.
- In a personalised exam a few anonymous booklets are printed as spares for late registrations and spoilt booklets.

**Printing.**
- An exam booklet with the questions (not scanned) and an answer booklet that is scanned: first the tick boxes for all multiple-choice questions, then one answer area per free-text question with a grey point strip "for examiners only" next to it (boxes 0, 1, 2 … up to the maximum, a box for ½ if half points are allowed, two rows for tens and units when the maximum is large).
- Every page of the answer booklet carries four corner marks and a QR code with exam, variant, page and booklet number.
- One print-ready PDF for the copier, the answer key, an examiner's copy, and a marking guide per free-text question (expected answer and notes for partial credit).

## After the exam

**Marking free text.** The examiner marks the free-text answers on paper with the marking guide and ticks the points in the point strip.

**Scanning.** The answer booklets are scanned at the copier into a PDF (300 dpi, greyscale) and dropped into Markwise. Each page is identified by its QR code, straightened by its corner marks and read: ticks and point strips in one pass. Problems go into a list (unknown page, missing page, page read twice).

**Doubtful cases.** Only uncertain marks are shown (half-filled, corrected, crossed out, an empty point strip), as an image crop next to the reading. The examiner decides by keyboard; every decision is logged. An empty point strip is never silently counted as zero.

**Grading.** The grading rules come from a profile of the examination regulations (points for single and multiple choice, pass mark and any sliding pass mark, grade scale, bonus). How multiple-choice and free-text parts are combined has to be checked against the regulations before it is built. After grading, the item analysis shows questions that behaved oddly (for example the strongest participants answering wrongly); such a question can be removed and everything is recalculated and documented.

**Results.** Grade list as an export for the examinations office, an inspection copy per participant (their scan with the marks read and the correct answers), a statistics report.

## What the examiner does

| When | What | Time |
|---|---|---|
| Once per module | set up the module: name, module folder, examination regulations | about 5 min |
| Weeks before | write questions or have an agent draft them, review and release them in Markwise | depends on the pool |
| Two weeks before | choose the blueprint, let Markwise draw the exam, check the booklet, freeze | about 30 min |
| One week before | import participants, create the PDF, print and check one sample, print all | about 20 min plus copier |
| During the exam | hand out booklets; late registrations get a spare booklet | as today |
| After the exam | mark free-text answers on paper and tick the points | depends on the exam |
| | scan the answer booklets, drop the PDF into Markwise | about 15 min |
| | decide the doubtful cases | an estimated 5 to 10 min for 50 booklets |
| | look at the item analysis, remove odd questions if needed, release grades, export | about 15 min |
| Inspection | open the participant's inspection copy | a few minutes |

## Optional help from a language model

Every place where a model could help works fully without it. The core has a narrow provider module (`assist.py`); since October 2026 it speaks to OpenAI, and the first uses below are built: checking a question text or the whole question with proposed corrections, and proposing wrong answers with feedback. The model answers in a fixed JSON schema, so that its suggestions can be shown and applied field by field.

Examiners who want it switch it on in the settings, enter an API key there and choose a model from those the key may use; the key is stored in the Windows credential store, never in question files or exam folders. Every suggestion from the model is shown as a suggestion and has to be accepted by a person; nothing changes without that click. The provider is to become configurable: OpenAI (built) and Anthropic through their APIs, and a model running locally on the examiner's computer (for example through Ollama), so that nothing has to leave the computer. **External providers are used only for work on questions**, which contain no personal data. Everything that comes from a scan (tick crops, handwriting) goes to a locally running model or nowhere.

Where it helps, the first use case first:

- **Reviewing and fixing questions** (built for the question text and for the question with its answers in one language; comparing the language versions is next). The model checks a question against the writing rules: is the stem clear without the options, are the distractors plausible, does an option give itself away by length or wording, does the level fit, do the German and English versions say the same. It explains its findings and proposes a corrected wording, which the examiner accepts or rejects.
- **Second opinion on doubtful marks**, with a local model only. For an uncertain tick or point strip, the model says how it reads the image crop and why. The examiner still decides.
- **Drafting.** Proposing additional distractors (built), translating a question into the other language, drafting the expected answer and marking notes for a free-text question.
- **Transcribing handwriting for marking.** For free-text answers the model turns the handwriting into typed text, shown next to the scanned original, so that hard-to-read answers can be marked faster and more fairly. The original always stays visible and is what counts; words the model is unsure about are highlighted. This needs the answers scanned before they are marked, so it comes together with marking on screen (decision 6): scan once, read the transcript next to the original, enter the points by keyboard. Handwriting is personal data even without a name, so this feature works only with a locally running model.
- **Reading the item analysis.** For a question that behaved oddly in an exam, the model suggests possible reasons (for example two defensible answers) as a starting point for the examiner's decision.

Not planned: grading free-text answers. Marking stays with the examiner.

Privacy: whatever is sent to the model leaves the computer. Markwise shows which features send what, sends nothing that identifies a participant, and each feature can be switched on separately. Whether a feature may be used for an exam is the examiner's decision under the rules of their institution.

## Interface for agents and skills

An AI agent maintains questions through the same rules as a person: the command-line program and the local HTTP interface offer create, update, delete, check, build and grade, with validation, the same delete confirmation semantics and JSON output. An agent may also write question files directly; Markwise picks up the change on its next scan of the folder. Markwise does not depend on any agent skill; it manages its questions itself.

## Privacy

Markwise runs on the examiner's computer and sends nothing anywhere, unless the optional language model is switched on (see above). Participants' names and results exist only in the exam folder.

The repository holds code, documentation and invented test data only. Real exams, scans, participant lists and grades never go into it, not even as test cases; tests for scan reading use answer sheets filled in for the purpose.

## Plan

| Phase | Until | Result |
|---|---|---|
| 0 Concept and clickable prototype | 23 Oct 2026 | this concept, and a clickable interface without logic, to judge the look before anything is built |
| 1 Foundation and questions | 13 Nov 2026 | core package, question format, import of existing question banks, rules, command-line interface, app window with the question views; in parallel a test answer sheet scanned at the university's copier and read back |
| 2 A version for a second computer, building exams | 27 Nov 2026 | an installer, so that a colleague can test Markwise and enter their own questions; blueprint, variants, exam and answer booklets as PDF |
| 3 Scanning, doubtful cases, grading | early Dec 2026 | multiple-choice exams end to end, ready for the test exams |
| 4 Test exams | Dec 2026 | test exams in the modules that follow, results checked by hand against the sheets; fixes from what they show |
| 5 Output | 15 Jan 2027 | item analysis, exports, inspection copies; fixes from the colleague's tests |
| 6 First real exams | 21 Jan and 5 Feb 2027 | multiple-choice exams "Applications of AI" and "Digitization and Programming" |
| afterwards | | free-text questions, marking on screen, further help from a language model |

## Decisions

1. **Answer booklets:** personalised by default, generated from the export of the examination system (name and student number); anonymous booklets with a tick grid for the student number are possible as well and serve as spares.
2. **Shuffling:** chosen per exam (individual order, groups A to D, or options only).
3. **Half points for free text:** set per question.
4. **Second marker:** not supported; one point strip per question.
5. **Users:** first the author; from the end of November 2026 a colleague tests on a second computer and enters their own questions. Until the first real exams Markwise is built for one set of examination regulations; afterwards it gets help texts and settings for other regulations.
6. **Marking on screen:** yes, after the first real exams, as a second way next to paper and together with the transcription of handwriting.
7. **Language model:** not in the first version, but designed for. First use case: reviewing and fixing questions. Providers later: OpenAI, Anthropic and a locally running model; anything from a scan only with the local one.
8. **Interface language:** German and English, switchable, German by default.
9. **Independent question management:** Markwise keeps its own question format and does not depend on any other tool; existing question banks are imported.
10. **Pools and modules are separate folders:** pools hold questions only and can be shared; modules hold the exams and point to their pools.
11. **First use:** the test exams in December 2026 and both multiple-choice exams in early 2027 run on Markwise, without Auto Multiple Choice.
