<script>
  import Icon from "./Icon.svelte";
  import { inline } from "../lib/inline.js";
  import { t } from "../lib/i18n.svelte.js";

  // What the language model found and proposes, per field and language, each change to apply on its own or
  // all at once. `label(field)` names a field, `showLang` adds the language to each change, and `note`
  // ({ title, text }) shows something to check first, such as the model's calculation.
  let { findings = [], changes = [], label, showLang = false, note = null, onapply, onclose } = $props();

  const missing = $derived(changes.filter((c) => !c.before?.trim()));
</script>

<div class="assist-review">
  {#if note?.text}
    <div class="assist-note"><span class="hint">{note.title}</span><p>{note.text}</p></div>
  {/if}
  {#if findings.length}
    <ul>{#each findings as f}<li>{#if f.about}<b>{label(f.about)}:</b> {/if}{f.text}</li>{/each}</ul>
  {:else if !changes.length && !note?.text}
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
  <div class="assist-actions">
    {#if changes.length > 1}<button type="button" class="btn primary btn-small" onclick={() => onapply([...changes])}>{t("assist.applyAll")}</button>{/if}
    {#if missing.length && missing.length < changes.length}
      <button type="button" class="btn btn-small" onclick={() => onapply([...missing])}>{t("assist.applyMissing", { n: missing.length })}</button>
    {/if}
    <button type="button" class="btn ghost btn-small" onclick={onclose}>{changes.length ? t("assist.dismiss") : t("dialog.close")}</button>
  </div>
</div>
