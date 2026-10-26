<script>
  import Icon from "./Icon.svelte";
  import Menu from "./Menu.svelte";
  import InlineText from "./InlineText.svelte";
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
  // in the shape the editor saves, so that the page can save it at once.
  let { question, variants = [], compact = false, onopen, onedit, onaction, me = "", lifecycle = true, language = null,
    editable = false, onchange } = $props();

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
  const reviewers = $derived((data.reviewed_by ?? []).map(String));
  const releasedByMe = $derived(Boolean(me) && reviewers.includes(me));
  const retired = $derived(data.status === "retired");
  const hasErrors = $derived(question.findings.some((f) => f.severity === "error"));
  const actions = $derived([
    ...(data.public && !data.variant_of
      ? [{ label: t("life.variant"), icon: "copy", onclick: () => onaction?.("variant") }] : []),
    ...(releasedByMe ? [{ label: t("life.withdraw"), icon: "undo", onclick: () => onaction?.("withdraw") }] : []),
    { label: t("q.openFile"), icon: "upload", onclick: () => onopen?.(question.path) },
    retired
      ? { label: t("life.restore"), icon: "undo", onclick: () => onaction?.("restore") }
      : { label: t("life.retire"), icon: "archive", onclick: () => onaction?.("retire") },
    ...(data.status === "draft" ? [{ label: t("life.delete"), icon: "trash", onclick: () => onaction?.("delete") }] : []),
  ]);
  // --- changes in place: each one goes out as the fields it touches ----------------------------
  const can = $derived(editable && !retired && Boolean(onchange));
  const copy = (value) => JSON.parse(JSON.stringify(value ?? null));
  const save = (fields) => onchange?.(fields);
  function setText(key, value) {
    save({ [key]: { ...(copy(question.data[key]) ?? {}), [shown]: value } });
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
  function setType(type) {
    const options = optionsCopy();
    if (type === "single") {
      let seen = false;
      for (const o of options) {
        o.correct = Boolean(o.correct) && !seen;
        seen ||= o.correct;
      }
    }
    save({ type, options });
  }
  // Practice and exam can both be on; at least one stays on.
  function toggleUse(which) {
    const exam = typeof question.data.exam === "boolean" ? question.data.exam : !question.data.public;
    const now = { public: question.data.public === true, exam };
    now[which] = !now[which];
    if (!now.public && !now.exam) return;
    save(now);
  }
  const TIMES = [15, 30, 45, 60, 120, 300];
  const timeChoices = $derived([...new Set([...TIMES, ...(question.data.time_seconds ? [question.data.time_seconds] : [])])].sort((a, b) => a - b));
  const usesOf = (d) => ({ practice: d.public === true, exam: typeof d.exam === "boolean" ? d.exam : !d.public });

  const useKey = (d) => {
    const exam = typeof d.exam === "boolean" ? d.exam : !d.public;
    return d.public && exam ? "use.both" : d.public ? "use.practice" : "use.exam";
  };
</script>

<article class="preview">
  <header class="preview-head">
    <div class="preview-title">
      <span class="qid">{data.id}</span>
      {#if can && data.type !== "free_text" && !isInherited("type")}
        <select class="select select-small tag-select" aria-label={t("stats.type")} value={data.type} onchange={(e) => setType(e.currentTarget.value)}>
          <option value="single">{t("type.single")}</option>
          <option value="multiple">{t("type.multiple")}</option>
        </select>
      {:else}
        <span class="tag">{t(`type.${data.type}`)}</span>
      {/if}
      <span class="tag" class:ok={data.status === "reviewed" || data.status === "piloted"}>{t(`status.${data.status}`)}</span>
      {#if can && !data.variant_of}
        {@const uses = usesOf(question.data)}
        <span class="chips" role="group" aria-label={t("q.meta.use")}>
          <button type="button" class="chip" class:on={uses.practice} aria-pressed={uses.practice} onclick={() => toggleUse("public")}>{t("use.practice")}</button>
          <button type="button" class="chip" class:on={uses.exam} aria-pressed={uses.exam} onclick={() => toggleUse("exam")}>{t("use.exam")}</button>
        </span>
      {:else}
        <span class="tag">{t(useKey(data))}</span>
      {/if}
    </div>
    {#if languages.length > 1}
      <div class="seg seg-small" role="group">
        {#each languages as code}
          <button class:on={shown === code} onclick={() => (lang = code)}>{code.toUpperCase()}</button>
        {/each}
      </div>
    {/if}
    {#if !compact && !lifecycle}
      {#if onedit}<button class="btn primary" onclick={() => onedit()}><Icon name="edit" />{t("edit.edit")}</button>{/if}
    {:else if !compact}
      {#if !retired}
        {#if releasedByMe}
          <span class="released" title={t("life.releasedBy", { names: reviewers.join(", ") })}><Icon name="check" />{t("life.released")}</span>
        {:else}
          <button class="btn" disabled={hasErrors} title={hasErrors ? t("err.has_errors") : t("life.releaseHint")}
            onclick={() => onaction?.("release")}><Icon name="check" />{reviewers.length ? t("life.releaseAlso") : t("life.release")}</button>
        {/if}
        <button class="btn primary" class:ghost={can} title={can ? t("sheet.allFields") : null} onclick={() => onedit?.()}><Icon name="edit" />{can ? t("sheet.allFieldsShort") : t("edit.edit")}</button>
      {/if}
      <Menu label={t("life.more")} items={actions} />
    {/if}
  </header>

  {#if retired}<p class="form-info retired-note">{t("life.retiredBanner")}</p>{/if}

  {#if data.variant_of}<p class="variant-note">{t("q.variantOf", { id: data.variant_of })}</p>{/if}

  {#if can}
    <InlineText class="stem" value={pick(question.data.stem)} placeholder={t("sheet.stem")} label={t("sheet.stem")} onsave={(v) => setText("stem", v)} />
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
    {#if data.half_points}<p class="muted small">{t("q.halfPoints")}</p>{/if}
    <h4 class="sub">{t("q.expected")}</h4>
    <InlineText value={pick(question.data.expected)} placeholder={t("sheet.expected")} onsave={(v) => setText("expected", v)} />
    <h4 class="sub">{t("q.markingNotes")}</h4>
    <InlineText value={pick(question.data.marking_notes)} placeholder={t("sheet.marking")} onsave={(v) => setText("marking_notes", v)} />
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
            <InlineText value={pick(option.feedback)} placeholder={t("sheet.feedback")} onsave={(v) => setOption(i, "feedback", v)} />
          </div>
          <button type="button" class="icon-btn small-icon danger option-remove" title={t("sheet.removeOption")} aria-label={t("sheet.removeOption")}
            onclick={() => removeOption(i)}><Icon name="remove" /></button>
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

  <section class="preview-section">
    <h4 class="sub">{t("q.findings")}</h4>
    {#if question.findings.length === 0}
      <p class="check-ok"><Icon name="check" />{t("q.noFindings")}</p>
    {:else}
      <ul class="findings">
        {#each question.findings as f}
          <li><span class="tag {severityClass[f.severity]}">{t(`sev.${f.severity}`)}</span>{findingText(f)}</li>
        {/each}
      </ul>
    {/if}
  </section>

  {#if !compact}
  <section class="preview-section">
    <dl class="meta">
      <dt>{t("q.meta.concept")}</dt><dd>{question.concept_name ?? data.concept}{#if question.concept_description}<span class="muted small concept-desc">{question.concept_description}</span>{/if}</dd>
      {#if can}
        <dt>{t("q.meta.level")}</dt>
        <dd><select class="select select-small" aria-label={t("q.meta.level")} value={question.data.level ?? ""} onchange={(e) => save({ level: e.currentTarget.value || null })}>
          {#if data.variant_of}<option value="">{t("sheet.inherit", { value: question.inherited?.level ? t(`level.${question.inherited.level}`) : "–" })}</option>{/if}
          {#each ["remember", "understand", "apply"] as level}<option value={level}>{t(`level.${level}`)}</option>{/each}
        </select></dd>
        <dt>{t("edit.time")}</dt>
        <dd><select class="select select-small" aria-label={t("edit.time")} value={question.data.time_seconds ?? ""} onchange={(e) => save({ time_seconds: e.currentTarget.value ? Number(e.currentTarget.value) : null })}>
          <option value="">{data.variant_of ? t("sheet.inherit", { value: question.inherited?.time_seconds ? formatTime(question.inherited.time_seconds) : "–" }) : t("q.noTime")}</option>
          {#each timeChoices as s}<option value={s}>{formatTime(s)}</option>{/each}
        </select></dd>
      {:else}
      <dt>{t("q.meta.level")}</dt><dd>{t(`level.${data.level}`)}{#if isInherited("level")}<span class="muted small"> · {t("q.inherited")}</span>{/if}</dd>
      <dt>{t("edit.time")}</dt><dd>{data.time_seconds ? formatTime(data.time_seconds) : t("q.noTime")}{#if isInherited("time_seconds")}<span class="muted small"> · {t("q.inherited")}</span>{/if}</dd>
      {/if}
      {#if data.public}
        <dt>{t("q.variants")}</dt><dd>{variants.length ? variants.join(", ") : t("q.noVariant")}</dd>
      {/if}
      {#if data.variant_of}
        <dt>{t("q.parent")}</dt><dd>{data.variant_of}{#if question.parent?.stem}<span class="muted small concept-desc">{question.parent.stem}</span>{/if}</dd>
      {/if}
      {#if data.coverage}<dt>{t("q.meta.coverage")}</dt><dd>{data.coverage}</dd>{/if}
      {#if data.misconception}<dt>{t("q.meta.misconception")}</dt><dd>{data.misconception}</dd>{/if}
      {#if reviewers.length}<dt>{t("q.meta.reviewed")}</dt><dd>{reviewers.join(", ")}</dd>{/if}
      {#if data.created_by || data.created_at}<dt>{t("q.meta.created")}</dt><dd>{t("q.by", { name: data.created_by || "–", date: formatDate(data.created_at) })}</dd>{/if}
      <dt>{t("q.meta.pool")}</dt><dd>{question.pool_name}</dd>
      {#if question.modified}<dt>{t("q.meta.modified")}</dt><dd>{data.changed_by ? `${data.changed_by}, ` : ""}{new Date(question.modified * 1000).toLocaleString(ui.lang === "de" ? "de-DE" : "en-GB", { dateStyle: "medium", timeStyle: "short" })}</dd>{/if}
      <dt>{t("q.meta.file")}</dt><dd class="small">{question.path}</dd>
    </dl>
  </section>
  {/if}
</article>
