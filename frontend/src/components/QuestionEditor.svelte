<script>
  import { untrack } from "svelte";
  import Icon from "./Icon.svelte";
  import QuestionPreview from "./QuestionPreview.svelte";
  import Menu from "./Menu.svelte";
  import CodeDialog from "./CodeDialog.svelte";
  import ImageDialog from "./ImageDialog.svelte";
  import { CODE_LANGUAGES, detectLanguage } from "../lib/highlight.js";
  import { call } from "../lib/api.js";
  import { errorText, t, ui } from "../lib/i18n.svelte.js";
  import { showToast } from "../lib/state.svelte.js";

  // Edits one question: form on the left, the question as it reads on the right, checked while typing.
  // `practice` lists the practice questions of the same pool for the variant choice.
  let { question, practice = [], onclose, onsaved } = $props();
  // The editor is created anew for every question (see {#key} in the page), so it starts from this snapshot.
  const initial = untrack(() => question);

  const EDITABLE = ["type", "level", "public", "exam", "variant_of", "coverage", "misconception", "stem", "images", "image_columns", "code",
    "code_language", "options", "points", "half_points", "lines", "expected", "marking_notes"];
  const languages = initial.languages;
  const blankTexts = () => Object.fromEntries(languages.map((l) => [l, ""]));

  function editable(data) {
    const fields = {};
    for (const key of EDITABLE) if (key in data) fields[key] = JSON.parse(JSON.stringify(data[key])); // data may be reactive state
    // Every text map gets every language, so that the form has a field for each.
    for (const key of ["stem", "expected", "marking_notes"]) {
      if (key in fields || (key === "stem")) fields[key] = { ...blankTexts(), ...(fields[key] ?? {}) };
    }
    // Optional fields as empty strings, so that inputs bind to them; the core drops empty optional fields.
    for (const key of ["variant_of", "coverage", "misconception", "code", "code_language"]) fields[key] ??= "";
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

  let base = $state(initial);
  let fields = $state(editable(initial.data));
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
  const isChoice = $derived(fields.type === "single" || fields.type === "multiple");
  const variantChoices = $derived(practice.filter((p) => p.concept === base.data.concept && p.id !== base.data.id));

  // Languages in which a required text is still empty, for the marks on the language tabs.
  const missing = $derived(
    languages.filter((l) =>
      !fields.stem?.[l]?.trim() ||
      (isChoice && (fields.options ?? []).some((o) => !o.text?.[l]?.trim())) ||
      (fields.type === "free_text" && !fields.expected?.[l]?.trim()),
    ),
  );

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
    if (fields.type === "single") for (const o of fields.options) o.correct = o === option;
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

  async function save(force = false) {
    if (busy) return;
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
    } catch (err) {
      if (err.code === "conflict") conflict = true;
      else showToast(errorText(err));
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

  function close() {
    if (dirty && !confirm(t("edit.confirmLeave", { id: base.data.id }))) return;
    onclose?.();
  }

  function onkeydown(event) {
    if (event.ctrlKey && event.key.toLowerCase() === "s") {
      event.preventDefault();
      save();
    }
  }
</script>

<svelte:window {onkeydown} />

<div class="editor-shell">
  <header class="editor-bar">
    <button class="btn ghost" onclick={close}><Icon name="back" />{t("edit.back")}</button>
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

  <div class="editor-split">
    <form class="editor-form" onsubmit={(e) => { e.preventDefault(); save(); }}>
      {#if base.data.status === "reviewed"}<p class="form-info">{t("edit.reviewedNote")}</p>{/if}

      <div class="form-grid">
        {#if fields.type !== "free_text"}
          <div class="field">
            <span>{t("edit.type")}</span>
            <div class="seg" role="group">
              {#each ["single", "multiple"] as v}
                <button type="button" class:on={fields.type === v} onclick={() => setType(v)}>{t(`type.${v}`)}</button>
              {/each}
            </div>
          </div>
        {/if}
        <div class="field">
          <span>{t("edit.level")}</span>
          <div class="seg" role="group">
            {#each ["remember", "understand", "apply"] as v}
              <button type="button" class:on={fields.level === v} onclick={() => (fields.level = v)}>{t(`level.${v}`)}</button>
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

      {#if languages.length > 1}
        <div class="lang-tabs" role="tablist" aria-label={t("edit.language")}>
          {#each languages as l}
            <button type="button" role="tab" aria-selected={lang === l} class:on={lang === l} onclick={() => (lang = l)}
              title={missing.includes(l) ? t("edit.missingIn", { lang: l.toUpperCase() }) : ""}>
              {l === "de" ? "Deutsch" : "English"}{#if missing.includes(l)}<i class="dot warn-dot"></i>{/if}
            </button>
          {/each}
        </div>
      {/if}

      <label class="field">
        <span>{t("edit.stem")}</span>
        <textarea class="input grow-text" rows="3" bind:value={fields.stem[lang]}></textarea>
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
              <button type="button" class="correct-toggle" class:round={fields.type === "single"} class:on={option.correct} aria-pressed={option.correct}
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
          <label class="field"><span>{t("edit.points")}</span>
            <input class="input" type="number" min="0.5" step="0.5" bind:value={fields.points} style="width: 100px" /></label>
          <label class="field"><span>{t("edit.lines")}</span>
            <input class="input" type="number" min="1" bind:value={fields.lines} style="width: 100px" /></label>
          <label class="check-line"><input type="checkbox" bind:checked={fields.half_points} />{t("edit.halfPoints")}</label>
        </div>
        <label class="field"><span>{t("q.expected")}</span>
          <textarea class="input grow-text" rows="3" bind:value={fields.expected[lang]}></textarea></label>
        <label class="field"><span>{t("q.markingNotes")}</span>
          <textarea class="input grow-text" rows="2" bind:value={fields.marking_notes[lang]}></textarea></label>
      {/if}

      <details class="more">
        <summary>{t("edit.more")}</summary>
        <label class="field"><span>{t("edit.coverage")}</span><input class="input" bind:value={fields.coverage} /></label>
        <label class="field"><span>{t("edit.misconception")}</span><input class="input" bind:value={fields.misconception} /></label>
      </details>
    </form>

    <CodeDialog bind:open={codeOpen} code={fields.code} language={fields.code_language} onapply={applyCode} />
    <ImageDialog bind:open={imageOpen} pool={base.pool} current={fields.images} columns={fields.image_columns} onapply={applyImages} />

    <div class="editor-preview">
      <QuestionPreview question={preview} compact />
    </div>
  </div>
</div>
