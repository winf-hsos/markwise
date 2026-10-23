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

# The concepts, each with a name and a short description in plain words. The key is the identifier
# Markwise makes from the name; it names the folder of the concept's questions and never changes.
# Without any [concepts] table, the folder names under questions/ are the concepts.
[concepts.code-systems]
name = "Code Systems"
description = "A code system is a table that assigns symbols to meanings."

[concepts.zahlensysteme-und-codes]
name = "Zahlensysteme und Codes"
description = "Wie Zahlen in verschiedenen Basen geschrieben werden."
```

The identifier is the name in lower case, with umlauts written out (`ä` becomes `ae`) and everything that is not a letter or digit turned into a hyphen. Renaming a concept changes only its name. An earlier `concepts = ["code-systems", …]` list of identifiers is still read; such concepts show a name made from the identifier until someone names them.

## A question

```yaml
id: cs-001                 # prefix of the concept and a running number
concept: code-systems      # the concept's identifier, equal to the folder name
type: single               # single | multiple | free_text
level: understand          # remember | understand | apply
status: draft              # draft | reviewed | piloted | retired
public: true               # shown to students for practice
exam: true                 # may be drawn for an exam; without the field: true exactly when public is false
variant_of: cs-001         # exam variants only: the practice question they vary (then public: false)
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
code_language: python      # optional: the language of the code, for highlighting; without it Markwise guesses

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

A question can be meant for practice, for exams, or for both. An exam variant is never public, because a variant students have seen no longer tests whether they understood the practice question.

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

- errors: required fields missing or of the wrong kind, identifier differs from the file name, concept differs from the folder or is unknown, a language missing, too few or too many options, duplicate option ids, the number of correct options does not fit the type, image file missing, `variant_of` pointing to a missing question or another concept, a public exam variant, a question meant neither for practice nor for exams, duplicate identifiers;
- warnings: an option much longer than the others (it may give itself away), a feedback text or expected answer missing in a language;
- notes: a question meant only for practice that has no exam variant, a concept without questions.

Retired questions only have to stay readable.

## Importing the earlier YAML format

`markwise import <old pool.toml> <new pool folder>` converts a question bank in the earlier format (German keys: `konzept`, `niveau`, `oeffentlich`, `frage`, `richtig`, `optionen` with `kennung`, `text`, `begruendung`) into this format. It maps the keys and values, derives `type` from `richtig` (a single letter is `single`, a list is `multiple`), copies the images and keeps unknown fields. Concepts take their names from the concept pages of the website (`title`) and their short descriptions from the `subtitle` or else the first sentence of the summary; a later import fills in names that are still missing and never overwrites one given in Markwise. It never overwrites an existing question: questions that changed in the source since the last import are listed instead.
