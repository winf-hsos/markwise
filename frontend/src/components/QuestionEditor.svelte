<script>
  import { untrack } from "svelte";
  import Icon from "./Icon.svelte";
  import QuestionPreview from "./QuestionPreview.svelte";
  import Menu from "./Menu.svelte";
  import TimeChoice from "./TimeChoice.svelte";
  import AssistChanges from "./AssistChanges.svelte";
  import { inline } from "../lib/inline.js";
  import CodeDialog from "./CodeDialog.svelte";
  import ImageDialog from "./ImageDialog.svelte";
  import { CODE_LANGUAGES, detectLanguage } from "../lib/highlight.js";
  import { ask } from "../lib/confirm.svelte.js";
  import { call } from "../lib/api.js";
  import { errorText, t, ui } from "../lib/i18n.svelte.js";
  import { llmReady, showToast } from "../lib/state.svelte.js";

  // Edits one question: form on the left, the question as it reads on the right, checked while typing.
  // `practice` lists the practice questions of the same pool for the variant choice.
  // `draft` brings back unsaved changes from an earlier visit; `ondraft` hears of every change while unsaved.
  // `back` names where closing leads, the question list unless the editor was opened from elsewhere;
  // with `saveOnBack`, going back saves first instead of asking whether to discard.
  let { question, practice = [], onclose, onsaved, draft = null, ondraft, back = "", saveOnBack = false } = $props();
  let shell; // the editor's element: pages stay open in the background, and a hidden editor must not save
  // The editor is created anew for every question (see {#key} in the page), so it starts from this snapshot.
  const initial = untrack(() => question);
  const kept = untrack(() => draft);

  const EDITABLE = ["type", "level", "public", "exam", "variant_of", "coverage", "misconception", "stem", "images", "image_columns", "code",
    "code_language", "options", "time_seconds", "half_points", "lines", "expected", "marking_notes"];
  const languages = initial.languages;
  const blankTexts = () => Object.fromEntries(languages.map((l) => [l, ""]));
  // A variant takes these settings from the question it varies, unless it sets its own; empty here means inherited.
  const inherited = initial.inherited ?? {};
  const parentId = initial.parent?.id ?? initial.data.variant_of ?? "";

  function editable(data) {
    const fields = {};
    for (const key of EDITABLE) if (key in data) fields[key] = JSON.parse(JSON.stringify(data[key])); // data may be reactive state
    // Every text map gets every language, so that the form has a field for each.
    for (const key of ["stem", "expected", "marking_notes"]) {
      if (key in fields || (key === "stem")) fields[key] = { ...blankTexts(), ...(fields[key] ?? {}) };
    }
    // Optional fields as empty strings, so that inputs bind to them; the core drops empty optional fields.
    for (const key of ["variant_of", "coverage", "misconception", "code", "code_language"]) fields[key] ??= "";
    fields.time_seconds ??= null;
    if (data.variant_of) {
      fields.type ??= null;
      fields.level ??= null;
      if ((data.type ?? inherited.type) === "free_text") {
        fields.lines ??= null;
        fields.half_points ??= null;
      }
    }
    // One figure is stored as `image`, several as `images`; the editor always works with the list.
    fields.images = Array.isArray(data.images) ? [...data.images] : data.image ? [data.image] : [];
    fields.image_columns = Number.isInteger(data.image_columns) ? data.image_columns : 1;
    // Without the field, exam questions are exactly those not shown for practice.
    fields.public = data.public === true;
    fields.exam = typeof data.exam === "boolean" ? data.exam : !fields.public;
    for (const option of fields.options ?? []) {
      option.text = { ...blankTexts(), ...(option.text ?? {}) };
      option.feedback = { ...blankTexts(), ...(option.feedback ?? {}) };
    }
    return fields;
  }

  // Unsaved changes from an earlier visit keep the file time they were made against, so that a change
  // elsewhere since then still counts as a conflict on saving.
  let base = $state(kept ? { ...initial, mtime_ns: kept.mtime_ns } : initial);
  let fields = $state(kept ? kept.fields : editable(initial.data));
  let saved = $state(JSON.stringify(editable(initial.data)));
  let lang = $state(languages.includes(ui.lang) ? ui.lang : languages[0]);
  let findings = $state(initial.findings);
  // Attachments below the question text, each added and changed in a dialog of its own.
  let codeOpen = $state(false);
  let imageOpen = $state(false);
  // Previews of the figures by name, so that the editor can show figures chosen since the last save.
  let figureData = $state(Object.fromEntries((initial.figures ?? []).map((f) => [f.name, f.data])));
  let conflict = $state(false);
  let busy = $state(false);

  const dirty = $derived(JSON.stringify(fields) !== saved);
  const isVariant = $derived(Boolean(fields.variant_of));
  const fromParent = (key) => isVariant && (fields[key] == null || fields[key] === "") && inherited[key] != null;
  const effective = (key) => (fromParent(key) ? inherited[key] : fields[key]);
  const qtype = $derived(effective("type"));
  const isChoice = $derived(qtype === "single" || qtype === "multiple");
  // A variant varies a question of the same kind: free text a free-text question, choice a choice question.
  const variantChoices = $derived(practice.filter((p) => p.concept === base.data.concept && p.id !== base.data.id
    && (p.type === "free_text") === (qtype === "free_text")));

  // Languages in which a required text is still empty, for the marks on the language tabs.
  const missing = $derived(
    languages.filter((l) =>
      !fields.stem?.[l]?.trim() ||
      (isChoice && (fields.options ?? []).some((o) => !o.text?.[l]?.trim())) ||
      (qtype === "free_text" && !fields.expected?.[l]?.trim()),
    ),
  );

  // Keep unsaved changes for the next visit; forget them once saved or discarded.
  $effect(() => {
    const snapshot = $state.snapshot(fields);
    const unsaved = JSON.stringify(snapshot) !== saved;
    untrack(() => ondraft?.(unsaved ? { fields: snapshot, mtime_ns: base.mtime_ns } : null));
  });

  // Check while typing, a moment after the last keystroke.
  let timer = null;
  $effect(() => {
    const snapshot = $state.snapshot(fields);
    clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        findings = await call("check_question", base.pool, base.data.id, snapshot);
      } catch {
        /* the next keystroke tries again */
      }
    }, 300);
    return () => clearTimeout(timer);
  });

  const figures = $derived(fields.images.map((name) => ({ name, data: figureData[name] ?? null })));
  const preview = $derived({ ...base, data: { ...base.data, ...fields }, findings, figures, image_columns: fields.image_columns });
  const layoutName = $derived(
    fields.images.length < 2 ? "" : fields.image_columns === 1 ? t("attach.layoutRows")
      : fields.image_columns >= fields.images.length ? t("attach.layoutSide") : t("attach.layoutColumns", { n: fields.image_columns }),
  );

  const languageName = (id) => CODE_LANGUAGES.find(([key]) => key === id)?.[1];
  const codeLanguageName = $derived(
    languageName(fields.code_language) ??
      (languageName(detectLanguage(fields.code)) ? t("attach.detected", { name: languageName(detectLanguage(fields.code)) }) : t("attach.unknownLanguage")),
  );
  const codeLines = $derived(fields.code ? fields.code.split("\n").length : 0);
  const addItems = $derived([
    { label: fields.code ? t("attach.codeEdit") : t("attach.code"), icon: "code", onclick: () => (codeOpen = true) },
    { label: fields.images.length ? t("attach.imageChange") : t("attach.image"), icon: "image", onclick: () => (imageOpen = true) },
    { label: t("attach.formula"), icon: "formula", disabled: true, hint: t("attach.soon"), onclick: () => {} },
  ]);

  function setCorrect(option) {
    if (qtype === "single") for (const o of fields.options) o.correct = o === option;
    else option.correct = !option.correct;
  }

  function addOption() {
    const used = new Set(fields.options.map((o) => o.id));
    const id = "abcdefghij".split("").find((c) => !used.has(c));
    fields.options.push({ id, correct: false, text: blankTexts(), feedback: blankTexts() });
  }

  function removeOption(option) {
    fields.options = fields.options.filter((o) => o !== option);
  }

  function setType(type) {
    fields.type = type;
    // Single choice keeps only the first correct option.
    if (type === "single") {
      let seen = false;
      for (const o of fields.options) {
        o.correct = o.correct && !seen;
        seen ||= o.correct;
      }
    }
  }

  // Practice and exam can both be on; at least one stays on. A practice question is no exam variant.
  function toggleUse(which) {
    const next = { public: fields.public, exam: fields.exam, [which]: !fields[which] };
    if (!next.public && !next.exam) return;
    fields.public = next.public;
    fields.exam = next.exam;
    if (fields.public) fields.variant_of = "";
  }

  // Help from the language model, only when it is switched on in the settings. One check looks at the whole question
  // in every language of the pool and completes it; its answer: { findings: [{about, text}],
  // changes: [{field, lang, text, before}], new_options: [{text, feedback, misconception}] }.
  let review = $state(null);
  let asking = $state(""); // "review" or "numbers" while the model works

  // The question as the model has to see it: a variant with the settings it inherits filled in.
  function effectiveFields() {
    const snapshot = $state.snapshot(fields);
    for (const [key, value] of Object.entries(inherited)) {
      if (isVariant && (snapshot[key] == null || snapshot[key] === "")) snapshot[key] = value;
    }
    return snapshot;
  }

  async function askModel(kind, method, ...args) {
    asking = kind;
    try {
      return await call(method, base.pool, effectiveFields(), ...args);
    } catch (err) {
      showToast(errorText(err));
      return null;
    } finally {
      asking = "";
    }
  }

  async function reviewQuestion() {
    // The errors and warnings of the check go along, so that the model proposes what to do about them.
    const known = $state.snapshot(findings).filter((f) => f.severity === "error" || f.severity === "warning");
    const answer = await askModel("review", "assist_review", lang, known);
    if (answer?.level) {
      // A different level appears among the proposals like a text, and applying it sets the question's own level.
      const { before, proposed } = answer.level;
      answer.changes.push({ field: "level", lang: "", value: proposed, text: t(`level.${proposed}`),
        before: before ? t(`level.${before}`) : "" });
    }
    review = answer;
  }

  // For a free-text variant: the same calculation with other numbers, the answer worked out again.
  let numbers = $state(null);

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

  // Put proposed texts into the form and take them off the list they came from.
  function applyTo(result, chosen) {
    for (const change of chosen) {
      if (change.field === "level") {
        fields.level = change.value;
      } else if (change.field.startsWith("option.")) {
        const [, id, part] = change.field.split(".");
        const option = fields.options.find((o) => o.id === id);
        if (option) option[part][change.lang] = change.text;
      } else {
        fields[change.field] = { ...(fields[change.field] ?? blankTexts()), [change.lang]: change.text };
      }
    }
    result.changes = result.changes.filter((c) => !chosen.some((x) => x.field === c.field && x.lang === c.lang));
  }

  // New wrong options the check proposed because the question had too few.
  function addOptions(result, chosen) {
    for (const option of chosen) {
      const used = new Set(fields.options.map((o) => o.id));
      const id = "abcdefghij".split("").find((c) => !used.has(c));
      if (!id) break;
      fields.options.push({ id, correct: false, text: { ...blankTexts(), ...option.text }, feedback: { ...blankTexts(), ...option.feedback } });
    }
    result.new_options = result.new_options.filter((o) => !chosen.includes(o));
  }

  function removeCode() {
    fields.code = "";
    fields.code_language = "";
  }

  function applyCode(code, language) {
    fields.code = code;
    fields.code_language = language;
  }

  function applyImages(chosen, columns) {
    for (const f of chosen) if (f.data) figureData[f.name] = f.data;
    fields.images = chosen.map((f) => f.name);
    fields.image_columns = columns;
  }

  // Whether the question was saved; a conflict or an error keeps the editor open with its message.
  async function save(force = false) {
    if (busy) return false;
    busy = true;
    try {
      const result = await call("save_question", base.pool, base.data.id, $state.snapshot(fields), base.mtime_ns, force);
      const wasReviewed = base.data.status === "reviewed";
      base = result.question;
      fields = editable(result.question.data);
      saved = JSON.stringify(fields);
      conflict = false;
      showToast(!result.changed ? t("edit.noChange") : wasReviewed && base.data.status === "draft" ? t("edit.savedDraft") : t("edit.saved"));
      onsaved?.(result.question);
      return true;
    } catch (err) {
      if (err.code === "conflict") conflict = true;
      else showToast(errorText(err));
      return false;
    } finally {
      busy = false;
    }
  }

  async function loadTheirs() {
    const fresh = await call("get_question", base.pool, base.data.id);
    base = fresh;
    fields = editable(fresh.data);
    saved = JSON.stringify(fields);
    conflict = false;
  }

  function discard() {
    fields = editable(base.data);
  }

  async function close() {
    if (dirty && saveOnBack) {
      if (!(await save())) return;
    } else if (dirty && !(await ask({ title: t("edit.leaveTitle"), message: t("edit.confirmLeave", { id: base.data.id }), action: t("edit.discard") }))) return;
    ondraft?.(null);
    onclose?.();
  }

  function onkeydown(event) {
    if (!shell?.offsetParent) return; // on a page in the background
    if (event.ctrlKey && event.key.toLowerCase() === "s") {
      event.preventDefault();
      save();
    }
  }
</script>

<svelte:window {onkeydown} />

<div class="editor-shell" bind:this={shell}>
  <!-- While the language model works, a veil over the editor says so and keeps the question from changing meanwhile. -->
  {#if asking}
    <div class="assist-veil" role="status" aria-live="polite">
      <span class="spinner" aria-hidden="true"></span>
      <b>{t(asking === "numbers" ? "assist.busyNumbers" : "assist.busyReview")}</b>
      <span class="hint">{t("assist.busyHint")}</span>
    </div>
  {/if}
  <header class="editor-bar">
    <button class="btn ghost" onclick={close}><Icon name="back" />{back || t("edit.back")}</button>
    <span class="qid">{base.data.id}</span>
    <span class="tag" class:ok={base.data.status === "reviewed"}>{t(`status.${base.data.status}`)}</span>
    {#if dirty}<span class="unsaved"><i class="dot"></i>{t("edit.unsaved")}</span>{/if}
    <span class="spacer"></span>
    <span class="hint">{t("edit.shortcut")}</span>
    <button class="btn ghost" onclick={discard} disabled={!dirty}>{t("edit.discard")}</button>
    <button class="btn primary" onclick={() => save()} disabled={busy || !dirty}>{t("edit.save")}</button>
  </header>

  {#if conflict}
    <div class="conflict">
      <p>{t("edit.conflict")}</p>
      <button class="btn" onclick={loadTheirs}>{t("edit.loadTheirs")}</button>
      <button class="btn decide" onclick={() => save(true)}>{t("edit.keepMine")}</button>
    </div>
  {/if}

  <!-- Next to a setting of a variant: inherited from the parent, or its own value with a way back. -->
  {#snippet heritage(key)}
    {#if isVariant && inherited[key] != null && fromParent(key)}
      <span class="heritage" title={t("edit.inheritedHint", { id: parentId })}>{t("edit.inherited", { id: parentId })}</span>
    {:else if isVariant && inherited[key] != null}
      <button type="button" class="heritage own" title={t("edit.inheritAgainHint", { id: parentId })}
        onclick={(e) => { e.preventDefault(); fields[key] = key === "coverage" || key === "misconception" ? "" : null; }}>{t("edit.inheritAgain")}</button>
    {/if}
  {/snippet}

  <div class="editor-split">
    <form class="editor-form" onsubmit={(e) => { e.preventDefault(); save(); }}>
      {#if base.data.status === "reviewed"}<p class="form-info">{t("edit.reviewedNote")}</p>{/if}

      <div class="form-grid">
        {#if qtype !== "free_text"}
          <div class="field">
            <span class="field-label">{t("edit.type")}{@render heritage("type")}</span>
            <div class="seg" role="group">
              {#each ["single", "multiple"] as v}
                <button type="button" class:on={qtype === v} class:inherited={fromParent("type")} onclick={() => setType(v)}>{t(`type.${v}`)}</button>
              {/each}
            </div>
          </div>
        {/if}
        <div class="field">
          <span class="field-label">{t("edit.level")}{@render heritage("level")}</span>
          <div class="seg" role="group">
            {#each ["remember", "understand", "apply"] as v}
              <button type="button" class:on={effective("level") === v} class:inherited={fromParent("level")} onclick={() => (fields.level = v)}>{t(`level.${v}`)}</button>
            {/each}
          </div>
        </div>
        <div class="field">
          <span>{t("edit.use")}</span>
          <div class="chips" role="group" aria-label={t("edit.use")}>
            <button type="button" class="chip" class:on={fields.public} aria-pressed={fields.public} onclick={() => toggleUse("public")}>{t("use.practice")}</button>
            <button type="button" class="chip" class:on={fields.exam} aria-pressed={fields.exam} onclick={() => toggleUse("exam")}>{t("use.exam")}</button>
          </div>
        </div>
        <div class="field">
          <span class="field-label">{t("edit.time")}{@render heritage("time_seconds")}</span>
          <TimeChoice bind:value={fields.time_seconds} inherited={isVariant ? inherited.time_seconds ?? null : null} />
        </div>
        {#if !fields.public}
          <label class="field">
            <span>{t("edit.variantOf")}</span>
            <select class="select" bind:value={fields.variant_of}>
              <option value="">{t("edit.noVariant")}</option>
              {#each variantChoices as p}<option value={p.id}>{p.id}: {p.stem.slice(0, 60)}</option>{/each}
            </select>
          </label>
        {/if}
      </div>

      <div class="lang-row">
        <div class="lang-tabs" role="tablist" aria-label={t("edit.language")}>
          {#each languages as l}
            <button type="button" role="tab" aria-selected={lang === l} class:on={lang === l} onclick={() => (lang = l)}
              title={missing.includes(l) ? t("edit.missingIn", { lang: l.toUpperCase() }) : ""}>
              {l === "de" ? "Deutsch" : "English"}{#if missing.includes(l)}<i class="dot warn-dot"></i>{/if}
            </button>
          {/each}
        </div>
        {#if llmReady()}
          <button type="button" class="btn ghost btn-small review-btn" onclick={reviewQuestion}
            disabled={asking === "review" || languages.every((l) => !fields.stem[l]?.trim())}
            title={t(isChoice ? "assist.reviewHint" : "assist.reviewHintFree")}>
            <Icon name="wand" />{asking === "review" ? t("assist.working") : t("assist.review")}
          </button>
        {/if}
        <a class="lang-hint" href="#/modules" title={t("edit.languagesHint")}>{t(languages.length > 1 ? "edit.languagesPool" : "edit.languagePool")}</a>
      </div>
      {#if review}
        <AssistChanges findings={review.findings} changes={review.changes} additions={review.new_options}
          title={t("assist.reviewTitle")} label={fieldLabel} showLang={languages.length > 1}
          onapply={(chosen) => applyTo(review, chosen)} onadd={(chosen) => addOptions(review, chosen)} onclose={() => (review = null)} />
      {/if}

      <label class="field">
        <span>{t("edit.stem")}</span>
        <textarea id="stem-input" class="input grow-text" rows="3" bind:value={fields.stem[lang]}></textarea>
      </label>

      <div class="attachments">
        {#if fields.code}
          <div class="attachment-card">
            <span class="attachment-icon"><Icon name="code" /></span>
            <span class="attachment-text"><b>{t("attach.code")}</b><span>{codeLanguageName} · {t(codeLines === 1 ? "attach.line" : "attach.lines", { n: codeLines })}</span></span>
            <button type="button" class="icon-btn" title={t("attach.codeEdit")} aria-label={t("attach.codeEdit")} onclick={() => (codeOpen = true)}><Icon name="edit" /></button>
            <button type="button" class="icon-btn danger" title={t("attach.removeCode")} aria-label={t("attach.removeCode")} onclick={removeCode}><Icon name="trash" /></button>
          </div>
        {/if}
        {#if fields.images.length}
          <div class="attachment-card">
            <span class="attachment-thumbs">
              {#each figures.slice(0, 3) as f (f.name)}
                <span class="attachment-icon">{#if f.data}<img src={f.data} alt="" />{:else}<Icon name="image" />{/if}</span>
              {/each}
            </span>
            <span class="attachment-text">
              <b>{fields.images.length === 1 ? t("edit.image") : t("attach.figures", { n: fields.images.length })}</b>
              <span>{fields.images.length === 1 ? fields.images[0] : layoutName}</span>
            </span>
            <button type="button" class="icon-btn" title={t("attach.imageChange")} aria-label={t("attach.imageChange")} onclick={() => (imageOpen = true)}><Icon name="edit" /></button>
            <button type="button" class="icon-btn danger" title={t("attach.removeImages")} aria-label={t("attach.removeImages")} onclick={() => { fields.images = []; fields.image_columns = 1; }}><Icon name="trash" /></button>
          </div>
        {/if}
        <Menu buttonLabel={t("attach.add")} items={addItems} align="left" />
      </div>

      {#if isChoice}
        <h3 class="form-section">{t("edit.options")}</h3>
        <ol class="option-edit">
          {#each fields.options as option (option.id)}
            <li class:correct={option.correct}>
              <button type="button" class="correct-toggle" class:round={qtype === "single"} class:on={option.correct} aria-pressed={option.correct}
                title={t("edit.correct")} onclick={() => setCorrect(option)}>
                {#if option.correct}<Icon name="check" />{/if}
              </button>
              <div class="option-fields">
                <span class="option-letter">{option.id}</span>
                <textarea class="input grow-text" rows="1" aria-label={t("edit.text", { id: option.id })}
                  bind:value={option.text[lang]}></textarea>
                <textarea class="input grow-text feedback" rows="1" placeholder={t("edit.feedback", { id: option.id })}
                  aria-label={t("edit.feedback", { id: option.id })} bind:value={option.feedback[lang]}></textarea>
              </div>
              <button type="button" class="icon-btn" aria-label={t("edit.removeOption", { id: option.id })}
                title={t("edit.removeOption", { id: option.id })} onclick={() => removeOption(option)}>
                <Icon name="remove" />
              </button>
            </li>
          {/each}
        </ol>
        {#if fields.options.length < 10}
          <button type="button" class="btn ghost" onclick={addOption}><Icon name="plus" />{t("edit.addOption")}</button>
        {/if}
      {:else}
        <div class="form-row">
          <label class="field"><span class="field-label">{t("edit.lines")}{@render heritage("lines")}</span>
            <input class="input" type="number" min="1" bind:value={fields.lines} style="width: 100px"
              placeholder={isVariant && inherited.lines != null ? String(inherited.lines) : ""} /></label>
          <label class="check-line"><input type="checkbox" checked={effective("half_points") === true}
            onchange={(e) => (fields.half_points = e.currentTarget.checked)} />{t("edit.halfPoints")}{@render heritage("half_points")}</label>
        </div>
        <label class="field"><span>{t("q.expected")}</span>
          <textarea class="input grow-text" rows="3" bind:value={fields.expected[lang]}></textarea></label>
        <label class="field"><span>{t("q.markingNotes")}</span>
          <textarea class="input grow-text" rows="2" bind:value={fields.marking_notes[lang]}></textarea></label>
      {/if}

      {#if llmReady() && isVariant && qtype === "free_text"}
        <div class="assist-whole">
          <button type="button" class="btn ghost" onclick={varyNumbers} disabled={asking === "numbers" || !fields.stem[lang]?.trim()}
            title={t("assist.numbersHint")}>
            <Icon name="wand" />{asking === "numbers" ? t("assist.working") : t("assist.numbers")}
          </button>
          {#if numbers}
            <AssistChanges findings={numbers.findings} changes={numbers.changes} title={t("assist.numbersTitle")} label={fieldLabel} showLang={languages.length > 1}
              note={{ title: t("assist.calculation"), text: numbers.calculation }}
              onapply={(chosen) => applyTo(numbers, chosen)} onclose={() => (numbers = null)} />
          {/if}
        </div>
      {/if}

      <details class="more">
        <summary>{t("edit.more")}</summary>
        <label class="field"><span class="field-label">{t("edit.coverage")}{@render heritage("coverage")}</span>
          <input class="input" bind:value={fields.coverage} placeholder={isVariant ? inherited.coverage ?? "" : ""} /></label>
        <label class="field"><span class="field-label">{t("edit.misconception")}{@render heritage("misconception")}</span>
          <input class="input" bind:value={fields.misconception} placeholder={isVariant ? inherited.misconception ?? "" : ""} /></label>
      </details>
    </form>

    <CodeDialog bind:open={codeOpen} code={fields.code} language={fields.code_language} onapply={applyCode} />
    <ImageDialog bind:open={imageOpen} pool={base.pool} current={fields.images} columns={fields.image_columns} onapply={applyImages} />

    <div class="editor-preview">
      <QuestionPreview question={preview} compact />
    </div>
  </div>
</div>
