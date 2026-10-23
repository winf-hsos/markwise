<script>
  import Dialog from "./Dialog.svelte";
  import Icon from "./Icon.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { showToast } from "../lib/state.svelte.js";
  import { slugify } from "../lib/slug.js";

  // Name and describe the concepts of a pool. Identifiers and folders never change here.
  let { open = $bindable(false), pools = [], onchanged } = $props();

  let pool = $state("");
  let concepts = $state([]); // rows with a draft name and description
  let adding = $state({ name: "", description: "" });
  let error = $state("");

  const usable = $derived(pools.filter((p) => p.exists));

  async function load() {
    if (!pool) return;
    const list = await call("list_concepts", pool);
    concepts = list.map((c) => ({ ...c, draftName: c.named ? c.name : "", draftDescription: c.description }));
  }

  $effect(() => {
    if (open) {
      pool = usable[0]?.path ?? "";
      adding = { name: "", description: "" };
      error = "";
    }
  });

  $effect(() => {
    if (open && pool) load();
  });

  const changed = (c) => c.draftName.trim() !== (c.named ? c.name : "") || c.draftDescription.trim() !== c.description;

  async function save(c) {
    error = "";
    try {
      await call("update_concept", pool, c.id, c.draftName, c.draftDescription);
      await load();
      showToast(t("concepts.saved"));
      onchanged?.();
    } catch (err) {
      error = errorText(err);
    }
  }

  async function add(event) {
    event.preventDefault();
    error = "";
    try {
      const created = await call("add_concept", pool, adding.name, adding.description);
      adding = { name: "", description: "" };
      await load();
      showToast(t("concepts.added", { name: created.name }));
      onchanged?.();
    } catch (err) {
      error = errorText(err);
    }
  }
</script>

<Dialog bind:open title={t("concepts.title")} lead={t("concepts.lead")} wide>
  {#if usable.length > 1}
    <label class="field concepts-pool">
      <span>{t("newQ.pool")}</span>
      <select class="select" bind:value={pool}>
        {#each usable as p}<option value={p.path}>{p.name}</option>{/each}
      </select>
    </label>
  {/if}

  <ul class="concept-list">
    {#each concepts as c (c.id)}
      <li>
        <div class="concept-fields">
          <input class="input" bind:value={c.draftName} placeholder={c.name} aria-label={t("concepts.name")} />
          <input class="input" bind:value={c.draftDescription} placeholder={t("concepts.description")} aria-label={t("concepts.description")} />
        </div>
        <div class="concept-meta">
          <span class="muted small">{t(c.questions === 1 ? "modules.question" : "modules.questions", { count: c.questions })}</span>
          <span class="concept-id">{c.id}</span>
        </div>
        <button class="btn" class:primary={changed(c)} disabled={!changed(c) || !c.draftName.trim()} onclick={() => save(c)}>
          {t("settings.save")}
        </button>
      </li>
    {/each}
  </ul>

  <form class="concept-add" onsubmit={add} oninput={() => (error = "")}>
    <div class="concept-fields">
      <input class="input" bind:value={adding.name} placeholder={t("concepts.namePlaceholder")} aria-label={t("concepts.name")} />
      <input class="input" bind:value={adding.description} placeholder={t("concepts.descriptionPlaceholder")} aria-label={t("concepts.description")} />
    </div>
    <div class="concept-meta">
      {#if adding.name.trim()}<span class="concept-id">{slugify(adding.name)}</span>{/if}
    </div>
    <button class="btn" type="submit" disabled={!adding.name.trim()}><Icon name="plus" />{t("concepts.add")}</button>
  </form>
  {#if error}<p class="form-error" role="alert">{error}</p>{/if}

  {#snippet footer()}
    <button class="btn" type="button" onclick={() => (open = false)}>{t("dialog.close")}</button>
  {/snippet}
</Dialog>
