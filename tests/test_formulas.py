"""Formulas in question texts: where they start and end, and what is no formula."""

from markwise.formulas import DISPLAY, INLINE, formulas, problems, split


def test_formulas_inline_and_set_apart():
    assert formulas("Energie $E = mc^2$ und Masse") == [(INLINE, "E = mc^2")]
    assert formulas("Es gilt\n\n$$\n\\frac{a}{b} = c\n$$\n\nalso") == [(DISPLAY, "\\frac{a}{b} = c")]
    assert formulas("$a$, $b$ und $\\sqrt{2}$") == [(INLINE, "a"), (INLINE, "b"), (INLINE, "\\sqrt{2}")]


def test_dollar_signs_that_are_no_formula():
    # from a real question: passwords with a dollar sign, and "s zu $"
    assert formulas("`k7$Qz!2p`, acht Zeichen aus dem vollen Vorrat von 95 Zeichen") == []
    assert formulas("k7$Qz!2p, acht zufällige Zeichen aus 95") == []
    assert formulas("a zu @, o zu 0, s zu $. Für den Angreifer ist das kein neues Passwort") == []
    assert formulas("Das kostet 5 $ und 10 $.") == []  # a space after the first, before the second dollar
    assert formulas("zwischen $5 und $10") == []  # the closing dollar would be followed by a digit
    assert formulas("ein Dollar \\$ ist kein $x$-Wert") == [(INLINE, "x")]
    assert split("nur \\$ hier") == [("text", "nur $ hier")]


def test_code_keeps_its_dollars():
    assert split("`echo $HOME` und $y$") == [("code", "`echo $HOME`"), ("text", " und "), (INLINE, "y")]


def test_problems_of_a_formula():
    assert problems("\\frac{a}{b}") == []
    assert problems("\\frac{a}{b") == ["braces"]
    assert problems("\\begin{cases} a \\\\ b") == ["environment"]
    assert problems("\\{ a \\}") == []


def test_the_check_names_broken_formulas_and_files_keep_backslashes_readable(tmp_path):
    from markwise.checks import check_question
    from markwise.editing import save
    from markwise.importer import import_pool
    from markwise.pool import Pool
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from test_core import write_legacy

    import_pool(write_legacy(tmp_path / "legacy"), tmp_path / "pool")
    pool = Pool.open(tmp_path / "pool")
    q = pool.find("co-001")
    stem = dict(q.data["stem"])
    stem["en"] = "What is $\\frac{1}{2$? And $$ x"
    save(pool, "co-001", {"stem": stem}, None, True)
    codes = sorted(f.code for f in check_question(pool.find("co-001"), pool) if f.code.startswith("formula"))
    assert codes == ["formula_invalid", "formula_open"]
    stem["en"] = "What is $\\frac{1}{2}$?"
    save(pool, "co-001", {"stem": stem}, None, True)
    text = pool.find("co-001").path.read_text(encoding="utf-8")
    assert "en: |-\n    What is $\\frac{1}{2}$?" in text  # one backslash, as typed
    assert not [f for f in check_question(pool.find("co-001"), pool) if f.code.startswith("formula")]
