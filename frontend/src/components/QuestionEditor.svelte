<script>
  import { untrack } from "svelte";
  import Icon from "./Icon.svelte";
  import QuestionPreview from "./QuestionPreview.svelte";
  import Menu from "./Menu.svelte";
  import TimeChoice from "./TimeChoice.svelte";
  import DistractorDialog from "./DistractorDialog.svelte";
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
  let { question, practice = [], onclose, onsaved, draft = null, ondraft } = $props();
  // The editor is created anew for every question (see {#key} in the page), so it starts from this snapshot.
  const initial = untrack(() => question);
  const kept = untrack(() => draft);

  const EDITABLE = ["type", "level", "public", "exam", "variant_of", "coverage", "misconception", "stem", "images", "image_columns", "code",
    "code_language", "options", "time_seconds", "half_points", "lines", "expected", "marking_notes"];
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
    fields.time_seconds ??= null;
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

  // Help from the language model, only when it is switched on in the settings.
  let review = $state(null); // { lang, findings, suggestion } for the question text
  let reviewing = $state(false);
  let distractorsOpen = $state(false);

  async function checkStem() {
    reviewing = true;
    try {
      const answer = await call("assist_check_stem", $state.snapshot(fields), lang);
      review = { lang, ...answer };
    } catch (err) {
      showToast(errorText(err));
    } finally {
      reviewing = false;
    }
  }

  function takeSuggestion() {
    fields.stem[review.lang] = review.suggestion;
    review = null;
  }

  // The question as a whole: do text and answers fit together, are the options clear and distinct.
  let whole = $state(null); // { lang, findings, changes }
  let checkingWhole = $state(false);

  async function reviewWhole() {
    checkingWhole = true;
    try {
      const answer = await call("assist_review_question", $state.snapshot(fields), lang);
      whole = { lang, ...answer };
    } catch (err) {
      showToast(errorText(err));
    } finally {
      checkingWhole = false;
    }
  }

  function fieldLabel(name) {
    if (name === "question") return t("assist.aboutQuestion");
    if (name === "stem") return t("edit.stem");
    if (name === "expected") return t("q.expected");
    if (name === "marking_notes") return t("q.markingNotes");
    const [, id, part] = name.split(".");
    return t(part === "text" ? "assist.aboutOption" : "assist.aboutFeedback", { id });
  }

  function applyChange(change) {
    const l = whole.lang;
    if (change.field.startsWith("option.")) {
      const [, id, part] = change.field.split(".");
      const option = fields.options.find((o) => o.id === id);
      if (option) option[part][l] = change.text;
    } else {
      fields[change.field] = { ...(fields[change.field] ?? blankTexts()), [l]: change.text };
    }
    whole.changes = whole.changes.filter((c) => c.field !== change.field);
  }

  function applyAll() {
    for (const change of [...whole.changes]) applyChange(change);
  }

  function addDistractors(chosen) {
    for (const d of chosen) {
      const used = new Set(fields.options.map((o) => o.id));
      const id = "abcdefghij".split("").find((c) => !used.has(c));
      if (!id) break;
      fields.options.push({ id, correct: false, text: { ...blankTexts(), ...d.text }, feedback: { ...blankTexts(), ...d.feedback } });
    }
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

  async function close() {
    if (dirty && !(await ask({ title: t("edit.leaveTitle"), message: t("edit.confirmLeave", { id: base.data.id }), action: t("edit.discard") }))) return;
    ondraft?.(null);
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
        <div class="field">
          <span>{t("edit.time")}</span>
          <TimeChoice bind:value={fields.time_seconds} />
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
        <a class="lang-hint" href="#/modules" title={t("edit.languagesHint")}>{t(languages.length > 1 ? "edit.languagesPool" : "edit.languagePool")}</a>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="stem-input">{t("edit.stem")}</label>
          {#if llmReady()}
            <button type="button" class="btn ghost btn-small" onclick={checkStem} disabled={reviewing || !fields.stem[lang]?.trim()}
              title={t("assist.checkHint")}><Icon name="wand" />{reviewing ? t("assist.working") : t("assist.check")}</button>
          {/if}
        </div>
        <textarea id="stem-input" class="input grow-text" rows="3" bind:value={fields.stem[lang]}></textarea>
        {#if review && review.lang === lang}
          <div class="assist-review">
            {#if review.findings.length}
              <ul>{#each review.findings as f}<li>{f}</li>{/each}</ul>
            {:else}
              <p class="check-ok"><Icon name="check" />{t("assist.nothing")}</p>
            {/if}
            {#if review.suggestion.trim() && review.suggestion.trim() !== fields.stem[lang].trim()}
              <div class="assist-suggestion">
                <span class="hint">{t("assist.suggestion")}</span>
                <div class="stem">{@html inline(review.suggestion)}</div>
              </div>
              <div class="assist-actions">
                <button type="button" class="btn primary btn-small" onclick={takeSuggestion}>{t("attach.apply")}</button>
                <button type="button" class="btn ghost btn-small" onclick={() => (review = null)}>{t("assist.dismiss")}</button>
              </div>
            {:else}
              <div class="assist-actions"><button type="button" class="btn ghost btn-small" onclick={() => (review = null)}>{t("dialog.close")}</button></div>
            {/if}
          </div>
        {/if}
      </div>

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
        <div class="option-tools">
          {#if fields.options.length < 10}
            <button type="button" class="btn ghost" onclick={addOption}><Icon name="plus" />{t("edit.addOption")}</button>
          {/if}
          {#if llmReady() && fields.options.some((o) => o.correct) && fields.options.length < 10}
            <button type="button" class="btn ghost" onclick={() => (distractorsOpen = true)}><Icon name="wand" />{t("assist.distractors")}</button>
          {/if}
        </div>
      {:else}
        <div class="form-row">
          <label class="field"><span>{t("edit.lines")}</span>
            <input class="input" type="number" min="1" bind:value={fields.lines} style="width: 100px" /></label>
          <label class="check-line"><input type="checkbox" bind:checked={fields.half_points} />{t("edit.halfPoints")}</label>
        </div>
        <label class="field"><span>{t("q.expected")}</span>
          <textarea class="input grow-text" rows="3" bind:value={fields.expected[lang]}></textarea></label>
        <label class="field"><span>{t("q.markingNotes")}</span>
          <textarea class="input grow-text" rows="2" bind:value={fields.marking_notes[lang]}></textarea></label>
      {/if}

      {#if llmReady()}
        <div class="assist-whole">
          <button type="button" class="btn ghost" onclick={reviewWhole} disabled={checkingWhole || !fields.stem[lang]?.trim()}
            title={t(isChoice ? "assist.wholeHint" : "assist.wholeHintFree")}>
            <Icon name="wand" />{checkingWhole ? t("assist.working") : t(isChoice ? "assist.whole" : "assist.wholeFree")}
          </button>
          {#if whole && whole.lang === lang}
            <div class="assist-review">
              {#if whole.findings.length}
                <ul>{#each whole.findings as f}<li><b>{fieldLabel(f.about)}:</b> {f.text}</li>{/each}</ul>
              {:else}
                <p class="check-ok"><Icon name="check" />{t("assist.nothing")}</p>
              {/if}
              {#each whole.changes as change (change.field)}
                <div class="assist-suggestion">
                  <div class="assist-change-head">
                    <span class="hint">{fieldLabel(change.field)}</span>
                    <button type="button" class="btn primary btn-small" onclick={() => applyChange(change)}>{t("attach.apply")}</button>
                  </div>
                  {#if change.before}<div class="assist-before">{@html inline(change.before)}</div>{/if}
                  <div class="assist-after">{@html inline(change.text)}</div>
                </div>
              {/each}
              <div class="assist-actions">
                {#if whole.changes.length > 1}<button type="button" class="btn primary btn-small" onclick={applyAll}>{t("assist.applyAll")}</button>{/if}
                <button type="button" class="btn ghost btn-small" onclick={() => (whole = null)}>{whole.changes.length ? t("assist.dismiss") : t("dialog.close")}</button>
              </div>
            </div>
          {/if}
        </div>
      {/if}

      <details class="more">
        <summary>{t("edit.more")}</summary>
        <label class="field"><span>{t("edit.coverage")}</span><input class="input" bind:value={fields.coverage} /></label>
        <label class="field"><span>{t("edit.misconception")}</span><input class="input" bind:value={fields.misconception} /></label>
      </details>
    </form>

    {#if isChoice}
      <DistractorDialog bind:open={distractorsOpen} pool={base.pool} {fields} {lang}
        room={Math.max(1, 5 - fields.options.filter((o) => o.text?.[lang]?.trim()).length)} onapply={addDistractors} />
    {/if}
    <CodeDialog bind:open={codeOpen} code={fields.code} language={fields.code_language} onapply={applyCode} />
    <ImageDialog bind:open={imageOpen} pool={base.pool} current={fields.images} columns={fields.image_columns} onapply={applyImages} />

    <div class="editor-preview">
      <QuestionPreview question={preview} compact />
    </div>
  </div>
</div>
