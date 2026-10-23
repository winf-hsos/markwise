<script>
  import Dialog from "./Dialog.svelte";
  import CodeField from "./CodeField.svelte";
  import { CODE_LANGUAGES } from "../lib/highlight.js";
  import { t } from "../lib/i18n.svelte.js";

  // Add or change the code block below the question text. Nothing changes in the question until "Apply".
  let { open = $bindable(false), code = "", language = "", onapply } = $props();

  let draft = $state("");
  let draftLanguage = $state("");

  $effect(() => {
    if (open) {
      draft = code;
      draftLanguage = language;
    }
  });

  function apply(event) {
    event.preventDefault();
    onapply?.(draft.replace(/\s+$/, ""), draftLanguage);
    open = false;
  }
</script>

<Dialog bind:open title={code ? t("attach.codeEditTitle") : t("attach.codeTitle")} lead={t("attach.codeLead")} wide>
  <form id="code-dialog" class="form" onsubmit={apply}>
    <label class="field">
      <span>{t("edit.codeLanguage")}</span>
      <select class="select" bind:value={draftLanguage}>
        <option value="">{t("edit.autoLanguage")}</option>
        {#each CODE_LANGUAGES as [id, name]}<option value={id}>{name}</option>{/each}
      </select>
    </label>
    <div class="field">
      <span>{t("edit.code")}</span>
      <div class="code-dialog-field"><CodeField bind:value={draft} language={draftLanguage} label={t("edit.code")} /></div>
      <small class="hint">{t("attach.codeHint")}</small>
    </div>
  </form>
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (open = false)}>{t("dialog.cancel")}</button>
    <button class="btn primary" type="submit" form="code-dialog" disabled={!draft.trim()}>{t("attach.apply")}</button>
  {/snippet}
</Dialog>
