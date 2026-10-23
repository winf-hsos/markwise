"""Command-line interface. Every command can answer in JSON, so that agents use the same rules as people."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .checks import ERROR, check_pool, summarize
from .importer import import_pool
from .module import Module
from .pool import Pool, PoolSettings
from .question import TYPES


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


def _filtered(pool: Pool, args):
    questions, errors = pool.load()
    for e in errors:
        print(f"cannot read {e.path}: {e.message}", file=sys.stderr)
    for key in ("concept", "status", "type", "level"):
        value = getattr(args, key, None)
        if value:
            questions = [q for q in questions if getattr(q, key) == value]
    if args.public is not None:
        questions = [q for q in questions if q.public == (args.public == "yes")]
    return questions


def cmd_question_list(args) -> int:
    questions = _filtered(Pool.open(args.pool), args)
    if args.json:
        _print_json([q.summary() for q in questions])
    else:
        for q in questions:
            print(f"{q.id:<10} {q.type:<9} {q.level:<10} {q.status:<9} {'public' if q.public else 'exam':<6} {q.concept}")
        print(f"{len(questions)} questions")
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


def cmd_question_delete(args) -> int:
    if not args.yes:
        print("Deleting needs --yes. A question that is not a draft, or was in an exam, is retired instead.",
              file=sys.stderr)
        return 2
    outcome = Pool.open(args.pool).delete(args.id, used_in_exam=args.used_in_exam)
    print(json.dumps({"id": args.id, "outcome": outcome}) if args.json else f"{args.id} {outcome}")
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
    p = question.add_parser("list", parents=[common])
    p.add_argument("pool")
    p.add_argument("--concept")
    p.add_argument("--status")
    p.add_argument("--type", choices=TYPES)
    p.add_argument("--level")
    p.add_argument("--public", choices=("yes", "no"))
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
    p = question.add_parser("delete", parents=[common], help="delete a draft, retire anything else")
    p.add_argument("pool")
    p.add_argument("id")
    p.add_argument("--yes", action="store_true", help="confirm")
    p.add_argument("--used-in-exam", action="store_true", help="the question was in an exam: retire it")
    p.set_defaults(func=cmd_question_delete)

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
    except (FileNotFoundError, FileExistsError, KeyError, ValueError) as exc:
        message = exc.args[0] if exc.args else str(exc)
        if getattr(args, "json", False):
            _print_json({"error": str(message)})
        else:
            print(f"markwise: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
