<script>
  import Dialog from "./Dialog.svelte";
  import PoolChooser from "./PoolChooser.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { refreshWorkspace, showToast } from "../lib/state.svelte.js";

  let { open = $bindable(false), module = null } = $props();

  let pool = $state({ mode: "existing", path: "", name: "", languages: ["de", "en"], source: "" });
  let error = $state("");
  let busy = $state(false);

  $effect(() => {
    if (open) {
      pool = { mode: "existing", path: "", name: "", languages: ["de", "en"], source: "" };
      error = "";
    }
  });

  async function add(event) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      await call("add_pool", module.path, $state.snapshot(pool));
      await refreshWorkspace();
      open = false;
      showToast(t("addPool.added"));
    } catch (err) {
      error = errorText(err);
    } finally {
      busy = false;
    }
  }
</script>

<Dialog bind:open title={t("addPool.title")} lead={module ? t("addPool.lead", { name: module.name }) : ""} wide>
  <form id="add-pool" class="form" oninput={() => (error = "")} onsubmit={add}>
    <PoolChooser bind:spec={pool} />
    {#if error}<p class="form-error" role="alert">{error}</p>{/if}
  </form>
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (open = false)}>{t("dialog.cancel")}</button>
    <button class="btn primary" type="submit" form="add-pool" disabled={busy}>{t("addPool.add")}</button>
  {/snippet}
</Dialog>
