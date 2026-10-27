"""The life of a question after writing it: release by examiners, exam variants, retiring and taking back.

None of these count as a change of content: they leave changed_by alone and never send a question back to draft
the way editing does.
"""

from __future__ import annotations

import copy

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .checks import ERROR, check_question
from .pool import Pool
from .question import INHERITED, Question, default_author, insert_field, ordered, today


class LifecycleError(Exception):
    """A step that does not fit the question's state; `code` names the reason for the interface."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _author(author: str | None) -> str:
    name = (default_author() if author is None else author).strip()
    if not name:
        raise LifecycleError("name_missing", "enter your name in the settings first")
    return name


def _set(question: Question, key: str, value) -> None:
    """Set a field in its usual place, after the fields that come before it."""
    if key in question.data:
        question.data[key] = value
        return
    insert_field(question.data, key, value)


def release(pool: Pool, qid: str, author: str | None = None) -> Question:
    """Add the examiner to released_by and make the question released. A question with errors cannot be released."""
    name = _author(author)
    question = pool.find(qid)
    if question.status == "retired":
        raise LifecycleError("retired", f"{qid} is retired")
    if any(f.severity == ERROR for f in check_question(question, pool)):
        raise LifecycleError("has_errors", f"{qid} has errors; correct them before releasing it")
    reviewers = [str(r) for r in question.data.get("released_by") or []]
    if name not in reviewers:
        reviewers.append(name)
    _set(question, "released_by", CommentedSeq(reviewers))
    if question.status == "draft":
        question.data["status"] = "released"
    question.save()
    return question


def withdraw(pool: Pool, qid: str, author: str | None = None) -> Question:
    """Take back the examiner's own release; without any release left, the question is a draft again."""
    name = _author(author)
    question = pool.find(qid)
    reviewers = [str(r) for r in question.data.get("released_by") or []]
    if name not in reviewers:
        raise LifecycleError("not_released_by_you", f"{qid} was not released by {name}")
    reviewers.remove(name)
    if reviewers:
        question.data["released_by"] = CommentedSeq(reviewers)
    else:
        del question.data["released_by"]
        if question.status == "released":
            question.data["status"] = "draft"
    question.save()
    return question


def create_variant(pool: Pool, qid: str, author: str | None = None) -> Question:
    """A new exam question in the same concept: its texts start as a copy of the practice question it varies,
    its settings (type, level, time and the like) are inherited from that question until it sets its own."""
    original = pool.find(qid)
    if not original.public:
        raise LifecycleError("not_practice", f"{qid} is not a practice question")
    if original.variant_of:
        raise LifecycleError("is_variant", f"{qid} is itself an exam variant")
    name = default_author() if author is None else author
    new_id = pool.next_variant_id(original.id)
    skip = {"id", "status", "public", "exam", "variant_of", "released_by", "created_by", "created_at",
            "changed_by", "changed_at", *INHERITED}
    fields = {key: copy.deepcopy(value) for key, value in original.data.items() if key not in skip}
    fields.update(id=new_id, status="draft", public=False, variant_of=original.id)
    if name:
        fields.update(created_by=name, created_at=today())
    data: CommentedMap = ordered(fields)
    variant = Question(data)
    variant.save(pool.path_for(original.concept, new_id))
    return variant


VARIANT_CHOICES = ("delete", "detach")


def _settle(variant: Question) -> None:
    """Write the settings a variant inherits into its own file, for when its parent goes away."""
    for key, value in variant.inherited().items():
        insert_field(variant.data, key, copy.deepcopy(value))


def _detach(pool: Pool, variant: Question, new_id: str) -> None:
    """Make a variant a question of its own: its inherited settings become its own, it gets an ordinary
    identifier, and it stays meant for exams only."""
    _settle(variant)
    del variant.data["variant_of"]
    variant.data["id"] = new_id
    old_path = variant.path
    variant.save(pool.path_for(variant.concept, new_id))
    old_path.unlink()


def delete(pool: Pool, qid: str, variants: str | None = None, used_in_exam: bool = False) -> dict:
    """Delete a draft that never was in an exam; retire anything else. If a deleted question has variants, `variants`
    says what becomes of them: "delete" deletes each one the same way (retiring those that are not drafts),
    "detach" makes them questions of their own with new identifiers."""
    question = pool.find(qid)
    removes = not used_in_exam and question.status == "draft"
    children = sorted((q for q in pool.load()[0] if q.variant_of == qid), key=lambda q: q.id) if removes else []
    if children and variants not in VARIANT_CHOICES:
        raise LifecycleError("has_variants", f"{qid} has {len(children)} variants: delete them too or detach them "
                                             f"(--variants delete|detach)")
    result = {"id": qid, "variants": []}
    if variants == "detach":
        prefix = pool.prefix_for(question.concept)
        for child in children:
            old_id, new_id = child.id, pool.next_id(prefix)  # numbered before the parent goes, so it is never reused
            _detach(pool, child, new_id)
            result["variants"].append({"id": old_id, "outcome": "detached", "new_id": new_id})
    result["outcome"] = pool.delete(qid, used_in_exam)
    if variants == "delete":
        for child in children:
            _settle(child)  # a variant that is retired rather than deleted keeps readable settings
            child.save()
            result["variants"].append({"id": child.id, "outcome": pool.delete(child.id, used_in_exam)})
    return result


def retire(pool: Pool, qid: str) -> Question:
    """Keep the question but take it out of every new exam; its identifier is never given again."""
    question = pool.find(qid)
    question.data["status"] = "retired"
    question.save()
    return question


def restore(pool: Pool, qid: str) -> Question:
    """Take a retired question back, as a draft that needs a new release."""
    question = pool.find(qid)
    if question.status != "retired":
        raise LifecycleError("not_retired", f"{qid} is not retired")
    question.data["status"] = "draft"
    if "released_by" in question.data:
        del question.data["released_by"]
    question.save()
    return question
