<script>
  import Dialog from "./Dialog.svelte";
  import FolderField from "./FolderField.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { refreshWorkspace, showToast } from "../lib/state.svelte.js";

  // `onpool` is called with the folder when the chosen folder is a question pool instead of a module.
  let { open = $bindable(false), onpool } = $props();

  let folder = $state("");
  let error = $state("");
  let isPool = $state(false);

  $effect(() => {
    if (open) {
      folder = "";
      error = "";
      isPool = false;
    }
  });

  const describe = (info) => (info.module ? null : info.pool ? "folder.pool" : null);

  async function openModule(event) {
    event.preventDefault();
    error = "";
    isPool = false;
    try {
      const module = await call("open_module", folder.trim());
      await refreshWorkspace();
      open = false;
      showToast(t("openFolder.opened", { name: module.name }));
    } catch (err) {
      error = errorText(err);
      isPool = err.code === "is_pool";
    }
  }
</script>

<Dialog bind:open title={t("openFolder.title")} lead={t("openFolder.lead")}>
  <form id="open-folder" class="form" oninput={() => (error = "")} onsubmit={openModule}>
    <FolderField label={t("newModule.folder")} bind:value={folder} {describe} />
    {#if error}<p class={isPool ? "form-info" : "form-error"} role="alert">{error}</p>{/if}
  </form>
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (open = false)}>{t("dialog.cancel")}</button>
    {#if isPool}
      <button class="btn primary" type="button" onclick={() => { open = false; onpool?.(folder.trim()); }}>{t("openFolder.newWithPool")}</button>
    {:else}
      <button class="btn primary" type="submit" form="open-folder">{t("openFolder.open")}</button>
    {/if}
  {/snippet}
</Dialog>
