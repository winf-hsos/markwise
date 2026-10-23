<script>
  import FolderField from "./FolderField.svelte";
  import { t } from "../lib/i18n.svelte.js";

  // How a module gets its questions: a new pool, an existing one, or an earlier question bank imported.
  let { spec = $bindable() } = $props();

  const modes = ["new", "existing", "import"];

  function toggleLanguage(lang) {
    spec.languages = spec.languages.includes(lang)
      ? spec.languages.filter((l) => l !== lang)
      : [...spec.languages, lang].sort();
  }

  const describeTarget = (info) =>
    spec.mode === "existing"
      ? info.pool ? "folder.pool" : null
      : info.pool ? "folder.pool" : !info.exists ? "folder.missing" : info.empty ? "folder.empty" : "folder.content";
</script>

<div class="seg seg-wide" role="tablist" aria-label={t("pool.section")}>
  {#each modes as mode}
    <button type="button" role="tab" aria-selected={spec.mode === mode} class:on={spec.mode === mode} onclick={() => (spec.mode = mode)}>
      {t(`pool.mode.${mode}`)}
    </button>
  {/each}
</div>

{#if spec.mode === "import"}
  <FolderField label={t("pool.source")} kind="file" bind:value={spec.source} placeholder="…\questions\pool.toml" />
{/if}

<FolderField label={t("pool.folder")} bind:value={spec.path} hint={spec.mode === "existing" ? "" : t("pool.folderHint")} describe={describeTarget} />

{#if spec.mode === "new"}
  <div class="form-row">
    <label class="field grow">
      <span>{t("pool.name")}</span>
      <input class="input" bind:value={spec.name} />
    </label>
    <div class="field">
      <span>{t("pool.languages")}</span>
      <div class="chips">
        {#each ["de", "en"] as lang}
          <button type="button" class="chip" class:on={spec.languages.includes(lang)} aria-pressed={spec.languages.includes(lang)} onclick={() => toggleLanguage(lang)}>
            {lang === "de" ? "Deutsch" : "English"}
          </button>
        {/each}
      </div>
    </div>
  </div>
{:else if spec.mode === "import"}
  <p class="hint">{t("pool.importHint")}</p>
{/if}
