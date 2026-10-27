<script>
  import Icon from "./Icon.svelte";
  import Menu from "./Menu.svelte";
  import InlineText from "./InlineText.svelte";
  import QuestionDetails from "./QuestionDetails.svelte";
  import TagPick from "./TagPick.svelte";
  import TimePick from "./TimePick.svelte";
  import { highlight } from "../lib/highlight.js";
  import { formatDate, formatTime } from "../lib/time.js";
  import { inline } from "../lib/inline.js";
  import { findingText, t, ui } from "../lib/i18n.svelte.js";

  // A read-only view of one question: text, options with the correct ones marked, findings and metadata.
  // `onaction(name)` runs a step of the question's life: release, withdraw, variant, retire, restore, delete.
  // `me` is the name Markwise notes on a release, to tell whether this examiner released the question already.
  // `lifecycle` false leaves out release and the other steps, for a look from elsewhere, such as an exam;
  // `language` is the language to show first.
  // `editable` lets each text turn into a field for its Markdown on a click; `onchange(fields)` receives what changed,
  // in the shape the editor saves, so that the page can save it at once. An editable question shows only its text,
  // figures, code and answers; `details` adds below them the rationales, all settings, the findings and where the
  // question comes from, each setting changed in place. `practice` lists the pool's practice questions for the
  // choice which one a variant varies, and `fresh` opens the text of a question just created for typing.
  let { question, variants = [], compact = false, onopen, onedit, onaction, me = "", lifecycle = true, language = null,
    editable = false, onchange, details = $bindable(false), practice = [], fresh = false } = $props();

  // A variant shows the settings it inherits from its parent where it sets none of its own.
  const data = $derived.by(() => {
    const merged = { ...question.data };
    for (const [key, value] of Object.entries(question.inherited ?? {})) {
      if (merged[key] == null || merged[key] === "") merged[key] = value;
    }
    return merged;
  });
  const isInherited = (key) => key in (question.inherited ?? {}) && (question.data[key] == null || question.data[key] === "");
  const languages = $derived(question.languages);
  let lang = $state(null);
  const shown = $derived(lang && languages.includes(lang) ? lang : languages.includes(language) ? language
    : languages.includes(ui.lang) ? ui.lang : languages[0]);

  const pick = (value) => (value && typeof value === "object" ? value[shown] ?? "" : value ?? "");
  const severityClass = { error: "red", warning: "warn", note: "" };
  const reviewers = $derived((data.released_by ?? []).map(String));
  const releasedByMe = $derived(Boolean(me) && reviewers.includes(me));
  const retired = $derived(data.status === "retired");
  const hasErrors = $derived(question.findings.some((f) => f.severity === "error"));
  const actions = $derived([
    ...(data.public && !data.variant_of
      ? [{ label: t("life.variant"), icon: "copy", onclick: () => onaction?.("variant") }] : []),
    { label: t("q.openFile"), icon: "upload", onclick: () => onopen?.(question.path) },
    ...(data.status === "draft" ? [{ label: t("life.delete"), icon: "trash", onclick: () => onaction?.("delete") }] : []),
  ]);
  // --- changes in place: each one goes out as the fields it touches ----------------------------
  const can = $derived(editable && !retired && Boolean(onchange));
  const copy = (value) => JSON.parse(JSON.stringify(value ?? null));
  const save = (fields) => onchange?.(fields);
  // Only the language changed goes out; the other languages of the text stay as they are in the file.
  function setText(key, value) {
    save({ [key]: { [shown]: value } });
  }
  const optionsCopy = () => copy(question.data.options ?? []);
  function setOption(index, key, value) {
    const options = optionsCopy();
    options[index][key] = { ...(options[index][key] ?? {}), [shown]: value };
    save({ options });
  }
  function toggleCorrect(index) {
    const options = optionsCopy();
    if (data.type === "single") options.forEach((o, i) => (o.correct = i === index));
    else options[index].correct = !options[index].correct;
    save({ options });
  }
  let added = $state(null); // the option just added, whose text opens for typing
  function addOption() {
    const options = optionsCopy();
    const used = new Set(options.map((o) => o.id));
    const id = "abcdefghij".split("").find((c) => !used.has(c));
    if (!id) return;
    options.push({ id, correct: false, text: Object.fromEntries(languages.map((l) => [l, ""])), feedback: {} });
    added = id;
    save({ options });
  }
  function removeOption(index) {
    save({ options: optionsCopy().filter((_, i) => i !== index) });
  }
  // Languages in which a text the question needs is still empty, marked on the language switch.
  const missing = $derived(can ? languages.filter((l) => {
    const text = (value) => String(value?.[l] ?? "").trim();
    return !text(data.stem) || (data.type === "free_text" ? !text(data.expected) : (data.options ?? []).some((o) => !text(o.text)));
  }) : []);
  const open = $derived(!can || details); // everything below the answers shows
  const problems = $derived(question.findings.filter((f) => f.severity !== "note"));

  const useOf = (d) => {
    const exam = typeof d.exam === "boolean" ? d.exam : !d.public;
    return d.public && exam ? "both" : d.public ? "practice" : "exam";
  };
  const useKey = (d) => `use.${useOf(d)}`;

  // --- the labels in the heading: each opens the choice of its setting --------------------------------
  const inherited = $derived(question.inherited ?? {});
  const parentId = $derived(question.parent?.id ?? data.variant_of ?? "");
  // A variant can take a setting from its parent again; the chip says what that is.
  const inheritChip = (key, label) => (data.variant_of && inherited[key] != null
    ? [{ value: null, label: t("sheet.inherit", { value: label(inherited[key]) }), faint: true, title: t("edit.inheritAgainHint", { id: parentId }) }] : []);
  const typeOptions = $derived([
    ...["single", "multiple"].map((v) => ({ value: v, label: t(`type.${v}`) })),
    ...inheritChip("type", (v) => t(`type.${v}`)),
  ]);
  const levelOptions = $derived([
    ...["remember", "understand", "apply"].map((v) => ({ value: v, label: t(`level.${v}`) })),
    ...inheritChip("level", (v) => t(`level.${v}`)),
  ]);
  const useOptions = ["practice", "exam", "both"].map((v) => ({ value: v, label: t(`use.${v}`) }));
  const USES = { practice: { public: true, exam: false }, exam: { public: false, exam: true }, both: { public: true, exam: true } };
  const inheritedNote = (key) => (isInherited(key) ? t("edit.inherited", { id: parentId }) : "");

  function setType(type) {
    const options = optionsCopy();
    if ((type ?? inherited.type) === "single") {
      let seen = false;
      for (const o of options) {
        o.correct = Boolean(o.correct) && !seen;
        seen ||= o.correct;
      }
    }
    save({ type, options });
  }

  // The status label holds every change of status: who released the question, releasing or taking one's release
  // back, retiring it, and taking a retired question back.
  const statusNote = $derived(
    retired ? t("life.retiredNote")
      : [reviewers.length ? t("life.releasedBy", { names: reviewers.join(", ") }) : t("life.notReleased"),
        hasErrors && !releasedByMe ? t("err.has_errors") : ""].filter(Boolean).join(" "),
  );
  const statusActions = $derived(
    retired
      ? [{ label: t("life.restore"), icon: "undo", title: t("life.restoreHint"), onclick: () => onaction?.("restore") }]
      : [
        releasedByMe
          ? { label: t("life.withdraw"), icon: "undo", onclick: () => onaction?.("withdraw") }
          : { label: reviewers.length ? t("life.releaseAlso") : t("life.release"), icon: "check", disabled: hasErrors,
            title: hasErrors ? t("err.has_errors") : t("life.releaseHint"), onclick: () => onaction?.("release") },
        { label: t("life.retire"), icon: "archive", title: t("life.confirmRetire"), onclick: () => onaction?.("retire") },
      ],
  );
</script>

<article class="preview">
  <header class="preview-head">
    <div class="preview-title">
      <span class="qid">{data.id}</span>
      {#if can}
        {#if data.type === "free_text"}
          <span class="tag">{t("type.free_text")}</span>
        {:else}
          <TagPick label={t(`type.${data.type}`)} heading={t("edit.type")} hint={t("pick.hint")} faint={isInherited("type")}
            value={question.data.type ?? null} options={typeOptions} note={inheritedNote("type")} onchoose={setType} />
        {/if}
        <TagPick label={t(`level.${data.level}`)} heading={t("edit.level")} hint={t("pick.hint")} faint={isInherited("level")}
          value={question.data.level ?? null} options={levelOptions} note={inheritedNote("level")} onchoose={(level) => save({ level })} />
        <TimePick seconds={question.data.time_seconds ?? null} inherited={data.variant_of ? inherited.time_seconds ?? null : null}
          parent={parentId} title={data.id} note="" align="left" onchoose={(time_seconds) => save({ time_seconds })} />
        {#if lifecycle}
          <TagPick label={t(`status.${data.status}`)} tone={data.status === "released" || data.status === "piloted" ? "ok" : ""}
            heading={t("q.meta.status")} hint={t("pick.statusHint")} note={statusNote} actions={statusActions} />
        {:else}
          <span class="tag" class:ok={data.status === "released" || data.status === "piloted"}>{t(`status.${data.status}`)}</span>
        {/if}
        {#if data.variant_of}
          <span class="tag" title={t("q.variantExamOnly")}>{t("use.exam")}</span>
        {:else}
          <TagPick label={t(useKey(question.data))} heading={t("edit.use")} hint={t("pick.hint")} value={useOf(question.data)}
            options={useOptions} onchoose={(use) => save(USES[use])} />
        {/if}
      {:else}
        <span class="tag">{t(`type.${data.type}`)}</span>
        {#if data.level}<span class="tag">{t(`level.${data.level}`)}</span>{/if}
        <span class="tag" class:warn={!data.time_seconds}>{data.time_seconds ? formatTime(data.time_seconds) : t("exams.noTime")}</span>
        {#if editable && lifecycle && !compact}
          <TagPick label={t(`status.${data.status}`)} heading={t("q.meta.status")} hint={t("pick.statusHint")} note={statusNote}
            actions={statusActions} />
        {:else}
          <span class="tag" class:ok={data.status === "released" || data.status === "piloted"}>{t(`status.${data.status}`)}</span>
        {/if}
        <span class="tag">{t(useKey(data))}</span>
      {/if}
    </div>
    {#if languages.length > 1}
      <div class="seg seg-small" role="group">
        {#each languages as code}
          <button class:on={shown === code} onclick={() => (lang = code)}
            title={missing.includes(code) ? t("edit.missingIn", { lang: code.toUpperCase() }) : null}>{code.toUpperCase()}{#if missing.includes(code)}<i class="dot warn-dot"></i>{/if}</button>
        {/each}
      </div>
    {/if}
    {#if !compact && !lifecycle}
      {#if onedit}<button class="btn primary" onclick={() => onedit()}><Icon name="edit" />{t("edit.edit")}</button>{/if}
    {:else if !compact}
      {#if !retired}
        {#if editable}
          <button class="btn ghost details-toggle" class:on={details} aria-expanded={details} title={t(details ? "sheet.detailsHide" : "sheet.detailsShow")}
            onclick={() => (details = !details)}><Icon name="sliders" />{t("sheet.details")}<span class="details-chevron"><Icon name="chevron" /></span></button>
        {:else}
          <button class="btn primary" onclick={() => onedit?.()}><Icon name="edit" />{t("edit.edit")}</button>
        {/if}
      {/if}
      <Menu label={t("life.more")} items={actions} />
    {/if}
  </header>

  {#if retired}<p class="form-info retired-note">{t("life.retiredBanner")}</p>{/if}

  {#if data.variant_of}<p class="variant-note">{t("q.variantOf", { id: data.variant_of })}</p>{/if}

  {#if can}
    <InlineText class="stem" value={pick(question.data.stem)} placeholder={t("sheet.stem")} label={t("sheet.stem")} opened={fresh} onsave={(v) => setText("stem", v)} />
    {#if question.data.code}<InlineText code value={question.data.code} language={question.data.code_language} label={t("sheet.code")} onsave={(v) => save({ code: v })} />{/if}
  {:else}
    <div class="stem">{@html inline(pick(data.stem))}</div>
    {#if data.code}<pre class="code-block hljs"><code>{@html highlight(data.code, data.code_language)}</code></pre>{/if}
  {/if}
  {#if question.figures?.length}
    <div class="figures" style="--columns: {question.figures.length > 1 ? question.image_columns ?? 1 : 1}">
      {#each question.figures as f (f.name)}
        <figure class="figure">{#if f.data}<img src={f.data} alt={t("q.image")} />{:else}<span class="missing-figure">{f.name}</span>{/if}</figure>
      {/each}
    </div>
  {/if}

  {#if data.type === "free_text" && can}
    <h4 class="sub">{t("q.expected")}</h4>
    <InlineText value={pick(question.data.expected)} placeholder={t("sheet.expected")} onsave={(v) => setText("expected", v)} />
    {#if details}
      <h4 class="sub">{t("q.markingNotes")}</h4>
      <InlineText value={pick(question.data.marking_notes)} placeholder={t("sheet.marking")} onsave={(v) => setText("marking_notes", v)} />
    {/if}
  {:else if data.type === "free_text"}
    {#if data.half_points}<p class="muted small">{t("q.halfPoints")}</p>{/if}
    {#if pick(data.expected)}<h4 class="sub">{t("q.expected")}</h4><p class="prose">{@html inline(pick(data.expected))}</p>{/if}
    {#if pick(data.marking_notes)}<h4 class="sub">{t("q.markingNotes")}</h4><p class="prose">{@html inline(pick(data.marking_notes))}</p>{/if}
  {:else if can}
    <ol class="options sheet-options" class:single={data.type === "single"}>
      {#each question.data.options ?? [] as option, i (option.id)}
        <li class:correct={option.correct}>
          <button type="button" class="box" title={t("sheet.correct")} aria-label={t("sheet.correct")} aria-pressed={Boolean(option.correct)}
            onclick={() => toggleCorrect(i)}>{#if option.correct}<Icon name="check" />{/if}</button>
          <div class="sheet-option">
            <div class="option-text"><b>{option.id}</b>
              <InlineText tag="span" value={pick(option.text)} placeholder={t("sheet.option")} opened={added === option.id}
                onsave={(v) => { added = null; setOption(i, "text", v); }} /></div>
            {#if details}<InlineText value={pick(option.feedback)} placeholder={t("sheet.feedback")} onsave={(v) => setOption(i, "feedback", v)} />{/if}
          </div>
          <button type="button" class="icon-btn small-icon danger option-remove" title={t("sheet.removeOption")} aria-label={t("sheet.removeOption")}
            onclick={() => removeOption(i)}><Icon name="trash" /></button>
        </li>
      {/each}
    </ol>
    {#if (question.data.options ?? []).length < 10}
      <button type="button" class="btn btn-small ghost add-option" onclick={addOption}><Icon name="plus" />{t("sheet.addOption")}</button>
    {/if}
  {:else}
    <ol class="options" class:single={data.type === "single"}>
      {#each data.options ?? [] as option}
        <li class:correct={option.correct}>
          <span class="box" aria-hidden="true">{#if option.correct}<Icon name="check" />{/if}</span>
          <div>
            <div class="option-text"><b>{option.id}</b> {@html inline(pick(option.text))}{#if option.correct}<span class="sr">({t("q.correct")})</span>{/if}</div>
            {#if pick(option.feedback)}<div class="option-feedback">{@html inline(pick(option.feedback))}</div>{/if}
          </div>
        </li>
      {/each}
    </ol>
  {/if}

  {#if can && details}
    <QuestionDetails {question} {data} lang={shown} {practice} {save} />
  {/if}

  {#if open || problems.length}
  <section class="preview-section">
    <h4 class="sub">{t("q.findings")}</h4>
    {#if question.findings.length === 0}
      <p class="check-ok"><Icon name="check" />{t("q.noFindings")}</p>
    {:else}
      <ul class="findings">
        {#each open ? question.findings : problems as f}
          <li><span class="tag {severityClass[f.severity]}">{t(`sev.${f.severity}`)}</span>{findingText(f)}</li>
        {/each}
      </ul>
    {/if}
  </section>
  {/if}

  {#if !compact && open}
  <section class="preview-section">
    <dl class="meta">
      <dt>{t("q.meta.concept")}</dt><dd>{question.concept_name ?? data.concept}{#if question.concept_description}<span class="muted small concept-desc">{question.concept_description}</span>{/if}</dd>
      {#if data.public}
        <dt>{t("q.variants")}</dt><dd>{variants.length ? variants.join(", ") : t("q.noVariant")}</dd>
      {/if}
      {#if data.variant_of}
        <dt>{t("q.parent")}</dt><dd>{data.variant_of}{#if question.parent?.stem}<span class="muted small concept-desc">{question.parent.stem}</span>{/if}</dd>
      {/if}
      {#if data.coverage && !can}<dt>{t("q.meta.coverage")}</dt><dd>{data.coverage}</dd>{/if}
      {#if data.misconception && !can}<dt>{t("q.meta.misconception")}</dt><dd>{data.misconception}</dd>{/if}
      {#if reviewers.length}<dt>{t("q.meta.released")}</dt><dd>{reviewers.join(", ")}</dd>{/if}
      {#if data.created_by || data.created_at}<dt>{t("q.meta.created")}</dt><dd>{t("q.by", { name: data.created_by || "–", date: formatDate(data.created_at) })}</dd>{/if}
      <dt>{t("q.meta.pool")}</dt><dd>{question.pool_name}</dd>
      {#if question.modified}<dt>{t("q.meta.modified")}</dt><dd>{data.changed_by ? `${data.changed_by}, ` : ""}{new Date(question.modified * 1000).toLocaleString(ui.lang === "de" ? "de-DE" : "en-GB", { dateStyle: "medium", timeStyle: "short" })}</dd>{/if}
      <dt>{t("q.meta.file")}</dt><dd class="small">{question.path}</dd>
    </dl>
  </section>
  {/if}
</article>
