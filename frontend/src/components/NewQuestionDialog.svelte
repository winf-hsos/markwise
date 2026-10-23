<script>
  import Dialog from "./Dialog.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";

  // `pools` as delivered by list_questions; `oncreated` receives the new question's detail.
  let { open = $bindable(false), pools = [], preset = {}, oncreated } = $props();

  let pool = $state("");
  let concept = $state("");
  let newConcept = $state("");
  let type = $state("single");
  let error = $state("");
  let busy = $state(false);

  const usable = $derived(pools.filter((p) => p.exists));
  const chosen = $derived(usable.find((p) => p.path === pool) ?? usable[0]);
  // A pool without a fixed list of concepts may get new ones; its concepts are its folders.
  const fixedList = $derived(chosen?.fixed_concepts ?? false);

  $effect(() => {
    if (open) {
      pool = preset.pool || usable[0]?.path || "";
      concept = preset.concept || "";
      newConcept = "";
      type = "single";
      error = "";
    }
  });

  async function create(event) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      const name = concept === "__new" ? newConcept.trim() : concept;
      const detail = await call("create_question", chosen.path, name, type);
      open = false;
      oncreated?.(detail);
    } catch (err) {
      error = errorText(err);
    } finally {
      busy = false;
    }
  }
</script>

<Dialog bind:open title={t("newQ.title")}>
  <form id="new-question" class="form" onsubmit={create} oninput={() => (error = "")}>
    {#if usable.length > 1}
      <label class="field">
        <span>{t("newQ.pool")}</span>
        <select class="select" bind:value={pool}>
          {#each usable as p}<option value={p.path}>{p.name}</option>{/each}
        </select>
      </label>
    {/if}
    <label class="field">
      <span>{t("newQ.concept")}</span>
      <select class="select" bind:value={concept}>
        <option value="" disabled>–</option>
        {#each chosen?.concepts ?? [] as c}<option value={c}>{c}</option>{/each}
        {#if !fixedList}<option value="__new">{t("newQ.newConcept")} …</option>{/if}
      </select>
    </label>
    {#if concept === "__new"}
      <label class="field">
        <span>{t("newQ.newConcept")}</span>
        <input class="input" bind:value={newConcept} placeholder="code-systems" />
        <small class="hint">{t("newQ.conceptHint")}</small>
      </label>
    {/if}
    <div class="field">
      <span>{t("newQ.type")}</span>
      <div class="seg seg-wide" role="group" aria-label={t("newQ.type")}>
        {#each ["single", "multiple", "free_text"] as v}
          <button type="button" class:on={type === v} onclick={() => (type = v)}>{t(`type.${v}`)}</button>
        {/each}
      </div>
    </div>
    {#if error}<p class="form-error" role="alert">{error}</p>{/if}
  </form>
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (open = false)}>{t("dialog.cancel")}</button>
    <button class="btn primary" type="submit" form="new-question" disabled={busy || !concept || (concept === "__new" && !newConcept.trim())}>{t("newQ.create")}</button>
  {/snippet}
</Dialog>
