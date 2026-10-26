<script>
  import Icon from "./Icon.svelte";
  import { inline } from "../lib/inline.js";
  import { t, ui } from "../lib/i18n.svelte.js";

  // What the language model found and proposes, per field and language, each change to apply on its own or
  // all at once. `label(field)` names a field, `showLang` adds the language to each change, and `note`
  // ({ title, text }) shows something to check first, such as the model's calculation. `additions` are new wrong
  // options, each added on its own with `onadd`.
  let { findings = [], changes = [], additions = [], label, showLang = false, note = null, title = "", onapply, onadd, onclose } = $props();
  const lang = $derived(ui.lang);
  const textIn = (texts) => texts?.[lang] || Object.values(texts ?? {}).find(Boolean) || "";

  const missing = $derived(changes.filter((c) => !c.before?.trim()));
  const count = $derived(changes.length + additions.length);

  function applyEverything() {
    onapply([...changes]);
    if (additions.length) onadd([...additions]);
  }
</script>

<div class="assist-review">
  <div class="assist-bar">
    <span class="assist-title"><Icon name="wand" />{title}{#if count}<span class="count">{count}</span>{/if}</span>
    {#if count}
      <button type="button" class="btn primary btn-small" onclick={applyEverything}>{t("assist.applyAll")}</button>
      {#if missing.length && missing.length < changes.length}
        <button type="button" class="btn btn-small" onclick={() => onapply([...missing])}>{t("assist.applyMissing", { n: missing.length })}</button>
      {/if}
    {/if}
    <button type="button" class="btn ghost btn-small" onclick={onclose}>{count ? t("assist.dismiss") : t("dialog.close")}</button>
  </div>
  {#if note?.text}
    <div class="assist-note"><span class="hint">{note.title}</span><p>{note.text}</p></div>
  {/if}
  {#if findings.length}
    <ul>{#each findings as f}<li>{#if f.about}<b>{label(f.about)}:</b> {/if}{f.text}</li>{/each}</ul>
  {:else if !changes.length && !additions.length && !note?.text}
    <p class="check-ok"><Icon name="check" />{t("assist.nothing")}</p>
  {/if}
  {#each changes as change (change.field + change.lang)}
    <div class="assist-suggestion">
      <div class="assist-change-head">
        <span class="hint">{label(change.field)}{#if showLang}<span class="lang-tag">{change.lang.toUpperCase()}</span>{/if}</span>
        <button type="button" class="btn primary btn-small" onclick={() => onapply([change])}>{t("attach.apply")}</button>
      </div>
      {#if change.before?.trim()}<div class="assist-before">{@html inline(change.before)}</div>{/if}
      <div class="assist-after">{@html inline(change.text)}</div>
    </div>
  {/each}
  {#each additions as option}
    <div class="assist-suggestion">
      <div class="assist-change-head">
        <span class="hint">{t("assist.newOption")}</span>
        <button type="button" class="btn primary btn-small" onclick={() => onadd([option])}>{t("assist.add")}</button>
      </div>
      <div class="assist-after">{@html inline(textIn(option.text))}</div>
      <span class="option-feedback">{@html inline(textIn(option.feedback))}</span>
      {#if showLang}
        {#each Object.entries(option.text).filter(([l]) => l !== lang && option.text[l]) as [l, text]}
          <span class="proposal-other"><span class="lang-tag">{l.toUpperCase()}</span>{@html inline(text)}</span>
        {/each}
      {/if}
      {#if option.misconception}<span class="proposal-why">{t("assist.misconception")}: {option.misconception}</span>{/if}
    </div>
  {/each}
</div>
