<script>
  import Dialog from "./Dialog.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";

  // A new exam of the current module: title, date, language and where the answers go. `languages` are those the
  // module's pools are written in; `oncreated` receives the new exam.
  let { open = $bindable(false), module = "", languages = ["de", "en"], oncreated } = $props();

  let title = $state("");
  let date = $state("");
  let language = $state("de");
  let answers = $state("sheet");
  let error = $state("");
  let busy = $state(false);

  $effect(() => {
    if (open) {
      title = "";
      date = "";
      language = languages.includes("de") ? "de" : languages[0] ?? "de";
      answers = "sheet";
      error = "";
    }
  });

  async function create(event) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      const exam = await call("create_exam", module, { title, date, language, answers });
      open = false;
      oncreated?.(exam);
    } catch (err) {
      error = errorText(err);
    } finally {
      busy = false;
    }
  }
</script>

<Dialog bind:open title={t("exams.new")} lead={t("exams.newLead")}>
  <form id="new-exam" class="form-grid single" onsubmit={create}>
    <label class="field"><span>{t("exams.examTitle")}</span>
      <input class="input" bind:value={title} placeholder={t("exams.titlePlaceholder")} /></label>
    <label class="field"><span>{t("exams.date")}</span>
      <input class="input" type="date" bind:value={date} /></label>
    {#if languages.length > 1}
      <div class="field">
        <span>{t("exams.language")}</span>
        <div class="seg" role="group">
          {#each languages as l}<button type="button" class:on={language === l} onclick={() => (language = l)}>{l === "de" ? "Deutsch" : "English"}</button>{/each}
        </div>
      </div>
    {/if}
    <div class="field">
      <span>{t("exams.answers")}</span>
      <div class="choice-cards">
        {#each ["sheet", "inline"] as mode}
          <label class="choice-card" class:on={answers === mode}>
            <input type="radio" name="answers" value={mode} bind:group={answers} />
            <b>{t(`exams.answers.${mode}`)}</b>
            <span class="hint">{t(`exams.answers.${mode}Hint`)}</span>
          </label>
        {/each}
      </div>
    </div>
    {#if error}<p class="form-error" role="alert">{error}</p>{/if}
  </form>
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (open = false)}>{t("dialog.cancel")}</button>
    <button class="btn primary" type="submit" form="new-exam" disabled={busy || !title.trim() || !date}>{t("exams.create")}</button>
  {/snippet}
</Dialog>
