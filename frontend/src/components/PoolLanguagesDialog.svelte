<script>
  import Dialog from "./Dialog.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { refreshWorkspace, showToast } from "../lib/state.svelte.js";

  // The languages every question of a pool is written in.
  let { open = $bindable(false), pool = null } = $props();

  let chosen = $state([]);
  let busy = $state(false);
  let error = $state("");

  $effect(() => {
    if (open && pool) {
      chosen = [...(pool.languages ?? [])];
      error = "";
    }
  });

  const added = $derived(chosen.filter((l) => !(pool?.languages ?? []).includes(l)));
  const dropped = $derived((pool?.languages ?? []).filter((l) => !chosen.includes(l)));
  const name = (l) => (l === "de" ? "Deutsch" : "English");

  function toggle(lang) {
    chosen = chosen.includes(lang) ? chosen.filter((l) => l !== lang) : [...chosen, lang];
  }

  async function save() {
    busy = true;
    error = "";
    try {
      const answer = await call("set_pool_languages", pool.path, chosen);
      await refreshWorkspace();
      open = false;
      showToast(answer.untranslated
        ? t("poolLang.savedMissing", { n: answer.untranslated, langs: answer.added.map(name).join(", ") })
        : t("poolLang.saved"));
    } catch (err) {
      error = errorText(err);
    } finally {
      busy = false;
    }
  }
</script>

<Dialog bind:open title={t("poolLang.title", { name: pool?.name ?? "" })} lead={t("poolLang.lead")}>
  <div class="field">
    <span>{t("pool.languages")}</span>
    <div class="chips">
      {#each ["de", "en"] as lang}
        <button type="button" class="chip" class:on={chosen.includes(lang)} aria-pressed={chosen.includes(lang)} onclick={() => toggle(lang)}>{name(lang)}</button>
      {/each}
    </div>
  </div>
  {#if added.length}<p class="form-info">{t("poolLang.addedNote", { langs: added.map(name).join(", ") })}</p>{/if}
  {#if dropped.length}<p class="form-info">{t("poolLang.droppedNote", { langs: dropped.map(name).join(", ") })}</p>{/if}
  {#if error}<p class="form-error" role="alert">{error}</p>{/if}
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (open = false)}>{t("dialog.cancel")}</button>
    <button class="btn primary" type="button" onclick={save} disabled={busy || !chosen.length || (!added.length && !dropped.length)}>{t("poolLang.save")}</button>
  {/snippet}
</Dialog>
