<script>
  import Icon from "./Icon.svelte";
  import { highlight } from "../lib/highlight.js";
  import { findingText, t, ui } from "../lib/i18n.svelte.js";

  // A read-only view of one question: text, options with the correct ones marked, findings and metadata.
  let { question, variants = [], compact = false, onopen, onedit } = $props();

  const data = $derived(question.data);
  const languages = $derived(question.languages);
  let lang = $state(null);
  const shown = $derived(lang && languages.includes(lang) ? lang : languages.includes(ui.lang) ? ui.lang : languages[0]);

  const pick = (value) => (value && typeof value === "object" ? value[shown] ?? "" : value ?? "");
  const severityClass = { error: "red", warning: "warn", note: "" };
  const useKey = (d) => {
    const exam = typeof d.exam === "boolean" ? d.exam : !d.public;
    return d.public && exam ? "use.both" : d.public ? "use.practice" : "use.exam";
  };
</script>

<article class="preview">
  <header class="preview-head">
    <div class="preview-title">
      <span class="qid">{data.id}</span>
      <span class="tag">{t(`type.${data.type}`)}</span>
      <span class="tag" class:ok={data.status === "reviewed" || data.status === "piloted"}>{t(`status.${data.status}`)}</span>
      <span class="tag">{t(useKey(data))}</span>
    </div>
    {#if languages.length > 1}
      <div class="seg seg-small" role="group">
        {#each languages as code}
          <button class:on={shown === code} onclick={() => (lang = code)}>{code.toUpperCase()}</button>
        {/each}
      </div>
    {/if}
  </header>

  {#if data.variant_of}<p class="variant-note">{t("q.variantOf", { id: data.variant_of })}</p>{/if}

  <div class="stem">{pick(data.stem)}</div>
  {#if data.code}<pre class="code-block hljs"><code>{@html highlight(data.code, data.code_language)}</code></pre>{/if}
  {#if question.figures?.length}
    <div class="figures" style="--columns: {question.figures.length > 1 ? question.image_columns ?? 1 : 1}">
      {#each question.figures as f (f.name)}
        <figure class="figure">{#if f.data}<img src={f.data} alt={t("q.image")} />{:else}<span class="missing-figure">{f.name}</span>{/if}</figure>
      {/each}
    </div>
  {/if}

  {#if data.type === "free_text"}
    <p class="muted small">{t("q.points", { n: data.points })}{data.half_points ? ` · ${t("q.halfPoints")}` : ""}</p>
    {#if pick(data.expected)}<h4 class="sub">{t("q.expected")}</h4><p class="prose">{pick(data.expected)}</p>{/if}
    {#if pick(data.marking_notes)}<h4 class="sub">{t("q.markingNotes")}</h4><p class="prose">{pick(data.marking_notes)}</p>{/if}
  {:else}
    <ol class="options">
      {#each data.options ?? [] as option}
        <li class:correct={option.correct}>
          <span class="box" aria-hidden="true">{#if option.correct}<Icon name="check" />{/if}</span>
          <div>
            <div class="option-text"><b>{option.id}</b> {pick(option.text)}{#if option.correct}<span class="sr">({t("q.correct")})</span>{/if}</div>
            {#if pick(option.feedback)}<div class="option-feedback">{pick(option.feedback)}</div>{/if}
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
      <dt>{t("q.meta.level")}</dt><dd>{t(`level.${data.level}`)}</dd>
      {#if data.public && data.type !== "free_text"}
        <dt>{t("q.variants")}</dt><dd>{variants.length ? variants.join(", ") : t("q.noVariant")}</dd>
      {/if}
      {#if data.coverage}<dt>{t("q.meta.coverage")}</dt><dd>{data.coverage}</dd>{/if}
      {#if data.misconception}<dt>{t("q.meta.misconception")}</dt><dd>{data.misconception}</dd>{/if}
      {#if data.reviewed_by?.length}<dt>{t("q.meta.reviewed")}</dt><dd>{data.reviewed_by.join(", ")}</dd>{/if}
      <dt>{t("q.meta.pool")}</dt><dd>{question.pool_name}</dd>
      {#if question.modified}<dt>{t("q.meta.modified")}</dt><dd>{new Date(question.modified * 1000).toLocaleString(ui.lang === "de" ? "de-DE" : "en-GB", { dateStyle: "medium", timeStyle: "short" })}</dd>{/if}
      <dt>{t("q.meta.file")}</dt><dd class="small">{question.path}</dd>
    </dl>
    <div class="preview-actions">
      <button class="btn primary" onclick={() => onedit?.()}><Icon name="edit" />{t("edit.edit")}</button>
      <button class="btn ghost" onclick={() => onopen?.(question.path)}><Icon name="upload" />{t("q.openFile")}</button>
    </div>
  </section>
  {/if}
</article>
