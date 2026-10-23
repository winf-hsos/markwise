<script>
  import Dialog from "./Dialog.svelte";
  import FolderField from "./FolderField.svelte";
  import PoolChooser from "./PoolChooser.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { refreshWorkspace, showToast } from "../lib/state.svelte.js";

  // `preset` fills the pool part, for example when an opened folder turned out to be a pool.
  let { open = $bindable(false), preset = null } = $props();

  const blankPool = () => ({ mode: "new", path: "", name: "", languages: ["de", "en"], source: "" });

  let name = $state("");
  let shortName = $state("");
  let shortTouched = $state(false);
  let folder = $state("");
  let pool = $state(blankPool());
  let error = $state("");
  let busy = $state(false);

  // Start fresh every time the dialog opens.
  $effect(() => {
    if (open) {
      name = "";
      shortName = "";
      shortTouched = false;
      folder = "";
      pool = { ...blankPool(), ...(preset ?? {}) };
      lastSuggested = "";
      error = "";
    }
  });

  // Suggest a short name from the initials of the name until the person types one.
  $effect(() => {
    if (shortTouched) return;
    // Capitalised words only, so that "und", "and" or "of" do not count; a single word gives its first letters.
    const words = name.trim().split(/[\s-]+/).filter(Boolean);
    const capitalised = words.filter((w) => /^[A-ZÄÖÜ0-9]/.test(w));
    shortName = (capitalised.length > 1 ? capitalised.map((w) => w[0]).join("") : (words[0] ?? "").slice(0, 3)).toUpperCase().slice(0, 6);
  });

  // A new pool takes the module's name unless the person gave it another.
  let lastSuggested = "";
  $effect(() => {
    if (pool.mode === "new" && pool.name === lastSuggested) {
      pool.name = name;
      lastSuggested = name;
    }
  });

  const describeModuleFolder = (info) =>
    info.module ? "folder.module" : !info.exists ? "folder.missing" : info.empty ? "folder.empty" : "folder.content";

  async function create(event) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      const result = await call("create_module", { name, short_name: shortName, folder, pool: $state.snapshot(pool) });
      await refreshWorkspace();
      open = false;
      showToast(result.pool === "imported"
        ? t("newModule.imported", { name: result.module.name, count: result.created })
        : t("newModule.created", { name: result.module.name }));
    } catch (err) {
      error = errorText(err);
    } finally {
      busy = false;
    }
  }
</script>

<Dialog bind:open title={t("newModule.title")} lead={t("newModule.lead")} wide>
  <form id="new-module" class="form" onsubmit={create} oninput={() => (error = "")}>
    <div class="form-row">
      <label class="field grow">
        <span>{t("newModule.name")}</span>
        <input class="input" bind:value={name} placeholder={t("newModule.namePlaceholder")} />
      </label>
      <label class="field short">
        <span>{t("newModule.short")}</span>
        <input class="input" bind:value={shortName} oninput={() => (shortTouched = true)} maxlength="8" title={t("newModule.shortHint")} />
      </label>
    </div>
    <FolderField label={t("newModule.folder")} bind:value={folder} describe={describeModuleFolder} />

    <h3 class="form-section">{t("pool.section")}</h3>
    <PoolChooser bind:spec={pool} />

    {#if error}<p class="form-error" role="alert">{error}</p>{/if}
  </form>
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (open = false)}>{t("dialog.cancel")}</button>
    <button class="btn primary" type="submit" form="new-module" disabled={busy}>{t("newModule.create")}</button>
  {/snippet}
</Dialog>
