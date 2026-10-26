"""Typesetting exam booklets and reading them back, with invented questions only."""

from __future__ import annotations

import json

import cv2
import numpy as np
import pymupdf
import pytest

from markwise import booklet
from markwise.app.api import Api
from markwise.exam import Exam
from markwise.importer import import_pool
from markwise.module import Module
from markwise.scan.model import TICKED
from markwise.scan.reader import read_page_image

from test_core import write_legacy

DPI = 150


@pytest.fixture
def exam(tmp_path):
    import_pool(write_legacy(tmp_path / "legacy"), tmp_path / "pool")
    module = Module.create(tmp_path / "module", "Invented Module", "IM", pools=[tmp_path / "pool"])
    pool = module.open_pools()[0]
    task = pool.new_question("colours", "free_text", author="Examiner A")
    task.data["stem"]["de"] = "Mische zwei Farben."
    task.data["expected"]["de"] = "Gelb."
    task.data["stem"]["en"] = "Mix *two* colours with `#rgb` codes; what does [red] + $green$ give?"
    task.data["expected"]["en"] = "Yellow."
    task.data["status"] = "reviewed"
    task.data["lines"] = 4
    task.save()
    exam = Exam.create(module, "Mock Exam", "2027-01-21", "en", "inline", author="")
    exam.examiners = ["Examiner A", "Examiner B"]
    exam.add(module, pool.root, "co-002")
    exam.add(module, pool.root, task.id, points=2)
    exam.save()
    return exam


def _pages(pdf):
    for page in pymupdf.open(pdf):
        pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
        yield np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()


def _tick(img, layout, box):
    cx, cy = ((layout.origin[0] + box.x) * DPI / 25.4, (layout.origin[1] + box.y) * DPI / 25.4)
    r = box.size * 0.3 * DPI / 25.4
    cv2.line(img, (int(cx - r), int(cy - r)), (int(cx + r), int(cy + r)), 0, 3)
    cv2.line(img, (int(cx - r), int(cy + r)), (int(cx + r), int(cy - r)), 0, 3)


def _read_back(printed, scanned):
    """Tick the student number 0420 and every other box, then read each page: what comes back must be what was ticked."""
    layout_file = printed.folder / booklet.LAYOUT_FILE
    for n, img in enumerate(_pages(scanned)):
        page = n % printed.pages_per_booklet + 1
        layout = booklet.page_layout(layout_file, page)
        ticked = set()
        for i, box in enumerate(layout.boxes):
            wanted = (box.digit == int("0420"[box.digit_position]) if box.digit_position is not None and box.digit_position < 4
                      else box.kind != "student" and i % 2 == 0)
            if wanted:
                _tick(img, layout, box)
                ticked.add(box.id)
        result = read_page_image(img, layout, page_index=n, dpi=DPI)
        assert {b.id for b in result.boxes if b.state == TICKED} == ticked
        assert f"page={page};bk={n // printed.pages_per_booklet + 1:03d}" in result.qr_text
        if page == 1:
            assert result.student_number.startswith("0420")


def test_the_booklet_with_boxes_below_the_questions_reads_back(exam):
    printed = booklet.print_exam(exam, booklets=2)
    names = [p.name for p in printed.files]
    assert names == ["Exam booklet with answers.pdf", "layout.json", "Answer key.pdf"]
    assert printed.pages_per_booklet % 2 == 0
    layout = json.loads((printed.folder / booklet.LAYOUT_FILE).read_text(encoding="utf-8"))
    kinds = {b["kind"] for b in layout["boxes"]}
    assert kinds == {"student", "answer", "points"} and layout["booklets"] == 2
    assert pymupdf.open(printed.folder / names[0]).page_count == 2 * printed.pages_per_booklet
    _read_back(printed, printed.folder / names[0])


def test_the_answer_sheet_reads_back_and_replaces_the_last_print(exam):
    booklet.print_exam(exam)
    exam.answers = "sheet"
    exam.save()
    printed = booklet.print_exam(exam, booklets=1)
    assert sorted(p.name for p in printed.folder.iterdir()) == [
        "Answer key.pdf", "Answer sheet.pdf", "Exam booklet.pdf", "layout.json"]
    _read_back(printed, printed.folder / "Answer sheet.pdf")
    key = "".join(page.get_text() for page in pymupdf.open(printed.folder / "Answer key.pdf"))
    assert "Yellow." in key and "Mock Exam" in key


def test_question_text_cannot_break_the_typesetting(tmp_path):
    text = "A `#raw` value, *stress*, **bold**, [brackets], $dollars$, <label>, a # hash and a\nwrapped line.\n\n- one\n- two"
    pdf = booklet._compile(booklet._preamble("en") + booklet.markdown(text), tmp_path, query=False).pdf
    shown = pymupdf.open(stream=pdf).load_page(0).get_text()
    for part in ("#raw", "stress", "bold", "[brackets]", "$dollars$", "<label>", "a # hash and a wrapped line", "two"):
        assert part in " ".join(shown.split())


def test_an_exam_with_errors_or_without_questions_does_not_print(exam):
    module = Module.around(exam.root)
    empty = Exam.create(module, "Empty", "2027-02-01", "en", author="")
    with pytest.raises(booklet.BookletError) as caught:
        booklet.print_exam(empty)
    assert caught.value.code == "booklet_empty"
    answer = Api().print_exam(str(empty.root), 1)
    assert answer["code"] == "booklet_empty"
    exam.questions[0].id = "co-404"
    exam.save()
    assert Api().print_exam(str(exam.root), 1)["code"] == "booklet_errors"


def test_the_exam_page_gets_questions_as_the_booklet_shows_them(exam):
    module = Module.around(exam.root)
    pool = str(module.pool_root(exam.questions[0].pool))
    answer = Api().exam_items("en", [{"pool": pool, "id": "co-002"}, {"pool": pool, "id": "co-003"},
                                     {"pool": pool, "id": "co-404"}])["data"]
    choice, task, gone = answer["items"]
    assert choice["type"] == "multiple" and choice["options"] and all(set(o) == {"id", "text"} for o in choice["options"])
    assert task["type"] == "free_text" and task["lines"] == 4 and task["stem"].startswith("Mix")
    assert gone == {"pool": pool, "id": "co-404", "missing": True}
    assert answer["words"]["question"] == "Question" and answer["words"]["multiple"].startswith("One or more")


def test_sections_head_their_questions_in_the_booklet_and_the_key(exam):
    from markwise.exam import ExamSection
    exam.set_flat([ExamSection("s1", "Part A", "Tick the boxes."), exam.questions[0],
                   ExamSection("s2", "Part B"), exam.questions[1], ExamSection("s3", "Empty part")])
    exam.answers = "sheet"
    exam.save()
    printed = booklet.print_exam(exam)
    text = " ".join(" ".join(p.get_text() for name in ("Exam booklet.pdf", "Answer key.pdf")
                             for p in pymupdf.open(printed.folder / name)).split())
    assert text.count("Part A") >= 3 and "Tick the boxes." in text  # cover, booklet, key
    pages = " ".join(" ".join(p.get_text() for p in pymupdf.open(printed.folder / "Exam booklet.pdf")[1:]).split())
    assert pages.index("Part A") < pages.index("Question 1") < pages.index("Part B") < pages.index("Question 2")
    assert "Empty part" not in text
    assert "Part B 2 points" in text  # the cover lists the parts with their points
