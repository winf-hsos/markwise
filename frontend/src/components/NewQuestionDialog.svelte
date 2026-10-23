<script>
  import Dialog from "./Dialog.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { slugify } from "../lib/slug.js";

  // `pools` as delivered by list_questions; `oncreated` receives the new question's detail.
  let { open = $bindable(false), pools = [], preset = {}, oncreated } = $props();

  let pool = $state("");
  let concept = $state("");
  let conceptName = $state("");
  let conceptDescription = $state("");
  let type = $state("single");
  let error = $state("");
  let busy = $state(false);

  const usable = $derived(pools.filter((p) => p.exists));
  const chosen = $derived(usable.find((p) => p.path === pool) ?? usable[0]);
  const isNew = $derived(concept === "__new");

  $effect(() => {
    if (open) {
      pool = preset.pool || usable[0]?.path || "";
      concept = preset.concept || "";
      conceptName = "";
      conceptDescription = "";
      type = "single";
      error = "";
    }
  });

  async function create(event) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      const detail = isNew
        ? await call("create_question", chosen.path, "", type, { name: conceptName, description: conceptDescription })
        : await call("create_question", chosen.path, concept, type);
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
        {#each chosen?.concepts ?? [] as c}<option value={c.id}>{c.name}</option>{/each}
        <option value="__new">{t("newQ.newConcept")} …</option>
      </select>
    </label>
    {#if isNew}
      <div class="new-concept">
        <label class="field">
          <span>{t("concepts.name")}</span>
          <input class="input" bind:value={conceptName} placeholder={t("concepts.namePlaceholder")} />
        </label>
        <label class="field">
          <span>{t("concepts.description")}</span>
          <input class="input" bind:value={conceptDescription} placeholder={t("concepts.descriptionPlaceholder")} />
          {#if conceptName.trim()}<small class="hint">{t("concepts.idPreview", { id: slugify(conceptName) })}</small>{/if}
        </label>
      </div>
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
    <button class="btn primary" type="submit" form="new-question" disabled={busy || !concept || (isNew && !conceptName.trim())}>{t("newQ.create")}</button>
  {/snippet}
</Dialog>
