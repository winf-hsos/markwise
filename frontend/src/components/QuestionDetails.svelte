<script>
  import Icon from "./Icon.svelte";
  import Menu from "./Menu.svelte";
  import TimeChoice from "./TimeChoice.svelte";
  import AssistChanges from "./AssistChanges.svelte";
  import CodeDialog from "./CodeDialog.svelte";
  import ImageDialog from "./ImageDialog.svelte";
  import { CODE_LANGUAGES, detectLanguage } from "../lib/highlight.js";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { llmReady, showToast } from "../lib/state.svelte.js";

  // The settings of a question below its text and answers, each saved the moment it changes: type, level, use,
  // time, the question a variant varies, figures and code, where the content is taught, and the help of the
  // language model. `data` is the question with what a variant inherits filled in, `lang` the language shown,
  // `practice` the practice questions of the pool, and `save(fields)` saves the fields it is given.
  let { question, data, lang, practice = [], save } = $props();

  const own = $derived(question.data);
  const inherited = $derived(question.inherited ?? {});
  const isVariant = $derived(Boolean(own.variant_of));
  const parentId = $derived(question.parent?.id ?? own.variant_of ?? "");
  const empty = (value) => value == null || value === "";
  const fromParent = (key) => isVariant && empty(own[key]) && inherited[key] != null;
  const isChoice = $derived(data.type === "single" || data.type === "multiple");
  const copy = (value) => JSON.parse(JSON.stringify(value ?? null));

  function setType(type) {
    const options = copy(own.options ?? []);
    if (type === "single") {
      let seen = false;
      for (const o of options) {
        o.correct = Boolean(o.correct) && !seen;
        seen ||= o.correct;
      }
    }
    save({ type, options });
  }

  // Practice and exam can both be on; at least one stays on. A practice question is no exam variant.
  const uses = $derived({ public: own.public === true, exam: typeof own.exam === "boolean" ? own.exam : !own.public });
  function toggleUse(which) {
    const next = { ...uses, [which]: !uses[which] };
    if (!next.public && !next.exam) return;
    save(next.public && own.variant_of ? { ...next, variant_of: "" } : next);
  }

  // A variant varies a question of the same kind: free text a free-text question, choice a choice question.
  const variantChoices = $derived(practice.filter((p) => p.concept === own.concept && p.id !== own.id
    && (p.type === "free_text") === (data.type === "free_text")));

  // The time is saved a moment after the last change, so that typing minutes and seconds saves once; until
  // then the choice shows what was chosen.
  let time = $state(undefined);
  let timeLater = null;
  $effect(() => {
    question.data.id;
    own.time_seconds;
    time = undefined;
  });
  function setTime(seconds) {
    time = seconds;
    clearTimeout(timeLater);
    timeLater = setTimeout(() => save({ time_seconds: seconds }), 500);
  }

  // --- figures and code ------------------------------------------------------------------------------------
  let codeOpen = $state(false);
  let imageOpen = $state(false);
  const images = $derived(Array.isArray(own.images) ? own.images : own.image ? [own.image] : []);
  const columns = $derived(Number.isInteger(own.image_columns) ? own.image_columns : 1);
  const languageName = (id) => CODE_LANGUAGES.find(([key]) => key === id)?.[1];
  const codeLanguageName = $derived(
    languageName(own.code_language) ??
      (languageName(detectLanguage(own.code ?? "")) ? t("attach.detected", { name: languageName(detectLanguage(own.code)) }) : t("attach.unknownLanguage")),
  );
  const codeLines = $derived(own.code ? own.code.split("\n").length : 0);
  const layoutName = $derived(
    images.length < 2 ? "" : columns === 1 ? t("attach.layoutRows")
      : columns >= images.length ? t("attach.layoutSide") : t("attach.layoutColumns", { n: columns }),
  );
  const addItems = $derived([
    { label: own.code ? t("attach.codeEdit") : t("attach.code"), icon: "code", onclick: () => (codeOpen = true) },
    { label: images.length ? t("attach.imageChange") : t("attach.image"), icon: "image", onclick: () => (imageOpen = true) },
  ]);

  // --- help from the language model, only when it is switched on in the settings --------------------------
  let review = $state(null);
  let numbers = $state(null);
  let asking = $state(""); // "review" or "numbers" while the model works

  async function askModel(kind, method, ...args) {
    asking = kind;
    try {
      return await call(method, question.pool, copy(data), ...args);
    } catch (err) {
      showToast(errorText(err));
      return null;
    } finally {
      asking = "";
    }
  }

  async function reviewQuestion() {
    // The errors and warnings of the check go along, so that the model proposes what to do about them.
    const known = question.findings.filter((f) => f.severity === "error" || f.severity === "warning");
    const answer = await askModel("review", "assist_review", lang, known);
    if (answer?.level) {
      const { before, proposed } = answer.level;
      answer.changes.push({ field: "level", lang: "", value: proposed, text: t(`level.${proposed}`),
        before: before ? t(`level.${before}`) : "" });
    }
    review = answer;
  }

  async function varyNumbers() {
    numbers = await askModel("numbers", "assist_vary_numbers");
  }

  function fieldLabel(name) {
    if (name === "question") return t("assist.aboutQuestion");
    if (name === "level") return t("edit.level");
    if (name === "stem") return t("edit.stem");
    if (name === "expected") return t("q.expected");
    if (name === "marking_notes") return t("q.markingNotes");
    const [, id, part] = name.split(".");
    return t(part === "text" ? "assist.aboutOption" : "assist.aboutFeedback", { id });
  }

  // Proposed texts go into the question in one save and leave the list they came from.
  function applyTo(result, chosen) {
    const fields = {};
    let options = null;
    for (const change of chosen) {
      if (change.field === "level") {
        fields.level = change.value;
      } else if (change.field.startsWith("option.")) {
        const [, id, part] = change.field.split(".");
        options ??= copy(own.options ?? []);
        const option = options.find((o) => o.id === id);
        if (option) option[part] = { ...(option[part] ?? {}), [change.lang]: change.text };
      } else {
        fields[change.field] = { ...(fields[change.field] ?? copy(own[change.field]) ?? {}), [change.lang]: change.text };
      }
    }
    if (options) fields.options = options;
    save(fields);
    result.changes = result.changes.filter((c) => !chosen.some((x) => x.field === c.field && x.lang === c.lang));
  }

  // New wrong options the check proposed because the question had too few.
  function addOptions(result, chosen) {
    const options = copy(own.options ?? []);
    for (const option of chosen) {
      const used = new Set(options.map((o) => o.id));
      const id = "abcdefghij".split("").find((c) => !used.has(c));
      if (!id) break;
      options.push({ id, correct: false, text: { ...option.text }, feedback: { ...option.feedback } });
    }
    save({ options });
    result.new_options = result.new_options.filter((o) => !chosen.includes(o));
  }
</script>

<!-- Next to a setting of a variant: inherited from the parent, or its own value with a way back. -->
{#snippet heritage(key)}
  {#if isVariant && inherited[key] != null && fromParent(key)}
    <span class="heritage" title={t("edit.inheritedHint", { id: parentId })}>{t("edit.inherited", { id: parentId })}</span>
  {:else if isVariant && inherited[key] != null}
    <button type="button" class="heritage own" title={t("edit.inheritAgainHint", { id: parentId })}
      onclick={() => save({ [key]: key === "coverage" || key === "misconception" ? "" : null })}>{t("edit.inheritAgain")}</button>
  {/if}
{/snippet}

<section class="preview-section details-panel">
  <div class="form-grid">
    {#if isChoice}
      <div class="field">
        <span class="field-label">{t("edit.type")}{@render heritage("type")}</span>
        <div class="seg seg-small" role="group" aria-label={t("edit.type")}>
          {#each ["single", "multiple"] as v}
            <button type="button" class:on={data.type === v} class:inherited={fromParent("type")} onclick={() => setType(v)}>{t(`type.${v}`)}</button>
          {/each}
        </div>
      </div>
    {/if}
    <div class="field">
      <span class="field-label">{t("edit.level")}{@render heritage("level")}</span>
      <div class="seg seg-small" role="group" aria-label={t("edit.level")}>
        {#each ["remember", "understand", "apply"] as v}
          <button type="button" class:on={data.level === v} class:inherited={fromParent("level")} onclick={() => save({ level: v })}>{t(`level.${v}`)}</button>
        {/each}
      </div>
    </div>
    {#if !isVariant}
      <div class="field">
        <span>{t("edit.use")}</span>
        <div class="chips" role="group" aria-label={t("edit.use")}>
          <button type="button" class="chip" class:on={uses.public} aria-pressed={uses.public} onclick={() => toggleUse("public")}>{t("use.practice")}</button>
          <button type="button" class="chip" class:on={uses.exam} aria-pressed={uses.exam} onclick={() => toggleUse("exam")}>{t("use.exam")}</button>
        </div>
      </div>
    {/if}
    <div class="field">
      <span class="field-label">{t("edit.time")}{@render heritage("time_seconds")}</span>
      {#key question.pool + question.data.id}
        <TimeChoice bind:value={() => (time === undefined ? own.time_seconds ?? null : time), setTime} inherited={isVariant ? inherited.time_seconds ?? null : null} />
      {/key}
    </div>
    {#if !uses.public}
      <label class="field">
        <span>{t("edit.variantOf")}</span>
        <select class="select select-small" value={own.variant_of ?? ""} onchange={(e) => save({ variant_of: e.currentTarget.value })}>
          <option value="">{t("edit.noVariant")}</option>
          {#if own.variant_of && !variantChoices.some((p) => p.id === own.variant_of)}<option value={own.variant_of}>{own.variant_of}</option>{/if}
          {#each variantChoices as p}<option value={p.id}>{p.id}: {p.stem.slice(0, 60)}</option>{/each}
        </select>
      </label>
    {/if}
    {#if data.type === "free_text"}
      <label class="field"><span class="field-label">{t("edit.lines")}{@render heritage("lines")}</span>
        <input class="input input-small" type="number" min="1" value={own.lines ?? ""} style="width: 90px"
          placeholder={isVariant && inherited.lines != null ? String(inherited.lines) : ""}
          onchange={(e) => save({ lines: e.currentTarget.value ? Number(e.currentTarget.value) : null })} /></label>
      <label class="check-line"><input type="checkbox" checked={data.half_points === true}
        onchange={(e) => save({ half_points: e.currentTarget.checked })} />{t("edit.halfPoints")}{@render heritage("half_points")}</label>
    {/if}
  </div>

  <div class="attachments">
    {#if own.code}
      <div class="attachment-card">
        <span class="attachment-icon"><Icon name="code" /></span>
        <span class="attachment-text"><b>{t("attach.code")}</b><span>{codeLanguageName} · {t(codeLines === 1 ? "attach.line" : "attach.lines", { n: codeLines })}</span></span>
        <button type="button" class="icon-btn" title={t("attach.codeEdit")} aria-label={t("attach.codeEdit")} onclick={() => (codeOpen = true)}><Icon name="edit" /></button>
        <button type="button" class="icon-btn danger" title={t("attach.removeCode")} aria-label={t("attach.removeCode")} onclick={() => save({ code: "", code_language: "" })}><Icon name="trash" /></button>
      </div>
    {/if}
    {#if images.length}
      <div class="attachment-card">
        <span class="attachment-thumbs">
          {#each (question.figures ?? []).slice(0, 3) as f (f.name)}
            <span class="attachment-icon">{#if f.data}<img src={f.data} alt="" />{:else}<Icon name="image" />{/if}</span>
          {/each}
        </span>
        <span class="attachment-text">
          <b>{images.length === 1 ? t("edit.image") : t("attach.figures", { n: images.length })}</b>
          <span>{images.length === 1 ? images[0] : layoutName}</span>
        </span>
        <button type="button" class="icon-btn" title={t("attach.imageChange")} aria-label={t("attach.imageChange")} onclick={() => (imageOpen = true)}><Icon name="edit" /></button>
        <button type="button" class="icon-btn danger" title={t("attach.removeImages")} aria-label={t("attach.removeImages")} onclick={() => save({ images: [], image_columns: 1 })}><Icon name="trash" /></button>
      </div>
    {/if}
    <Menu buttonLabel={t("sheet.attach")} items={addItems} align="left" />
  </div>

  <div class="form-grid single details-more">
    <label class="field"><span class="field-label">{t("edit.coverage")}{@render heritage("coverage")}</span>
      <input class="input" value={own.coverage ?? ""} placeholder={isVariant ? inherited.coverage ?? "" : ""}
        onchange={(e) => save({ coverage: e.currentTarget.value.trim() })} /></label>
    <label class="field"><span class="field-label">{t("edit.misconception")}{@render heritage("misconception")}</span>
      <input class="input" value={own.misconception ?? ""} placeholder={isVariant ? inherited.misconception ?? "" : ""}
        onchange={(e) => save({ misconception: e.currentTarget.value.trim() })} /></label>
  </div>

  {#if llmReady()}
    <div class="details-assist">
      <button type="button" class="btn ghost btn-small" onclick={reviewQuestion}
        disabled={Boolean(asking) || Object.values(own.stem ?? {}).every((s) => !String(s ?? "").trim())}
        title={t(isChoice ? "assist.reviewHint" : "assist.reviewHintFree")}>
        <Icon name="wand" />{asking === "review" ? t("assist.working") : t("assist.review")}
      </button>
      {#if isVariant && data.type === "free_text"}
        <button type="button" class="btn ghost btn-small" onclick={varyNumbers} disabled={Boolean(asking)} title={t("assist.numbersHint")}>
          <Icon name="wand" />{asking === "numbers" ? t("assist.working") : t("assist.numbers")}
        </button>
      {/if}
      {#if asking}<span class="spinner" aria-hidden="true"></span><span class="hint">{t("assist.busyHint")}</span>{/if}
    </div>
    {#if review}
      <AssistChanges findings={review.findings} changes={review.changes} additions={review.new_options}
        title={t("assist.reviewTitle")} label={fieldLabel} showLang={question.languages.length > 1}
        onapply={(chosen) => applyTo(review, chosen)} onadd={(chosen) => addOptions(review, chosen)} onclose={() => (review = null)} />
    {/if}
    {#if numbers}
      <AssistChanges findings={numbers.findings} changes={numbers.changes} title={t("assist.numbersTitle")} label={fieldLabel}
        showLang={question.languages.length > 1} note={{ title: t("assist.calculation"), text: numbers.calculation }}
        onapply={(chosen) => applyTo(numbers, chosen)} onclose={() => (numbers = null)} />
    {/if}
  {/if}
</section>

<CodeDialog bind:open={codeOpen} code={own.code ?? ""} language={own.code_language ?? ""} onapply={(code, language) => save({ code, code_language: language })} />
<ImageDialog bind:open={imageOpen} pool={question.pool} current={images} {columns}
  onapply={(chosen, cols) => save({ images: chosen.map((f) => f.name), image_columns: cols })} />
