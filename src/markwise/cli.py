"""Command-line interface. Every command can answer in JSON, so that agents use the same rules as people."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, catalog, editing
from .checks import ERROR, check_pool, summarize
from .importer import import_pool
from .module import Module
from .pool import Pool, PoolSettings
from .question import TYPES, ConflictError


def _print_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _count(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def cmd_check(args) -> int:
    pool = Pool.open(args.pool)
    findings = check_pool(pool)
    counts = summarize(findings)
    if args.json:
        _print_json({"pool": str(pool.root), "counts": counts, "findings": [f.to_dict() for f in findings]})
    else:
        shown = [f for f in findings if args.notes or f.severity != "note"]
        for f in shown:
            print(f"{f.severity:<8} {f.question or '-':<10} {f.message}")
        totals = ", ".join(_count(counts[k], k) for k in ("error", "warning", "note"))
        print(f"{pool.settings.name}: {totals}" + ("" if args.notes or not counts["note"] else " (show notes with --notes)"))
    return 1 if counts[ERROR] else 0


def cmd_import(args) -> int:
    report = import_pool(args.source, args.target, update=args.update)
    if args.json:
        _print_json(report.to_dict())
    else:
        for label, items in report.to_dict().items():
            if items:
                print(f"{label.replace('_', ' ')}: {len(items)}")
                if label in ("changed_in_source", "conflicts", "problems"):
                    for item in items:
                        print(f"  {item}")
        if report.changed_in_source:
            print("Run again with --update to take over the changes from the source.")
    return 1 if report.conflicts or report.problems else 0


def cmd_pool_init(args) -> int:
    pool = Pool.create(args.folder, PoolSettings(name=args.name, languages=args.languages.split(",")))
    print(json.dumps({"pool": str(pool.root)}) if args.json else f"Pool created in {pool.root}")
    return 0


FINDINGS = ("errors", "warnings", "none")


def _rows_for(path: str, lang: str) -> list[dict]:
    """Rows of a pool, or of every pool of a module when the folder holds a module.toml."""
    folder = Path(path)
    if (folder / "module.toml").exists() or folder.name == "module.toml":
        module = Module.open(folder)
        return [row for pool in module.open_pools() for row in catalog.rows(pool, lang)]
    return catalog.rows(Pool.open(folder), lang)


def _keep(row: dict, args) -> bool:
    for key in ("concept", "status", "type", "level"):
        value = getattr(args, key, None)
        if value and row[key] != value:
            return False
    if args.public is not None and row["public"] != (args.public == "yes"):
        return False
    if args.use == "practice" and not row["public"]:
        return False
    if args.use == "exam" and not row["exam"]:
        return False
    if args.findings == "errors" and not row["errors"]:
        return False
    if args.findings == "warnings" and not row["warnings"]:
        return False
    if args.findings == "none" and (row["errors"] or row["warnings"]):
        return False
    return not args.search or catalog.matches(row, args.search)


def _use(row: dict) -> str:
    return "both" if row["public"] and row["exam"] else "practice" if row["public"] else "exam"


def cmd_question_list(args) -> int:
    rows = [row for row in _rows_for(args.pool, args.lang) if _keep(row, args)]
    if args.json:
        _print_json([{k: v for k, v in row.items() if k != "search"} for row in rows])
    else:
        for row in rows:
            marks = ("E" if row["errors"] else "W" if row["warnings"] else " ")
            stem = " ".join(row["stem"].split())
            stem = stem[:70] + ("…" if len(stem) > 70 else "")
            print(f"{marks} {row['id']:<10} {row['type']:<9} {row['level']:<10} {row['status']:<9} "
                  f"{_use(row):<8} {row['concept']:<28} {stem}")
        print(_count(len(rows), "question") + ("  (E = errors, W = warnings; see markwise check)" if any(r["errors"] or r["warnings"] for r in rows) else ""))
    return 0


def cmd_question_show(args) -> int:
    question = Pool.open(args.pool).find(args.id)
    print(question.path.read_text(encoding="utf-8"), end="")
    return 0


def cmd_question_new(args) -> int:
    question = Pool.open(args.pool).new_question(args.concept, args.type)
    if args.json:
        _print_json(question.summary())
    else:
        print(f"{question.id} created: {question.path}")
    return 0


def cmd_question_set(args) -> int:
    pool = Pool.open(args.pool)
    question, changed = editing.set_field(pool, args.id, args.field, args.value)
    findings = [f for f in editing.check_fields(pool, args.id, {}) if f["severity"] != "note"]
    if args.json:
        _print_json({"id": question.id, "changed": changed, "status": question.status, "findings": findings})
    else:
        print(f"{question.id} {'changed' if changed else 'unchanged'}; status {question.status}")
        for f in findings:
            print(f"  {f['severity']:<8} {f['message']}")
    return 1 if any(f["severity"] == "error" for f in findings) else 0


def cmd_question_delete(args) -> int:
    if not args.yes:
        print("Deleting needs --yes. A question that is not a draft, or was in an exam, is retired instead.",
              file=sys.stderr)
        return 2
    outcome = Pool.open(args.pool).delete(args.id, used_in_exam=args.used_in_exam)
    print(json.dumps({"id": args.id, "outcome": outcome}) if args.json else f"{args.id} {outcome}")
    return 0


def cmd_concept_list(args) -> int:
    pool = Pool.open(args.pool)
    counts: dict[str, int] = {}
    for path in pool.question_files():
        counts[path.parent.name] = counts.get(path.parent.name, 0) + 1
    concepts = [{**c, "questions": counts.get(c["id"], 0)} for c in pool.concept_info()]
    if args.json:
        _print_json(concepts)
    else:
        for c in concepts:
            name = c["name"] if c["named"] else f"{c['name']} (no name yet)"
            print(f"{c['id']:<32} {c['questions']:>4}  {name}" + (f" — {c['description']}" if c["description"] else ""))
    return 0


def cmd_concept_add(args) -> int:
    pool = Pool.open(args.pool)
    cid = pool.add_concept(args.name, args.description or "")
    print(json.dumps({"id": cid}) if args.json else f"Concept {args.name!r} added as {cid}")
    return 0


def cmd_concept_edit(args) -> int:
    pool = Pool.open(args.pool)
    pool.update_concept(args.id, args.name, args.description)
    info = next(c for c in pool.concept_info() if c["id"] == args.id)
    print(json.dumps(info, ensure_ascii=False) if args.json else f"{args.id}: {info['name']}")
    return 0


def cmd_concept_delete(args) -> int:
    Pool.open(args.pool).delete_concept(args.id)
    print(json.dumps({"deleted": args.id}) if args.json else f"Concept {args.id} deleted")
    return 0


def cmd_module_init(args) -> int:
    module = Module.create(args.folder, args.name, args.short_name, pools=args.pool or [])
    print(json.dumps({"module": str(module.root)}) if args.json else f"Module created in {module.root}")
    return 0


def cmd_module_show(args) -> int:
    module = Module.open(args.folder)
    data = {
        "name": module.name, "short_name": module.short_name, "regulations": module.regulations,
        "pools": [{"ref": ref, "name": pool.settings.name, "path": str(pool.root)}
                  for ref, pool in zip(module.pools, module.open_pools())],
        "exams": [str(p) for p in module.exams()],
    }
    if args.json:
        _print_json(data)
    else:
        print(f"{module.name} ({module.short_name}), regulations {module.regulations}")
        for pool in data["pools"]:
            print(f"  pool  {pool['name']}  {pool['path']}")
        for exam in data["exams"]:
            print(f"  exam  {exam}")
    return 0


def cmd_module_add_pool(args) -> int:
    module = Module.open(args.folder)
    module.add_pool(args.pool)
    module.save()
    print(json.dumps({"pools": module.pools}) if args.json else f"{module.name} now draws from: {', '.join(module.pools)}")
    return 0


def cmd_module_remove_pool(args) -> int:
    module = Module.open(args.folder)
    module.remove_pool(args.pool)
    module.save()
    print(json.dumps({"pools": module.pools}) if args.json else f"{module.name} now draws from: {', '.join(module.pools) or 'no pool'}")
    return 0


def cmd_app(args) -> int:
    from .app import run
    run(dev=args.dev, debug=args.debug)
    return 0


def cmd_serve(args) -> int:
    from .app.server import serve
    serve(args.port)
    return 0


def cmd_shortcut(args) -> int:
    from .app import create_shortcut
    link = create_shortcut(Path(args.folder) if args.folder else None)
    print(json.dumps({"shortcut": str(link)}) if args.json else f"Start menu entry created: {link}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="markwise", description="Paper exams from the question pool to the grade.")
    parser.add_argument("--version", action="version", version=f"markwise {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="answer in JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", parents=[common], help="check every question of a pool")
    p.add_argument("pool", help="pool folder or its pool.toml")
    p.add_argument("--notes", action="store_true", help="also list notes, not only errors and warnings")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("import", parents=[common], help="import a question bank in the earlier YAML format")
    p.add_argument("source", help="pool.toml of the earlier format")
    p.add_argument("target", help="folder of the Markwise pool (created if needed)")
    p.add_argument("--update", action="store_true", help="take over questions that changed in the source")
    p.set_defaults(func=cmd_import)

    pool = sub.add_parser("pool", help="create pools").add_subparsers(dest="action", required=True)
    p = pool.add_parser("init", parents=[common], help="create an empty pool")
    p.add_argument("folder")
    p.add_argument("--name", required=True)
    p.add_argument("--languages", default="de,en")
    p.set_defaults(func=cmd_pool_init)

    question = sub.add_parser("question", help="list, show, create, delete questions").add_subparsers(
        dest="action", required=True)
    p = question.add_parser("list", parents=[common], help="list questions of a pool or of all pools of a module")
    p.add_argument("pool", help="pool folder, or a module folder for all its pools")
    p.add_argument("--search", help="words that must all occur in text, options, feedback or identifier")
    p.add_argument("--findings", choices=FINDINGS, help="only questions with errors, with warnings, or without findings")
    p.add_argument("--lang", default="de", help="language of the question text shown (default de)")
    p.add_argument("--concept")
    p.add_argument("--status")
    p.add_argument("--type", choices=TYPES)
    p.add_argument("--level")
    p.add_argument("--use", choices=("practice", "exam"), help="questions meant for practice, or for exams (both count for each)")
    p.add_argument("--public", choices=("yes", "no"), help="only questions that are (not) shown for practice")
    p.set_defaults(func=cmd_question_list)
    p = question.add_parser("show", parents=[common])
    p.add_argument("pool")
    p.add_argument("id")
    p.set_defaults(func=cmd_question_show)
    p = question.add_parser("new", parents=[common], help="create a question from the template of its type")
    p.add_argument("pool")
    p.add_argument("--concept", required=True)
    p.add_argument("--type", choices=TYPES, default="single")
    p.set_defaults(func=cmd_question_new)
    p = question.add_parser("set", parents=[common], help="change one field, for example level, stem.de or options.b.correct")
    p.add_argument("pool")
    p.add_argument("id")
    p.add_argument("field", help="dotted path: level, public, exam, variant_of, stem.de, code_language, options.b.text.en, options.b.correct …")
    p.add_argument("value", help="the new value; true, false and numbers are understood, everything else is text")
    p.set_defaults(func=cmd_question_set)
    p = question.add_parser("delete", parents=[common], help="delete a draft, retire anything else")
    p.add_argument("pool")
    p.add_argument("id")
    p.add_argument("--yes", action="store_true", help="confirm")
    p.add_argument("--used-in-exam", action="store_true", help="the question was in an exam: retire it")
    p.set_defaults(func=cmd_question_delete)

    concept = sub.add_parser("concept", help="list, add and rename the concepts of a pool").add_subparsers(
        dest="action", required=True)
    p = concept.add_parser("list", parents=[common])
    p.add_argument("pool")
    p.set_defaults(func=cmd_concept_list)
    p = concept.add_parser("add", parents=[common], help="add a concept; its identifier is made from the name")
    p.add_argument("pool")
    p.add_argument("name", help="the name in plain words, for example 'Zahlensysteme und Codes'")
    p.add_argument("--description", help="a short description")
    p.set_defaults(func=cmd_concept_add)
    p = concept.add_parser("edit", parents=[common], help="rename or describe a concept; identifier and folder stay")
    p.add_argument("pool")
    p.add_argument("id")
    p.add_argument("--name")
    p.add_argument("--description")
    p.set_defaults(func=cmd_concept_edit)
    p = concept.add_parser("delete", parents=[common], help="delete a concept that has no questions")
    p.add_argument("pool")
    p.add_argument("id")
    p.set_defaults(func=cmd_concept_delete)

    module = sub.add_parser("module", help="create and show modules").add_subparsers(dest="action", required=True)
    p = module.add_parser("init", parents=[common], help="create module.toml in the module folder")
    p.add_argument("folder")
    p.add_argument("--name", required=True)
    p.add_argument("--short-name", required=True)
    p.add_argument("--pool", action="append", help="a pool the module draws from (repeatable)")
    p.set_defaults(func=cmd_module_init)
    p = module.add_parser("show", parents=[common])
    p.add_argument("folder")
    p.set_defaults(func=cmd_module_show)
    p = module.add_parser("add-pool", parents=[common], help="let the module draw from another pool")
    p.add_argument("folder")
    p.add_argument("pool")
    p.set_defaults(func=cmd_module_add_pool)
    p = module.add_parser("remove-pool", parents=[common], help="detach a pool from the module (the pool stays)")
    p.add_argument("folder")
    p.add_argument("pool")
    p.set_defaults(func=cmd_module_remove_pool)

    p = sub.add_parser("app", help="open the app window")
    p.add_argument("--dev", action="store_true", help="load the interface from the Vite development server")
    p.add_argument("--debug", action="store_true", help="allow the developer tools in the window")
    p.set_defaults(func=cmd_app)

    p = sub.add_parser("serve", help="serve the core on 127.0.0.1 for developing the interface in a browser")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("shortcut", parents=[common], help="create a Start menu entry for the app window")
    p.add_argument("--folder", help="create it in this folder instead of the Start menu")
    p.set_defaults(func=cmd_shortcut)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # question texts contain umlauts; Windows consoles default to cp1252
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, FileExistsError, KeyError, ValueError, ConflictError) as exc:
        message = exc.args[0] if exc.args else str(exc)
        if getattr(args, "json", False):
            _print_json({"error": str(message)})
        else:
            print(f"markwise: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
