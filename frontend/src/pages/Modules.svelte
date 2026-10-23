<script>
  import Icon from "../components/Icon.svelte";
  import { t } from "../lib/i18n.svelte.js";
  import { app } from "../lib/state.svelte.js";

  const modules = $derived(app.workspace.modules);
</script>

<div class="page">
  <div class="page-head">
    <div>
      <h1>{t("modules.title")}</h1>
      <p>{t("modules.lead")}</p>
    </div>
    <div class="actions">
      <button class="btn" disabled title={t("soon.step2")}><Icon name="folder" />{t("modules.open")}</button>
      <button class="btn primary" disabled title={t("soon.step2")}><Icon name="plus" />{t("modules.new")}</button>
    </div>
  </div>

  {#if modules.length === 0}
    <div class="panel empty">
      <Icon name="modules" />
      <h2>{t("modules.empty.title")}</h2>
      <p>{t("modules.empty.text")}</p>
      <p class="soon">{t("soon.step2")}</p>
    </div>
  {:else}
    <div class="module-list">
      {#each modules as m}
        <div class="panel module-card" class:current={m.path === app.settings?.current_module}>
          <div class="module-main">
            <div class="module-title"><span class="module-short">{m.short_name}</span><h3>{m.name}</h3></div>
            <div class="module-facts">
              {#if m.exists}
                <span>{t("modules.pools")}: {m.pools.map((p) => p.name).join(", ") || "–"}</span>
              {:else}
                <span class="tag red">{t("modules.missing")}</span>
              {/if}
              <span class="path"><Icon name="folder" />{m.path}</span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
