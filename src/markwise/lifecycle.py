"""The life of a question after writing it: release by examiners, exam variants, retiring and taking back.

None of these count as a change of content: they leave changed_by alone and never send a question back to draft
the way editing does.
"""

from __future__ import annotations

import copy

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .checks import ERROR, check_question
from .pool import Pool
from .question import INHERITED, Question, default_author, ordered, today


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
    from .editing import _insert
    _insert(question.data, key, value)


def release(pool: Pool, qid: str, author: str | None = None) -> Question:
    """Add the examiner to reviewed_by and make the question reviewed. A question with errors cannot be released."""
    name = _author(author)
    question = pool.find(qid)
    if question.status == "retired":
        raise LifecycleError("retired", f"{qid} is retired")
    if any(f.severity == ERROR for f in check_question(question, pool)):
        raise LifecycleError("has_errors", f"{qid} has errors; correct them before releasing it")
    reviewers = [str(r) for r in question.data.get("reviewed_by") or []]
    if name not in reviewers:
        reviewers.append(name)
    _set(question, "reviewed_by", CommentedSeq(reviewers))
    if question.status == "draft":
        question.data["status"] = "reviewed"
    question.save()
    return question


def withdraw(pool: Pool, qid: str, author: str | None = None) -> Question:
    """Take back the examiner's own release; without any release left, the question is a draft again."""
    name = _author(author)
    question = pool.find(qid)
    reviewers = [str(r) for r in question.data.get("reviewed_by") or []]
    if name not in reviewers:
        raise LifecycleError("not_released_by_you", f"{qid} was not released by {name}")
    reviewers.remove(name)
    if reviewers:
        question.data["reviewed_by"] = CommentedSeq(reviewers)
    else:
        del question.data["reviewed_by"]
        if question.status == "reviewed":
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
    skip = {"id", "status", "public", "exam", "variant_of", "reviewed_by", "created_by", "created_at",
            "changed_by", "changed_at", *INHERITED}
    fields = {key: copy.deepcopy(value) for key, value in original.data.items() if key not in skip}
    fields.update(id=new_id, status="draft", public=False, variant_of=original.id)
    if name:
        fields.update(created_by=name, created_at=today())
    data: CommentedMap = ordered(fields)
    variant = Question(data)
    variant.save(pool.path_for(original.concept, new_id))
    return variant


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
    if "reviewed_by" in question.data:
        del question.data["reviewed_by"]
    question.save()
    return question
