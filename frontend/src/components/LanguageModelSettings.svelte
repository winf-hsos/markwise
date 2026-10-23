<script>
  import Icon from "./Icon.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { app, loadLlm, showToast, updateSettings } from "../lib/state.svelte.js";

  // Switching the language model on, storing the key, choosing the model. Nothing is sent before it is on.
  let key = $state("");
  let models = $state([]);
  let busy = $state(false);
  let error = $state("");

  const enabled = $derived(app.settings?.llm_enabled ?? false);
  const hasKey = $derived(app.llm?.has_key ?? false);

  async function loadModels() {
    if (!hasKey) return;
    try {
      models = await call("llm_models");
    } catch (err) {
      error = errorText(err);
    }
  }

  $effect(() => {
    if (enabled && hasKey && !models.length) loadModels();
  });

  async function toggle() {
    await updateSettings({ llm_enabled: !enabled });
    await loadLlm();
  }

  async function saveKey(event) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      models = await call("set_llm_key", key);
      key = "";
      if (!app.settings.llm_model && models.length) await updateSettings({ llm_model: models.find((m) => m.includes("mini")) ?? models[0] });
      await loadLlm();
      showToast(t("llm.keySaved"));
    } catch (err) {
      error = errorText(err);
    } finally {
      busy = false;
    }
  }

  async function removeKey() {
    await call("remove_llm_key");
    models = [];
    await loadLlm();
    showToast(t("llm.keyRemoved"));
  }

  async function chooseModel(event) {
    await updateSettings({ llm_model: event.currentTarget.value });
    await loadLlm();
  }
</script>

<section>
  <h2 class="section-title">{t("llm.title")}</h2>
  <div class="rows">
    <div class="row-item">
      <div class="text">
        <b>{t("llm.use")}</b>
        <span class="hint">{t("llm.useHint")}</span>
      </div>
      <button class="switch" class:on={enabled} role="switch" aria-checked={enabled} aria-label={t("llm.use")} onclick={toggle}></button>
    </div>
    {#if enabled}
      <form class="row-item" onsubmit={saveKey}>
        <div class="text">
          <b>{t("llm.key")}</b>
          <span class="hint">{hasKey ? t("llm.keyStored") : t("llm.keyHint")}</span>
        </div>
        <div class="control">
          {#if hasKey}
            <span class="released"><Icon name="check" />{t("llm.keyOk")}</span>
            <button class="btn ghost" type="button" onclick={removeKey}>{t("llm.removeKey")}</button>
          {:else}
            <input class="input" type="password" bind:value={key} placeholder="sk-…" autocomplete="off" aria-label={t("llm.key")} />
            <button class="btn primary" type="submit" disabled={busy || !key.trim()}>{busy ? t("llm.checking") : t("llm.saveKey")}</button>
          {/if}
        </div>
      </form>
      {#if hasKey}
        <div class="row-item">
          <div class="text"><b>{t("llm.model")}</b><span class="hint">{t("llm.modelHint")}</span></div>
          <select class="select model-select" value={app.settings?.llm_model ?? ""} onchange={chooseModel} aria-label={t("llm.model")}>
            {#if !app.settings?.llm_model}<option value="">–</option>{/if}
            {#each models.length ? models : [app.settings?.llm_model].filter(Boolean) as m}<option value={m}>{m}</option>{/each}
          </select>
        </div>
      {/if}
      <div class="row-item">
        <p class="hint privacy">{t("llm.privacy")}</p>
      </div>
    {/if}
    {#if error}<div class="row-item"><p class="form-error">{error}</p></div>{/if}
  </div>
</section>
