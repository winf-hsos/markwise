# Question pool format

A question pool is a folder with a `pool.toml` and one YAML file per question. It holds no personal data and can be shared as it is.

```
pool.toml
questions/<concept>/<id>.yaml
images/<name>.svg | .png
```

## `pool.toml`

```toml
name = "LiFi Project"
languages = ["de", "en"]   # every question needs stem, options and feedback in each
min_options = 4            # never below 4 (§ 5 (3) a of the general examination regulations)
max_options = 5

# Optional: the valid concepts. Without this list, the folder names under questions/ are the concepts.
concepts = ["code-systems", "compression"]
```

## A question

```yaml
id: cs-001                 # prefix of the concept and a running number
concept: code-systems      # equals the folder name
type: single               # single | multiple | free_text
level: understand          # remember | understand | apply
status: draft              # draft | reviewed | piloted | retired
public: true               # true: practice question; false: reserved for exams
variant_of: cs-001         # exam variants only: the practice question they vary
reviewed_by: []            # who released the question
coverage: "Deck 08, frames 5 to 7"   # optional: where the material is taught
misconception: code-equals-encryption # optional
session: 6                 # optional

stem:
  de: |
    Fragetext.
  en: |
    Question text.
image: decision-levels     # optional: a file in images/ (.svg for the screen, .png for print)
code: |                    # optional: a code block below the stem
  led.set_color(255, 0, 0)

options:                   # single and multiple only
  - id: a
    correct: false
    text:     {de: "...", en: "..."}
    feedback: {de: "Why this is wrong.", en: "..."}
  - id: b
    correct: true
    text:     {de: "...", en: "..."}
    feedback: {de: "Why this is right.", en: "..."}
```

Identifiers are never reused: a question that is not a draft is retired instead of deleted, and its file stays. Only a deleted draft frees its identifier.

`single` has exactly one correct option. `multiple` has at least one; one correct option is allowed, so that the number of correct answers cannot be guessed.

A free-text question has no options and instead:

```yaml
type: free_text
points: 4
half_points: true
lines: 10                  # size of the answer area
expected: {de: "...", en: "..."}
marking_notes: {de: "...", en: "..."}
```

Fields Markwise does not know stay in the file when Markwise saves it, together with comments and the layout of the untouched parts.

## Checks

`markwise check <pool>` reports errors (the question cannot be used), warnings (it should be looked at) and notes (worth knowing):

- errors: required fields missing or of the wrong kind, identifier differs from the file name, concept differs from the folder or is unknown, a language missing, too few or too many options, duplicate option ids, the number of correct options does not fit the type, image file missing, `variant_of` pointing to a missing question or another concept, a public exam variant, duplicate identifiers;
- warnings: an option much longer than the others (it may give itself away), a feedback text or expected answer missing in a language;
- notes: a practice question without an exam variant, a concept without questions.

Retired questions only have to stay readable.

## Importing the earlier YAML format

`markwise import <old pool.toml> <new pool folder>` converts a question bank in the earlier format (German keys: `konzept`, `niveau`, `oeffentlich`, `frage`, `richtig`, `optionen` with `kennung`, `text`, `begruendung`) into this format. It maps the keys and values, derives `type` from `richtig` (a single letter is `single`, a list is `multiple`), copies the images and keeps unknown fields. It never overwrites an existing question: questions that changed in the source since the last import are listed instead.
