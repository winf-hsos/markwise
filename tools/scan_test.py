"""Scan test: print a test answer sheet, fill it in by hand, scan it, read it back.

Usage:
    python tools/scan_test.py make <out-dir>
        writes the test sheets, a one-page instruction sheet (German) and the layout
    python tools/scan_test.py read <scan.pdf> <out-dir> [--layout layout.json]
        reads a scan, prints a report, writes results.json, crops of doubtful
        boxes and a debug image per page, and compares against the plan below

The plan of what to tick where is defined once in PLAN, so that the instruction
sheet and the comparison in ``read`` always agree. All data is invented.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import typst

from markwise.scan import DOUBTFUL, EMPTY, TICKED, crop_box, debug_image, read_pdf
from markwise.sheet import Layout, SheetPage, build_layout, render_sheet_pdf

EXAM = "SCANTEST"
UPSIDE_DOWN_BOOKLET = "002"
# Invented student numbers, one per booklet.
STUDENT_NUMBERS = {"001": "2468013", "002": "9753108"}


@dataclass(frozen=True)
class Task:
    """One line of the instruction sheet: what to do and what the reader should see."""

    questions: str  # shown in the instruction table
    action: str  # German instruction for the author
    boxes: str  # German list of the boxes to mark, as shown in the table
    expected: dict[str, frozenset[str]]  # box id -> acceptable states


def _all(ids: str, *states: str) -> dict[str, frozenset[str]]:
    return {i: frozenset(states) for i in ids.split()}


PLAN: list[Task] = [
    Task("1–5", "Ein sauberes Kreuz mit Kugelschreiber", "1a, 2b, 3c, 4d, 5e",
         _all("q1a q2b q3c q4d q5e", TICKED)),
    Task("6–8", "Zwei Kreuze in derselben Frage", "6a+c, 7b+e, 8a+d",
         _all("q6a q6c q7b q7e q8a q8d", TICKED)),
    Task("9–10", "Ein Häkchen statt eines Kreuzes", "9b, 10d",
         _all("q9b q10d", TICKED)),
    Task("11–12", "Ein kleines, flüchtiges Kreuz, das nur die Mitte des Kästchens trifft", "11c, 12a",
         _all("q11c q12a", TICKED)),
    Task("13–14", "Ein großes Kreuz, das deutlich über den Rand hinausreicht", "13b, 14e",
         _all("q13b q14e", TICKED)),
    Task("15–17", "Das Kästchen vollständig ausmalen", "15a, 16c, 17e",
         _all("q15a q16c q17e", DOUBTFUL)),
    Task("18–20", "Korrektur: erst ankreuzen, dann ganz ausmalen und ein anderes Kästchen ankreuzen",
         "18: a ausmalen, c ankreuzen; 19: b ausmalen, d ankreuzen; 20: e ausmalen, a ankreuzen",
         {**_all("q18a q19b q20e", DOUBTFUL), **_all("q18c q19d q20a", TICKED)}),
    Task("21–23", "Nur einen halben Strich ziehen, etwa ein angefangenes Häkchen", "21b, 22d, 23a",
         _all("q21b q22d q23a", DOUBTFUL)),
    Task("24–26", "Mit Bleistift ganz leicht andeuten", "24c, 25e, 26b",
         _all("q24c q25e q26b", DOUBTFUL, EMPTY)),
    Task("27–28", "Ein Kreuz mit Bleistift, normal fest", "27a, 28d",
         _all("q27a q28d", TICKED)),
    Task("29–30", "Mit Bleistift ankreuzen und wieder sauber wegradieren", "29c, 30e",
         _all("q29c q30e", EMPTY, DOUBTFUL)),
    Task("31", "Das Kästchen umkreisen, ohne hineinzuschreiben", "31b",
         _all("q31b", EMPTY, DOUBTFUL)),
    Task("32–35", "Ein Kreuz mit dickem Filzstift", "32a, 33b, 34c, 35d",
         _all("q32a q33b q34c q35d", TICKED, DOUBTFUL)),
    Task("36–40", "Nichts ankreuzen", "–", {}),
]


def expected_state(box_id: str) -> frozenset[str]:
    """Acceptable states of an answer box according to the plan (default: empty)."""
    for task in PLAN:
        if box_id in task.expected:
            return task.expected[box_id]
    return frozenset({EMPTY})


# ---------------------------------------------------------------------------
# make


def _typst_text(text: str) -> str:
    """Escape plain text for Typst markup."""
    for ch in "\\#*_`$<>@[]":
        text = text.replace(ch, "\\" + ch)
    return text


def instruction_source() -> str:
    rows = []
    for task in PLAN:
        rows.append(f"[{_typst_text(task.questions)}], [{_typst_text(task.action)}], [{_typst_text(task.boxes)}],")
    numbers = ", ".join(f"Bogen {bk}: {nr}" for bk, nr in STUDENT_NUMBERS.items())
    return f"""
#set page(paper: "a4", margin: (x: 18mm, y: 16mm))
#set text(font: ("Arial", "Liberation Sans", "DejaVu Sans"), size: 9.5pt, lang: "de")
#set par(justify: false, leading: 0.6em, spacing: 0.9em)

#text(size: 15pt, weight: "bold")[Scan-Test für Markwise: Anleitung]

Mit diesem Test prüfen wir vor Mitte November, ob Markwise Kreuze vom Kopierer der Hochschule zuverlässig
liest. Bitte beide Testbögen (Bogen 001 und 002) ausdrucken, ohne Skalierung („Tatsächliche Größe“),
und beide genau gleich nach der folgenden Tabelle ausfüllen. Fragen, die nicht in der Tabelle stehen,
bleiben leer.

#text(weight: "bold")[Matrikelnummer.] Bitte oben in die Felder schreiben und darunter je Spalte die Ziffer
ankreuzen: {_typst_text(numbers)}. Die Nummern sind ausgedacht.

#table(
  columns: (auto, 1fr, 62mm),
  inset: (x: 5pt, y: 4pt),
  stroke: 0.4pt + luma(60%),
  table.header([*Fragen*], [*Was tun*], [*Kästchen*]),
{chr(10).join(rows)}
)

#text(weight: "bold")[Stifte.] Kugelschreiber für alles, was nicht ausdrücklich Bleistift oder Filzstift
verlangt. Wenn ein zweiter Kugelschreiber zur Hand ist, gern Bogen 002 mit dem anderen ausfüllen.

#text(weight: "bold")[Scannen.] Am Kopierer der Hochschule „Scannen in Datei“ wählen, Format PDF,
Auflösung 300 dpi und Farbmodus Graustufen (nicht Schwarzweiß, nicht Farbe). Beide Bögen in einem
Durchgang durch den Einzug geben, wobei Bogen {UPSIDE_DOWN_BOOKLET} um 180 Grad gedreht, also auf dem Kopf
stehend, eingelegt wird. Die Bögen dafür nicht heften und nicht knicken.

#text(weight: "bold")[Auswerten.] Die PDF-Datei in den Arbeitsordner legen und dann lesen lassen:
#block(inset: (left: 8pt))[`python tools/scan_test.py read <scan.pdf> work/scan-test/auswertung`]
Der Bericht zeigt je Bogen, welche Kästchen wie erwartet gelesen wurden und welche nicht; Ausschnitte der
unsicheren Kästchen und ein Kontrollbild je Seite liegen im Ausgabeordner.
"""


def cmd_make(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    layout = build_layout()
    pages = [SheetPage(exam=EXAM, booklet=bk, title="Markwise · Testbogen Scan-Lesung") for bk in STUDENT_NUMBERS]
    sheet = out_dir / "scan-test-sheets.pdf"
    render_sheet_pdf(pages, sheet, layout)
    instructions = out_dir / "scan-test-instructions.pdf"
    instructions.write_bytes(typst.compile(instruction_source().encode("utf-8")))
    layout.to_json(out_dir / "layout.json")
    print(f"Testbögen:  {sheet}")
    print(f"Anleitung:  {instructions}")
    print(f"Layout:     {out_dir / 'layout.json'}")


# ---------------------------------------------------------------------------
# read

STATE_DE = {EMPTY: "leer", TICKED: "angekreuzt", DOUBTFUL: "unsicher"}
REASON_DE = {
    "filled": "ausgemalt",
    "heavy": "sehr viel Tinte",
    "partial": "nur teilweise",
    "faint": "nur schwach",
}


def _describe(box) -> str:
    text = STATE_DE[box.state]
    if box.reason:
        text += f" ({REASON_DE.get(box.reason, box.reason)})"
    return f"{text}, Füllung {box.fill_ratio:.2f}"


def compare_page(page) -> dict:
    """Compare the answer boxes of a page with the plan."""
    hits, misses = [], []
    for box in page.boxes:
        if box.kind != "answer":
            continue
        accepted = expected_state(box.id)
        entry = {
            "box": box.id,
            "expected": sorted(accepted),
            "read": box.state,
            "reason": box.reason,
            "fill_ratio": box.fill_ratio,
        }
        (hits if box.state in accepted else misses).append(entry)
    booklet = (page.qr or {}).get("bk")
    return {
        "booklet": booklet,
        "student_number_expected": STUDENT_NUMBERS.get(booklet),
        "student_number_read": page.student_number,
        "upside_down_expected": booklet == UPSIDE_DOWN_BOOKLET if booklet else None,
        "upside_down_read": page.upside_down,
        "hits": len(hits),
        "misses": misses,
    }


def cmd_read(scan: Path, out_dir: Path, layout_path: Path | None) -> int:
    layout = Layout.from_json(layout_path) if layout_path else build_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    crops = out_dir / "doubtful"
    crops.mkdir(exist_ok=True)
    result = read_pdf(scan, layout, keep_images=True)

    comparisons = []
    total_misses = 0
    print(f"Scan: {scan}  ({len(result.pages)} Seiten)\n")
    for page in result.pages:
        n = page.page_index + 1
        print(f"Seite {n}")
        print(f"  QR-Code:        {page.qr_text or 'nicht gelesen'}")
        if page.corners_px is None:
            for p in page.problems:
                print(f"  Problem:        {p.message}")
            comparisons.append({"page": n, "read": False})
            total_misses += 1
            print()
            continue
        cmp = compare_page(page)
        comparisons.append({"page": n, "read": True, **cmp})
        lage = "auf dem Kopf (gedreht)" if page.upside_down else "aufrecht"
        print(f"  Lage:           {lage}")
        if cmp["upside_down_expected"] is not None and cmp["upside_down_expected"] != page.upside_down:
            print("  ! Lage stimmt nicht mit dem Plan überein")
            total_misses += 1
        print(f"  Papier/Tinte:   {page.white_level:.0f} / {page.black_level:.0f} (Grauwerte)")
        sn_ok = cmp["student_number_expected"] == page.student_number
        print(f"  Matrikelnummer: {page.student_number}  (erwartet {cmp['student_number_expected']})"
              + ("" if sn_ok else "  !"))
        total_misses += 0 if sn_ok else 1
        for p in page.problems:
            print(f"  Problem:        {p.message}")
        answer_boxes = sum(1 for b in page.boxes if b.kind == "answer")
        print(f"  Kästchen:       {cmp['hits']} von {answer_boxes} wie erwartet")
        for m in cmp["misses"]:
            want = " oder ".join(STATE_DE[s] for s in m["expected"])
            print(f"  ! {m['box']:5} erwartet {want}, gelesen {_describe(page.box(m['box']))}")
        total_misses += len(cmp["misses"])
        doubtful = page.doubtful()
        if doubtful:
            print("  Unsicher:       " + ", ".join(f"{b.id} ({REASON_DE.get(b.reason, b.reason)})" for b in doubtful))
        print()

        # Images: crops of doubtful and wrongly read boxes, and the annotated page.
        missed = {m["box"] for m in cmp["misses"]}
        for b in page.boxes:
            if b.state == DOUBTFUL or b.id in missed:
                tag = b.reason or b.state
                cv2.imwrite(str(crops / f"p{n}-{b.id}-{tag}.png"), crop_box(page, b, layout.params.box_size))
        dbg = debug_image(page, layout)
        cv2.imwrite(str(out_dir / f"debug-p{n}.jpg"), dbg, [cv2.IMWRITE_JPEG_QUALITY, 85])

    data = result.to_dict()
    data["comparison"] = comparisons
    (out_dir / "results.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    verdict = "alles wie erwartet" if total_misses == 0 else f"{total_misses} Abweichung(en)"
    print(f"Ergebnis: {verdict}. Details in {out_dir / 'results.json'}")
    return 0 if total_misses == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Markwise scan test")
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("make", help="write the test sheets and the instructions")
    make.add_argument("out_dir", type=Path)
    read = sub.add_parser("read", help="read a scan and compare it with the plan")
    read.add_argument("scan", type=Path)
    read.add_argument("out_dir", type=Path)
    read.add_argument("--layout", type=Path, default=None, help="layout.json written by 'make'")
    args = parser.parse_args(argv)
    # The report is German; make sure umlauts survive a redirected console.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.command == "make":
        cmd_make(args.out_dir)
        return 0
    return cmd_read(args.scan, args.out_dir, args.layout)


if __name__ == "__main__":
    sys.exit(main())
