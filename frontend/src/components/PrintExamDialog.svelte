<script>
  import Dialog from "./Dialog.svelte";
  import Icon from "./Icon.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { showToast } from "../lib/state.svelte.js";

  // Typesets an exam into its print folder: how many numbered copies, then the PDFs of the last print to open.
  // `exam` is the exam as get_exam answers; `onprinted` receives it again with the new files.
  let { open = $bindable(false), exam, onprinted } = $props();

  let copies = $state(30);
  let busy = $state(false);
  let error = $state("");

  $effect(() => {
    if (open) error = "";
  });

  const errors = $derived((exam?.findings ?? []).filter((f) => f.severity === "error").length);
  const pdfs = $derived((exam?.printed ?? []).filter((f) => f.name.endsWith(".pdf")));
  const when = $derived(
    exam?.printed?.length ? new Date(Math.max(...exam.printed.map((f) => f.modified)) * 1000).toLocaleString() : "",
  );

  async function typeset(event) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      const answer = await call("print_exam", exam.path, Math.max(1, Math.round(copies)));
      onprinted?.(answer);
      showToast(t("print.done", { n: Math.max(1, Math.round(copies)) }));
    } catch (err) {
      error = errorText(err);
    } finally {
      busy = false;
    }
  }

  const openFile = (name) => call("open_printed", exam.path, name).catch((err) => showToast(errorText(err)));
</script>

<Dialog bind:open title={t("print.title")} lead={t(exam?.answers === "inline" ? "print.leadInline" : "print.leadSheet")}>
  <form id="print-exam" class="form-grid single" onsubmit={typeset}>
    <label class="field"><span>{t("print.copies")}</span>
      <input class="input" type="number" min="1" max="999" step="1" bind:value={copies} />
      <span class="hint">{t("print.copiesHint")}</span></label>
    {#if errors}<p class="form-error" role="alert">{t("print.hasErrors", { n: errors })}</p>{/if}
    {#if pdfs.length}
      <div class="field">
        <span>{t("print.last", { when })}</span>
        <div class="print-files">
          {#each pdfs as f (f.name)}
            <button type="button" class="btn ghost" onclick={() => openFile(f.name)}><Icon name="file" />{f.name}</button>
          {/each}
        </div>
      </div>
    {/if}
    {#if error}<p class="form-error" role="alert">{error}</p>{/if}
  </form>
  {#if busy}
    <div class="assist-veil" role="status"><div class="spinner"></div><b>{t("print.busy")}</b></div>
  {/if}
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (open = false)}>{t("dialog.close")}</button>
    <button class="btn primary" type="submit" form="print-exam" disabled={busy || errors > 0 || !exam?.entries?.length}>
      <Icon name="print" />{t(pdfs.length ? "print.again" : "print.make")}</button>
  {/snippet}
</Dialog>
