<script>
  import { tick, untrack } from "svelte";
  import { highlight } from "../lib/highlight.js";
  import { inline } from "../lib/inline.js";
  import { t } from "../lib/i18n.svelte.js";

  // A text of a question shown as it reads, which turns into a field for its Markdown on a click. The tick,
  // Ctrl+Enter or leaving the field renders it again and hands the new text to `onsave`; Escape keeps the old one.
  // `code` shows and edits program code instead of Markdown. Without `onsave` the text is only shown.
  // `opened` starts with the field open, for a text just added.
  let { value = "", placeholder = "", code = false, language = "", label = "", tag = "div", opened = false, class: klass = "", onsave } = $props();

  let editing = $state(false);
  let draft = $state("");
  let area = $state(null);

  async function open(event) {
    if (!onsave || editing || event?.target?.closest?.("a")) return;
    draft = value ?? "";
    editing = true;
    await tick();
    area?.focus();
    fit();
  }

  $effect(() => {
    if (opened) untrack(() => open());
  });

  function fit() {
    if (!area) return;
    area.style.height = "auto";
    area.style.height = `${area.scrollHeight + 2}px`;
  }

  function confirm() {
    if (!editing) return;
    editing = false;
    const next = code ? draft.replace(/\s+$/, "") : draft.trim();
    if (next !== (value ?? "")) onsave?.(next);
  }

  function cancel() {
    editing = false;
  }

  function onkeydown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      cancel();
    } else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      confirm();
    } else if (event.key === "Tab" && code) {
      event.preventDefault();
      const { selectionStart: a, selectionEnd: b } = area;
      draft = `${draft.slice(0, a)}    ${draft.slice(b)}`;
      tick().then(() => area.setSelectionRange(a + 4, a + 4));
    }
  }

  // Leaving the field saves; its own buttons keep the focus (they act on mousedown's default being prevented).
  function onblur() {
    confirm();
  }
</script>

{#if editing}
  <div class="inline-edit {klass}" class:code>
    <textarea bind:this={area} bind:value={draft} class="input" aria-label={label || placeholder} spellcheck={!code}
      oninput={fit} {onkeydown} {onblur}></textarea>
    <div class="inline-tools">
      <span class="hint">{t(code ? "inline.hintCode" : "inline.hint")}</span>
      <button type="button" class="icon-btn small-icon" title={t("inline.cancel")} aria-label={t("inline.cancel")}
        onmousedown={(e) => e.preventDefault()} onclick={cancel}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" fill="none" stroke-width="1.8" stroke-linecap="round" /></svg></button>
      <button type="button" class="icon-btn small-icon inline-ok" title={t("inline.ok")} aria-label={t("inline.ok")}
        onmousedown={(e) => e.preventDefault()} onclick={confirm}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg></button>
    </div>
  </div>
{:else if code}
  <pre class="code-block hljs inline-view" class:editable={onsave} role={onsave ? "button" : null} tabindex={onsave ? 0 : null}
    title={onsave ? t("inline.click") : null} onclick={open} onkeydown={(e) => e.key === "Enter" && open(e)}><code>{@html highlight(value ?? "", language)}</code></pre>
{:else}
  <svelte:element this={tag} class="inline-view {klass}" class:editable={onsave} class:empty={!value} role={onsave ? "button" : null}
    tabindex={onsave ? 0 : null} title={onsave ? t("inline.click") : null} onclick={open} onkeydown={(e) => e.key === "Enter" && open(e)}>
    {#if value}{@html inline(value)}{:else if onsave}<span class="inline-placeholder">{placeholder}</span>{/if}
  </svelte:element>
{/if}
