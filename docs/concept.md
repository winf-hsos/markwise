# Markwise: concept

Status: draft, October 2026. The decisions taken so far are listed at the end.

## What Markwise is for

Examiners who set paper exams with multiple-choice and free-text questions today juggle several tools: a document for the questions, a word processor for the exam booklet, a spreadsheet for the points, and, for automatic marking, a tool such as Auto Multiple Choice that only runs well on Linux. Markwise brings this into one Windows app with a calm, intuitive interface. It covers the whole way from the question to the grade:

1. write and maintain questions,
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
| Question files | one YAML file per question, in an ordinary folder | the single source of the questions. The folder can be local, on OneDrive or Teams, or on a network drive, so that colleagues can share a pool. No Git is needed. |
| Search index | SQLite, stored locally for each user (never in the shared folder) | fast search and statistics; rebuilt from the files at any time |
| Typesetting | Typst, used as a Python package | exam booklets, answer booklets, answer keys, marking guides, inspection copies as PDF |
| Scan reading | PyMuPDF (pages from the scanner's PDF) and OpenCV (corner marks, QR codes, tick boxes) | reading ticks and point strips |
| Agent interface | a command-line program (`markwise check`, `build`, `grade`, `question create/update/delete`, all with JSON output) and, while the app runs, a local HTTP interface on 127.0.0.1 | lets an AI agent maintain questions and run steps with the same rules as the interface |
| Installation | first a Python environment with a Start menu entry for the author; once colleagues use it, an installer (PyInstaller and Inno Setup) | |
| Languages | the interface in German and English, switchable, German by default | |

## Questions

**Types.** `single` (one correct answer), `multiple` (one or more correct answers) and `free_text`.

**Fields of every question.** An identifier assigned by the app (for example `aa-015`), the concept it belongs to, the cognitive level, the status (`draft` or `reviewed`), whether it is public (practice) or reserved for exams, the languages (German and English side by side), the question text with optional code, image or formula, and for exam variants the practice question they are a variant of.

**Multiple choice.** At least four options, each with a short justification of why it is right or wrong.

**Free text.** Maximum points, whether half points are allowed (set per question), the size of the answer area, the expected answer, and marking notes for partial credit. There is one point strip per question; a second marking is not supported inside Markwise.

**Working with questions.**
- Browse, search and filter by concept, level, status, type, public or exam, language.
- Create from a template per type; edit with a live preview that looks exactly like the printed question; delete after a confirmation. Saving overwrites the file; there is no version history and no archive of questions.
- Rules are checked while typing (for example at least four options, no option that gives itself away by its length).
- Review: a question becomes `reviewed` once examiners have read it; who released it is recorded in the file. Editing a reviewed question sets it back to `draft`.
- When two people edit the same question in a shared folder at the same time, Markwise notices on saving that the file changed in the meantime and shows both versions instead of silently overwriting the other person's work.
- Statistics per question from past exams: difficulty, discrimination, how often each wrong option was chosen.
- Export of the public questions for a practice platform.

## Exams

**Shuffling.** Chosen per exam, in one of three ways: an individual order of questions and options for every participant, four fixed groups A to D, or the same order of questions for everyone with the options shuffled per participant. The QR code tells Markwise which order a booklet has.

**Putting an exam together.** Choose a blueprint (how many questions per concept and level), let Markwise draw the questions or choose them by hand, and check the blueprint and the rules (for example no two variants of the same practice question). Preview the booklet, then **freeze** the exam.

**Frozen exams are self-contained.** On freezing, Markwise copies the full content of every question into the exam folder, together with the settings. Later the folder receives booklets, answer key, scans and results. An exam therefore stays complete and traceable even if its questions are changed or deleted in the pool afterwards. Each examiner keeps this folder safe, as they keep their exam documents today.

**Participants.** Import the list of registered participants from the export of the examination system (name and student number, as CSV or Excel). On the first import Markwise asks which column is which and remembers it. Names and results live only in the exam folder, never in the question pool.

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

Markwise works completely without a language model. Examiners who want one can switch it on in the settings and enter an API key there; the key is stored in the Windows credential store, never in question files or exam folders. Every suggestion from the model is shown as a suggestion and has to be accepted by a person; nothing changes without that click. The provider is configurable: OpenAI and Anthropic through their APIs, and a model running locally on the examiner's computer (for example through Ollama), so that nothing has to leave the computer.

Where it helps:

- **Second opinion on doubtful marks.** For an uncertain tick or point strip, the image crop goes to a vision model, which says how it reads it and why. The examiner still decides. Only the crop of the boxes is sent, without the QR code, the cover page or any name.
- **Didactic review of questions.** The model checks a question against the writing rules: is the stem clear without the options, are the distractors plausible, does an option give itself away by length or wording, does the level fit, do the German and English versions say the same. It explains its findings and proposes a better wording.
- **Drafting.** Translating a question into the other language, proposing additional distractors, drafting the expected answer and marking notes for a free-text question.
- **Transcribing handwriting for marking.** For free-text answers the model turns the handwriting into typed text, shown next to the scanned original, so that hard-to-read answers can be marked faster and more fairly. The original always stays visible and is what counts; words the model is unsure about are highlighted. This needs the answers scanned before they are marked, so it belongs together with marking on screen (open decision 6): scan once, read the transcript next to the original, enter the points by keyboard. Handwriting is personal data even without a name, so this feature is switched on separately and only where the examiner's institution allows sending answers to the chosen provider, or with a locally running model.
- **Reading the item analysis.** For a question that behaved oddly in an exam, the model suggests possible reasons (for example two defensible answers) as a starting point for the examiner's decision.

Not planned: grading free-text answers. Marking stays with the examiner.

Privacy: whatever is sent to the model leaves the computer. Markwise shows which features send what, sends nothing that identifies a participant, and each feature can be switched on separately. Whether a feature may be used for an exam is the examiner's decision under the rules of their institution.

## Interface for agents and skills

An AI agent maintains questions through the same rules as a person: the command-line program and the local HTTP interface offer create, update, delete, check, build and grade, with validation, the same delete confirmation semantics and JSON output. An agent may also write question files directly; Markwise picks up the change on its next scan of the folder. The existing skill `multiple-choice-pruefung` will later call Markwise instead of Auto Multiple Choice.

## Privacy

Markwise runs on the examiner's computer and sends nothing anywhere, unless the optional language model is switched on (see above). Participants' names and results exist only in the exam folder.

## Plan

| Phase | Until | Result |
|---|---|---|
| 0 Concept and clickable prototype | 23 Oct 2026 | this concept, and a clickable interface without logic, to judge the look before anything is built |
| 1 Foundation and questions | 13 Nov 2026 | app skeleton; reading, searching, creating, editing, deleting and checking questions; command-line interface |
| 2 Building exams | 27 Nov 2026 | blueprint, variants, exam and answer booklets as PDF |
| 3 Scanning and doubtful cases | 18 Dec 2026 | reading and review interface, tested with real scans from the university's copier, including deliberately sloppy ticks |
| 4 Grading and output | 15 Jan 2027 | grading, item analysis, exports, inspection copies; free text complete |
| 5 First real exam | 5 Feb 2027 | multiple-choice exam "Digitization and Programming"; Auto Multiple Choice runs in parallel as a cross-check, results spot-checked by hand |
| afterwards | | adapt the skill; first exam with free-text questions; marking on screen as an option |

## Decisions

1. **Answer booklets:** personalised by default, generated from the export of the examination system (name and student number); anonymous booklets with a tick grid for the student number are possible as well and serve as spares.
2. **Shuffling:** chosen per exam (individual order, groups A to D, or options only).
3. **Half points for free text:** set per question.
4. **Second marker:** not supported; one point strip per question.
5. **Users:** first the author, then colleagues. Until the first real exam Markwise is built for one computer and one set of examination regulations; afterwards it gets an installer, help texts and settings for other regulations.
6. **Marking on screen:** yes, after the first real exam, as a second way next to paper and together with the transcription of handwriting.
7. **Language model providers:** OpenAI, Anthropic and a locally running model.
8. **Interface language:** German and English, switchable, German by default.
