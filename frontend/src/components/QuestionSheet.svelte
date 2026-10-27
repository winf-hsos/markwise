<script>
  import QuestionPreview from "./QuestionPreview.svelte";
  import { ask } from "../lib/confirm.svelte.js";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { showToast } from "../lib/state.svelte.js";
  import { setDetails, sheet } from "../lib/sheet.svelte.js";

  // One question to read and change in place, the same on the Questions page and from an exam: every change is
  // saved at once, in the order it was made, and the steps of its life (release, withdraw, retire, take back,
  // variant, delete) run from here. `question` is the question as get_question gives it and follows every save;
  // `saving` counts the saves under way. The page hears of the rest: `onchanged` once the changes pause, so that
  // it reads the pools again; `onvariant(question)` with a variant just created, which the sheet then shows;
  // `ondeleted(pool, ids)` with the questions a deletion removed. `variants` names the variants of a practice
  // question, `practice` the practice questions of its pool, `language` the language to show first, and `fresh`
  // opens the text of a question just created for typing.
  let { question = $bindable(), saving = $bindable(0), variants = [], practice = [], language = null, fresh = false,
    onchanged, onvariant, ondeleted } = $props();

  let queue = Promise.resolve();
  let later = null;
  function changedSoon() {
    // The pools are read again once the edits pause, so that reading does not hold up the next save.
    clearTimeout(later);
    later = setTimeout(() => onchanged?.(), 900);
  }

  const same = (q, pool, id) => q?.pool === pool && q?.id === id;

  function saveFields(fields) {
    const { pool, id } = question;
    const since = question.mtime_ns;
    saving += 1;
    queue = queue.then(async () => {
      try {
        // The file's time from the last save of this question, so that saves in a row do not take each other for
        // edits made elsewhere.
        const mtime = same(question, pool, id) ? question.mtime_ns : since;
        const result = await call("save_question", pool, id, fields, mtime, false);
        if (same(question, pool, id)) question = result.question;
        if (result.changed) {
          showToast(t("edit.saved"));
          changedSoon();
        }
      } catch (err) {
        showToast(err.code === "conflict" ? t("sheet.conflict") : errorText(err));
        if (same(question, pool, id)) {
          try {
            question = await call("get_question", pool, id); // what is in the file now
          } catch {
            /* the question is gone; the page notices when it reads the pools again */
          }
        }
      } finally {
        saving -= 1;
      }
    });
  }

  async function act(name) {
    const { pool, id } = question;
    if (name === "retire" && !(await ask({ title: t("life.retireTitle", { id }), message: t("life.confirmRetire", { id }), action: t("life.retire") }))) return;
    // Deleting a question that has variants asks what becomes of them: deleted too, or questions of their own.
    let withVariants = null;
    if (name === "delete" && variants.length && question.data.status === "draft") {
      const n = variants.length;
      withVariants = await ask({
        title: t("life.deleteTitle", { id }),
        message: t(n === 1 ? "life.deleteWithVariant" : "life.deleteWithVariants", { id, n, ids: variants.join(", ") }),
        choices: [
          { value: "detach", label: t("life.keepVariants") },
          { value: "delete", label: t(n === 1 ? "life.deleteVariant" : "life.deleteVariants"), danger: true },
        ],
      });
      if (!withVariants) return;
    } else if (name === "delete" && !(await ask({ title: t("life.deleteTitle", { id }), message: t("life.confirmDelete", { id }), action: t("life.delete"), danger: true }))) return;
    try {
      if (name === "delete") {
        const result = await call("delete_question", pool, id, withVariants);
        const done = t(result.outcome === "deleted" ? "life.deleted" : "life.retiredToast", { id });
        const detached = result.variants.filter((v) => v.new_id).map((v) => v.new_id);
        showToast(detached.length ? t("life.variantsDetached", { done, ids: detached.join(", ") })
          : result.variants.length ? t("life.variantsDeleted", { done, n: result.variants.length }) : done);
        ondeleted?.(pool, [id, ...result.variants.map((v) => v.id)]);
        return;
      }
      const method = { release: "release_question", withdraw: "withdraw_release", variant: "create_variant",
        retire: "retire_question", restore: "restore_question" }[name];
      const result = await call(method, pool, id);
      question = result;
      if (name === "variant") {
        setDetails(true); // what makes the variant differ is in the details
        showToast(t("life.variantCreated", { id: result.id }));
        onvariant?.(result);
      } else {
        showToast(t(`life.${name}Toast`, { id }));
      }
      onchanged?.();
    } catch (err) {
      showToast(errorText(err));
    }
  }

  // Another concept: the question moves there in its pool, with its exam variants; its identifier stays.
  async function move(concept) {
    try {
      const result = await call("move_question", question.pool, question.id, concept);
      const others = result.moved.length - 1;
      question = result;
      showToast(t(others ? "conceptPick.movedWith" : "conceptPick.moved", { id: result.id, name: result.concept_name, n: others }));
      onchanged?.();
    } catch (err) {
      showToast(errorText(err));
    }
  }

  async function openFile(path) {
    try {
      await call("open_file", path);
    } catch (err) {
      showToast(errorText(err));
    }
  }
</script>

<QuestionPreview {question} {variants} {practice} {language} {fresh} me={sheet.me} editable onchange={saveFields}
  bind:details={() => sheet.details, setDetails} onopen={openFile} onaction={act} onmove={move} />
