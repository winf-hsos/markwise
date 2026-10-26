"""What the interface may ask the core. The same object serves the app window (pywebview) and `markwise serve`.

Every public method returns {"data": ...} or {"error": "...", "code": "...", "params": {...}}, so that the
interface gets a message it can translate instead of a stack trace.
"""

from __future__ import annotations

import functools
import os
import sys
from pathlib import Path

from .. import __version__, assist, booklet, catalog, editing, lifecycle, settings as user_settings
from ..exam import ANSWER_MODES, Exam, ExamQuestion, ExamSection, exams_of
from ..importer import import_pool
from ..module import EXAM_PATHS, MODULE_FILE, Module
from ..pool import LANGUAGES, POOL_FILE, Pool, PoolSettings
from ..question import TYPES, ConflictError


class Refusal(Exception):
    """A request the core turns down for a reason the person can fix; `code` names it for the interface."""

    def __init__(self, code: str, message: str, **params):
        super().__init__(message)
        self.code = code
        self.params = {k: str(v) for k, v in params.items()}


def _answer(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return {"data": method(*args, **kwargs)}
        except Refusal as exc:
            return {"error": str(exc), "code": exc.code, "params": exc.params}
        except Exception as exc:  # the interface shows the message; nothing may crash the window
            return {"error": str(exc.args[0]) if exc.args else exc.__class__.__name__}
    return wrapper


def _norm(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())


def _pool_entry(path: str) -> dict:
    folder = Path(path)
    if not (folder / POOL_FILE).exists():
        return {"path": path, "exists": False, "name": folder.name}
    pool = Pool.open(folder)
    return {"path": path, "exists": True, "name": pool.settings.name, "languages": pool.settings.languages,
            "questions": len(pool.question_files())}


def _module_entry(path: str) -> dict:
    folder = Path(path)
    if not (folder / MODULE_FILE).exists():
        return {"path": path, "exists": False, "name": folder.name, "short_name": "?", "pools": []}
    module = Module.open(folder)
    pools = [_pool_entry(str(module.pool_root(ref))) for ref in module.pools]
    return {"path": path, "exists": True, "name": module.name, "short_name": module.short_name,
            "regulations": module.regulations, "pools": pools}


def _remember_module(path: str, make_current: bool = True) -> None:
    current = user_settings.load()
    current.modules = [path] + [p for p in current.modules if p != path]
    if make_current:
        current.current_module = path
    user_settings.save(current)


def _check_pool_spec(spec: dict) -> Path:
    """Refuse a pool choice before anything is written, so that a refusal never leaves half a module behind."""
    mode, path = spec.get("mode"), (spec.get("path") or "").strip()
    if mode not in ("new", "existing", "import"):
        raise Refusal("pool_mode_unknown", f"unknown way to choose a pool: {mode!r}")
    if not path:
        raise Refusal("pool_folder_missing", "choose a folder for the question pool")
    folder = Path(path)
    if mode == "new":
        if (folder / POOL_FILE).exists():
            raise Refusal("pool_exists", f"{folder} already holds a question pool", path=folder)
        if not (spec.get("name") or "").strip():
            raise Refusal("pool_name_missing", "the question pool needs a name")
        if not [lang for lang in spec.get("languages") or [] if lang in LANGUAGES]:
            raise Refusal("pool_languages_missing", "choose at least one language")
    elif mode == "existing" and not (folder / POOL_FILE).exists():
        raise Refusal("pool_not_found", f"{folder} holds no question pool (pool.toml is missing)", path=folder)
    elif mode == "import" and not Path((spec.get("source") or "").strip()).is_file():
        raise Refusal("import_source_missing", "choose the pool.toml of the question bank to import")
    return folder


def _prepare_pool(spec: dict) -> tuple[Path, dict]:
    """Create, open or import the pool a module draws from. Returns its folder and what was done."""
    folder = _check_pool_spec(spec)
    if spec["mode"] == "new":
        languages = [lang for lang in spec["languages"] if lang in LANGUAGES]
        pool = Pool.create(folder, PoolSettings(name=spec["name"].strip(), languages=languages))
        return pool.root, {"pool": "created"}
    if spec["mode"] == "existing":
        return folder, {"pool": "opened"}
    report = import_pool(Path(spec["source"].strip()), folder)
    return folder, {"pool": "imported", "created": len(report.created), "conflicts": len(report.conflicts),
                    "problems": report.problems}


class Api:
    def __init__(self, window=None):
        self._window = window  # the pywebview window, for file dialogs; None when served over HTTP

    # --- basics ----------------------------------------------------------------------

    @_answer
    def info(self) -> dict:
        return {"version": __version__, "settings_file": str(user_settings.settings_file()),
                "dialogs": self._window is not None}

    @_answer
    def get_settings(self) -> dict:
        return user_settings.load().to_dict()

    @_answer
    def update_settings(self, changes: dict) -> dict:
        current = user_settings.load()
        current.update(changes)
        user_settings.save(current)
        return current.to_dict()

    @_answer
    def workspace(self) -> dict:
        current = user_settings.load()
        return {
            "modules": [_module_entry(p) for p in current.modules],
            "pools": [_pool_entry(p) for p in current.pools],
        }

    # --- folders -----------------------------------------------------------------------

    @_answer
    def pick_folder(self, start: str = "") -> str | None:
        """Windows folder dialog; None if cancelled. Only in the app window."""
        if self._window is None:
            raise Refusal("no_dialogs", "folder dialogs only work in the app window")
        import webview
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=start or "")
        return _norm(result[0]) if result else None

    @_answer
    def pick_file(self, start: str = "", kind: str = "pool") -> str | None:
        """Windows file dialog for a pool.toml or an image; None if cancelled. Only in the app window."""
        if self._window is None:
            raise Refusal("no_dialogs", "file dialogs only work in the app window")
        import webview
        types = {"pool": ("Markwise (pool.toml)",), "image": ("Images (*.png;*.svg;*.jpg;*.jpeg)",)}.get(kind, ())
        result = self._window.create_file_dialog(webview.FileDialog.OPEN, directory=start or "",
                                                 file_types=(*types, "All files (*.*)"))
        return _norm(result[0]) if result else None

    @_answer
    def inspect_folder(self, path: str) -> dict:
        """What a folder holds, so that the interface can say what opening it will do."""
        folder = Path(path)
        return {
            "path": _norm(folder) if path else "",
            "exists": folder.is_dir(),
            "module": (folder / MODULE_FILE).exists(),
            "pool": (folder / POOL_FILE).exists(),
            "empty": folder.is_dir() and not any(folder.iterdir()),
            "name": folder.name,
        }

    @_answer
    def reveal(self, path: str) -> None:
        """Show a folder in Windows Explorer."""
        if not Path(path).is_dir():
            raise Refusal("folder_missing", f"{path} does not exist", path=path)
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606 (opens Explorer on a folder the person chose)

    # --- modules -----------------------------------------------------------------------

    @_answer
    def create_module(self, spec: dict) -> dict:
        folder = Path((spec.get("folder") or "").strip())
        name, short_name = (spec.get("name") or "").strip(), (spec.get("short_name") or "").strip()
        if not name:
            raise Refusal("module_name_missing", "the module needs a name")
        if not short_name:
            raise Refusal("module_short_missing", "the module needs a short name")
        if not str(folder) or str(folder) == ".":
            raise Refusal("module_folder_missing", "choose a folder for the module")
        if (folder / MODULE_FILE).exists():
            raise Refusal("module_exists", f"{folder} already holds a module", path=folder)
        _check_pool_spec(spec.get("pool") or {})
        pool_root, outcome = _prepare_pool(spec["pool"])
        language = user_settings.load().language
        module = Module.create(folder, name, short_name, pools=[pool_root], exam_path=EXAM_PATHS.get(language, EXAM_PATHS["en"]))
        path = _norm(module.root)
        _remember_module(path)
        return {"module": _module_entry(path), **outcome}

    @_answer
    def open_module(self, path: str) -> dict:
        folder = Path(path)
        if not (folder / MODULE_FILE).exists():
            if (folder / POOL_FILE).exists():
                raise Refusal("is_pool", f"{folder} is a question pool, not a module", path=folder)
            raise Refusal("no_module", f"{folder} holds no module (module.toml is missing)", path=folder)
        path = _norm(folder)
        _remember_module(path)
        return _module_entry(path)

    @_answer
    def set_current_module(self, path: str) -> dict:
        current = user_settings.load()
        if path not in current.modules:
            raise Refusal("module_not_listed", f"{path} is not in the list of modules", path=path)
        current.current_module = path
        user_settings.save(current)
        return current.to_dict()

    @_answer
    def forget_module(self, path: str) -> dict:
        """Remove a module from the list; its folder and files stay untouched."""
        current = user_settings.load()
        current.modules = [p for p in current.modules if p != path]
        if current.current_module == path:
            current.current_module = current.modules[0] if current.modules else ""
        user_settings.save(current)
        return current.to_dict()

    @_answer
    def add_pool(self, module_path: str, pool_spec: dict) -> dict:
        module = Module.open(module_path)
        folder = _check_pool_spec(pool_spec)
        if folder.resolve() in [module.pool_root(ref) for ref in module.pools]:
            raise Refusal("pool_already_added", "the module already draws from this pool")
        pool_root, outcome = _prepare_pool(pool_spec)
        module.add_pool(pool_root)
        module.save()
        return {"module": _module_entry(module_path), **outcome}

    @_answer
    def set_pool_languages(self, pool_path: str, languages: list) -> dict:
        """Change the languages of a pool; reports how many questions then lack a text in an added language."""
        pool = Pool.open(pool_path)
        if not [lang for lang in languages if lang in LANGUAGES]:
            raise Refusal("pool_languages_missing", "choose at least one language")
        added = [lang for lang in LANGUAGES if lang in languages and lang not in pool.settings.languages]
        pool.set_languages(languages)
        questions, _ = pool.load()
        untranslated = sum(1 for q in questions if any(not str((q.data.get("stem") or {}).get(lang) or "").strip()
                                                       for lang in added))
        return {**_pool_entry(str(pool.root)), "added": added, "untranslated": untranslated}

    @_answer
    def remove_pool(self, module_path: str, pool_path: str) -> dict:
        """Detach a pool from the module; the pool itself stays untouched."""
        module = Module.open(module_path)
        module.remove_pool(pool_path)
        module.save()
        return _module_entry(module_path)

    # --- questions ---------------------------------------------------------------------

    @_answer
    def list_questions(self, module_path: str) -> dict:
        """All questions in the pools of a module, as rows for the list."""
        module = Module.open(module_path)
        language = user_settings.load().language
        pools, rows = [], []
        for ref in module.pools:
            root = module.pool_root(ref)
            if not (root / POOL_FILE).exists():
                pools.append({"path": str(root), "name": root.name, "exists": False})
                continue
            pool = Pool.open(root)
            pools.append({"path": str(root), "name": pool.settings.name, "exists": True,
                          "languages": pool.settings.languages, "concepts": pool.concept_info()})
            rows.extend(catalog.rows(pool, language))
        return {"pools": pools, "questions": rows}

    @_answer
    def get_question(self, pool_path: str, qid: str) -> dict:
        return catalog.detail(Pool.open(pool_path), qid)

    @_answer
    def open_file(self, path: str) -> None:
        """Open a question file in the program Windows uses for YAML files. Only files inside an opened pool."""
        target = Path(path).resolve()
        if target.suffix not in (".yaml", ".toml") or not target.is_file():
            raise Refusal("file_missing", f"{path} is not a question file", path=path)
        allowed = []
        for module_path in user_settings.load().modules:
            if (Path(module_path) / MODULE_FILE).exists():
                module = Module.open(module_path)
                allowed.extend(module.pool_root(ref) for ref in module.pools)
        if not any(root == target or root in target.parents for root in allowed):
            raise Refusal("file_outside", f"{path} is not in a pool of an opened module", path=path)
        if sys.platform == "win32":
            os.startfile(target)  # noqa: S606 (a question file inside an opened pool)

    @_answer
    def create_question(self, pool_path: str, concept: str, qtype: str, new_concept: dict | None = None) -> dict:
        """A new question from the template of its type, in an existing concept or in a new one given by
        name and short description (its identifier is made from the name)."""
        pool = Pool.open(pool_path)
        if qtype not in TYPES:
            raise Refusal("type_unknown", f"unknown type {qtype!r}")
        if new_concept:
            concept = self._add_concept(pool, new_concept.get("name", ""), new_concept.get("description", ""))
        if concept not in pool.concepts():
            raise Refusal("concept_unknown", f"the pool has no concept {concept}", concept=concept)
        question = pool.new_question(concept, qtype)
        return catalog.detail(pool, question.id)

    @staticmethod
    def _add_concept(pool: Pool, name: str, description: str) -> str:
        if not name.strip():
            raise Refusal("concept_name_missing", "the concept needs a name")
        if any(c["name"].lower() == name.strip().lower() for c in pool.concept_info()):
            raise Refusal("concept_exists", f"a concept named {name} exists already", name=name.strip())
        return pool.add_concept(name, description)

    @_answer
    def add_concept(self, pool_path: str, name: str, description: str = "") -> dict:
        pool = Pool.open(pool_path)
        cid = self._add_concept(pool, name, description)
        return next(c for c in pool.concept_info() if c["id"] == cid)

    @_answer
    def update_concept(self, pool_path: str, cid: str, name: str, description: str) -> dict:
        """Rename or describe a concept; its identifier, folder and questions stay."""
        pool = Pool.open(pool_path)
        if not name.strip():
            raise Refusal("concept_name_missing", "the concept needs a name")
        if any(c["name"].lower() == name.strip().lower() and c["id"] != cid for c in pool.concept_info()):
            raise Refusal("concept_exists", f"a concept named {name} exists already", name=name.strip())
        pool.update_concept(cid, name, description)
        return next(c for c in pool.concept_info() if c["id"] == cid)

    @_answer
    def concept_overview(self, module_path: str) -> list:
        """The concepts of all pools of a module, each with a summary of its questions."""
        module = Module.open(module_path)
        language = user_settings.load().language
        result = []
        for ref in module.pools:
            root = module.pool_root(ref)
            if (root / POOL_FILE).exists():
                result.extend(catalog.concept_overview(Pool.open(root), language))
        return result

    @_answer
    def delete_concept(self, pool_path: str, cid: str) -> None:
        """Remove a concept without questions."""
        try:
            Pool.open(pool_path).delete_concept(cid)
        except ValueError:
            raise Refusal("concept_not_empty", f"the concept {cid} still has questions", id=cid) from None

    @_answer
    def list_concepts(self, pool_path: str) -> list:
        """The concepts of a pool with their names, descriptions and number of questions."""
        pool = Pool.open(pool_path)
        counts: dict[str, int] = {}
        for path in pool.question_files():
            counts[path.parent.name] = counts.get(path.parent.name, 0) + 1
        return [{**c, "questions": counts.get(c["id"], 0)} for c in pool.concept_info()]

    @_answer
    def check_question(self, pool_path: str, qid: str, fields: dict) -> list:
        """Findings for the fields as they stand in the editor, before saving."""
        return editing.check_fields(Pool.open(pool_path), qid, fields)

    @_answer
    def save_question(self, pool_path: str, qid: str, fields: dict, mtime_ns: str | None = None,
                      force: bool = False) -> dict:
        pool = Pool.open(pool_path)
        try:
            question, changed = editing.save(pool, qid, fields, int(mtime_ns) if mtime_ns else None, force)
        except ConflictError:
            raise Refusal("conflict", "the file was changed elsewhere since you opened it", id=qid) from None
        return {"changed": changed, "question": catalog.detail(pool, question.id)}

    @_answer
    def list_images(self, pool_path: str) -> list:
        """The figures in the pool's images folder: name (as questions use it) and a preview."""
        pool = Pool.open(pool_path)
        return [{"name": name, "data": catalog.data_url(pool.image_file(name))} for name in pool.image_names()]

    @_answer
    def add_image(self, pool_path: str, source: str) -> dict:
        """Copy an image file into the pool, so that questions can show it."""
        source_path = Path((source or "").strip())
        if not source_path.is_file():
            raise Refusal("image_missing", "choose an image file", path=source)
        pool = Pool.open(pool_path)
        try:
            name = pool.add_image(source_path)
        except ValueError:
            raise Refusal("image_type", f"{source_path.name} is not a PNG, SVG or JPEG image", name=source_path.name) from None
        return {"name": name, "data": catalog.data_url(pool.image_file(name))}

    # --- release, variants, retiring ---------------------------------------------------

    @staticmethod
    def _step(step, pool_path: str, qid: str, *args) -> dict:
        pool = Pool.open(pool_path)
        try:
            question = step(pool, qid, *args)
        except lifecycle.LifecycleError as exc:
            raise Refusal(exc.code, str(exc), id=qid) from None
        return catalog.detail(pool, question.id)

    @_answer
    def release_question(self, pool_path: str, qid: str) -> dict:
        return self._step(lifecycle.release, pool_path, qid)

    @_answer
    def withdraw_release(self, pool_path: str, qid: str) -> dict:
        return self._step(lifecycle.withdraw, pool_path, qid)

    @_answer
    def create_variant(self, pool_path: str, qid: str) -> dict:
        return self._step(lifecycle.create_variant, pool_path, qid)

    @_answer
    def retire_question(self, pool_path: str, qid: str) -> dict:
        return self._step(lifecycle.retire, pool_path, qid)

    @_answer
    def restore_question(self, pool_path: str, qid: str) -> dict:
        return self._step(lifecycle.restore, pool_path, qid)

    @_answer
    def delete_question(self, pool_path: str, qid: str, variants: str | None = None) -> dict:
        """Delete a draft; anything else is retired, so that its identifier is never given again. A draft with
        variants is refused until `variants` says whether they are deleted too or become questions of their own."""
        pool = Pool.open(pool_path)
        try:
            return lifecycle.delete(pool, qid, variants)
        except lifecycle.LifecycleError as exc:
            ids = [q.id for q in pool.load()[0] if q.variant_of == qid]
            raise Refusal(exc.code, str(exc), id=qid, count=len(ids), ids=", ".join(sorted(ids))) from None

    @_answer
    def whoami(self) -> str:
        """The name Markwise notes on releases and changes."""
        from ..question import default_author
        return default_author()

    # --- help from a language model ----------------------------------------------------

    @staticmethod
    def _assist(step, *args):
        try:
            return step(*args)
        except assist.AssistError as exc:
            raise Refusal(exc.code, str(exc)) from None

    @_answer
    def llm_status(self) -> dict:
        current = user_settings.load()
        try:
            has_key = bool(assist.get_key())
        except Exception:  # no credential store available
            has_key = False
        found = "" if has_key else assist.env_key()
        return {"enabled": current.llm_enabled, "model": current.llm_model, "has_key": has_key,
                "env_key": assist.masked(found) if found else "", "env_var": assist.ENV_VAR}

    @_answer
    def set_llm_key(self, key: str) -> list:
        """Check the key with the provider, store it in the Windows credential store, return the models."""
        key = (key or "").strip()
        if not key:
            raise Refusal("llm_no_key", "enter an API key")
        models = self._assist(assist.list_models, key)
        assist.set_key(key)
        return models

    @_answer
    def use_env_llm_key(self) -> list:
        """Like set_llm_key with the key from the environment, which never passes through the interface."""
        key = assist.env_key()
        if not key:
            raise Refusal("llm_no_key", f"{assist.ENV_VAR} is not set")
        models = self._assist(assist.list_models, key)
        assist.set_key(key)
        return models

    @_answer
    def remove_llm_key(self) -> None:
        assist.remove_key()

    @_answer
    def llm_models(self) -> list:
        return self._assist(assist.list_models)

    @_answer
    def assist_review(self, pool_path: str, fields: dict, lang: str, known: list | None = None) -> dict:
        """Check a question with its answers and complete it: languages, feedback and missing wrong options.
        `known` are the findings of Markwise's own check as the editor shows them, for the model to act on."""
        pool = Pool.open(pool_path)
        return self._assist(assist.review, fields, pool.settings.languages, lang, user_settings.load().language,
                            pool.settings.min_options, assist.figures_for_model(pool, fields), known or [])

    @_answer
    def assist_vary_numbers(self, pool_path: str, fields: dict) -> dict:
        pool = Pool.open(pool_path)
        return self._assist(assist.vary_numbers, fields, pool.settings.languages, user_settings.load().language,
                            assist.figures_for_model(pool, fields))

    # --- exams -------------------------------------------------------------------------

    @staticmethod
    def _exam_entry(exam: Exam) -> dict:
        return {"path": str(exam.root), "title": exam.title, "date": exam.date, "semester": exam.semester,
                "language": exam.language, "answers": exam.answers, "questions": len(exam.questions),
                "points": exam.total_points()}

    @_answer
    def list_exams(self, module_path: str) -> list:
        """The exams of a module, newest first."""
        return [self._exam_entry(e) for e in sorted(exams_of(Module.open(module_path)), key=lambda e: e.date, reverse=True)]

    @_answer
    def create_exam(self, module_path: str, spec: dict) -> dict:
        if not (spec.get("title") or "").strip():
            raise Refusal("exam_title_missing", "the exam needs a title")
        if not spec.get("date"):
            raise Refusal("exam_date_missing", "the exam needs a date")
        try:
            exam = Exam.create(Module.open(module_path), spec["title"], spec["date"], spec.get("language") or "de",
                               spec.get("answers") or "sheet")
        except FileExistsError:
            raise Refusal("exam_exists", "an exam with this date and title exists already") from None
        return self._exam_detail(exam)

    def _exam_detail(self, exam: Exam) -> dict:
        module = Module.around(exam.root)
        entries = [{"section": item.id, "title": item.title, "note": item.note} if isinstance(item, ExamSection)
                   else {"pool": str(module.pool_root(item.pool)), "id": item.id, "points": item.points}
                   for item in exam.flat()]
        return {**self._exam_entry(exam), "examiners": exam.examiners, "entries": entries,
                "findings": [f.to_dict() for f in exam.check(module)], "printed": booklet.printed_files(exam)}

    @_answer
    def get_exam(self, exam_path: str) -> dict:
        return self._exam_detail(Exam.open(exam_path))

    @_answer
    def update_exam(self, exam_path: str, fields: dict) -> dict:
        """Change an exam: its settings, examiners, and its questions as [{pool, id, points}] in their order, with
        sections as {section, title, note} where they start."""
        exam = Exam.open(exam_path)
        module = Module.around(exam.root)
        if "title" in fields or "date" in fields:
            title = str(fields.get("title", exam.title)).strip()
            if not title:
                raise Refusal("exam_title_missing", "the exam needs a title")
            if not fields.get("date", exam.date):
                raise Refusal("exam_date_missing", "the exam needs a date")
            try:
                exam.rename(module, title, str(fields.get("date") or exam.date))
            except FileExistsError:
                raise Refusal("exam_exists", "an exam with this date and title exists already") from None
            except PermissionError:
                raise Refusal("exam_folder_busy", "a file in the exam folder is open in another program") from None
        if fields.get("language") in ("de", "en"):
            exam.language = fields["language"]
        if fields.get("answers") in ANSWER_MODES:
            exam.answers = fields["answers"]
        if "examiners" in fields:
            exam.examiners = [str(e).strip() for e in fields["examiners"] if str(e).strip()]
        if "entries" in fields:
            items: list[ExamQuestion | ExamSection] = []
            for e in fields["entries"]:
                if "section" in e:
                    items.append(ExamSection(str(e["section"] or exam.new_section_id()), str(e.get("title") or ""),
                                             str(e.get("note") or "")))
                else:
                    items.append(ExamQuestion(exam.pool_ref(module, e["pool"]), str(e["id"]), float(e["points"])))
            exam.set_flat(items)
        exam.save()
        return self._exam_detail(exam)

    @_answer
    def print_exam(self, exam_path: str, booklets: int) -> dict:
        """Typeset the booklets, the answer sheet and the answer key into the exam's print folder."""
        exam = Exam.open(exam_path)
        try:
            printed = booklet.print_exam(exam, booklets=booklets)
        except booklet.BookletError as exc:
            raise Refusal(exc.code, str(exc), **exc.params) from None
        return {**self._exam_detail(exam), "folder": str(printed.folder), "pages_per_booklet": printed.pages_per_booklet}

    @_answer
    def exam_items(self, lang: str, refs: list) -> dict:
        """Questions as the booklet shows them, in the exam's language and without the solution, for the exam page:
        `refs` are [{pool, id}]. A question that cannot be read comes back with `missing`."""
        lang = lang if lang in booklet.WORDS else "de"
        pools: dict[str, Pool] = {}
        items = []
        for ref in refs:
            pool_path, qid = str(ref["pool"]), str(ref["id"])
            try:
                pool = pools.get(pool_path) or pools.setdefault(pool_path, Pool.open(pool_path))
                item = booklet.item_of(pool, qid, lang)
            except (FileNotFoundError, KeyError, ValueError):
                items.append({"pool": pool_path, "id": qid, "missing": True})
                continue
            items.append({
                "pool": pool_path, "id": qid, "type": item.type, "stem": item.stem, "code": item.code,
                "code_language": item.code_language, "image_columns": item.image_columns, "lines": item.lines,
                "half_points": item.half_points, "options": [{"id": o["id"], "text": o["text"]} for o in item.options],
                "figures": [{"name": path.name, "data": catalog.data_url(path)} for path in item.figures],
            })
        words = booklet.WORDS[lang]
        return {"items": items, "words": {k: words[k] for k in ("question", "point", "points", "single", "multiple",
                                                                 "examiners_only")}}

    @_answer
    def open_printed(self, exam_path: str, name: str) -> None:
        """Open a PDF of the exam's last print in the program Windows uses for it."""
        files = {f["name"]: f["path"] for f in booklet.printed_files(Exam.open(exam_path))}
        if name not in files:
            raise Refusal("file_missing", f"{name} has not been printed", path=name)
        if sys.platform == "win32":
            os.startfile(files[name])  # noqa: S606 (a file Markwise wrote into the exam's print folder)

