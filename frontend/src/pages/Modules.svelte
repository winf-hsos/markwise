<script>
  import Icon from "../components/Icon.svelte";
  import NewModuleDialog from "../components/NewModuleDialog.svelte";
  import OpenFolderDialog from "../components/OpenFolderDialog.svelte";
  import AddPoolDialog from "../components/AddPoolDialog.svelte";
  import Menu from "../components/Menu.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { app, refreshWorkspace, setCurrentModule, showToast } from "../lib/state.svelte.js";

  const modules = $derived(app.workspace.modules);

  let newOpen = $state(false);
  let newPreset = $state(null);
  let openOpen = $state(false);
  let addPoolOpen = $state(false);
  let addPoolModule = $state(null);

  function newModule(preset = null) {
    newPreset = preset;
    newOpen = true;
  }

  async function run(action) {
    try {
      await action();
    } catch (err) {
      showToast(errorText(err));
    }
  }

  const makeCurrent = (m) =>
    run(async () => {
      await setCurrentModule(m.path);
      showToast(t("modules.switched", { name: m.name }));
    });

  const forget = (m) =>
    run(async () => {
      await call("forget_module", m.path);
      await refreshWorkspace();
      showToast(t("modules.forgotten", { name: m.name }));
    });

  const removePool = (m, p) =>
    run(async () => {
      await call("remove_pool", m.path, p.path);
      await refreshWorkspace();
      showToast(t("modules.poolRemoved"));
    });

  const reveal = (path) => run(() => call("reveal", path));
</script>

<div class="page">
  <div class="page-head">
    <div>
      <h1>{t("modules.title")}</h1>
      <p>{t("modules.lead")}</p>
    </div>
    {#if modules.length > 0}
      <div class="actions">
        <button class="btn" onclick={() => (openOpen = true)}><Icon name="folder" />{t("modules.open")}</button>
        <button class="btn primary" onclick={() => newModule()}><Icon name="plus" />{t("modules.new")}</button>
      </div>
    {/if}
  </div>

  {#if modules.length === 0}
    <div class="empty">
      <div class="mark"><Icon name="modules" /></div>
      <h2>{t("modules.empty.title")}</h2>
      <p>{t("modules.empty.text")}</p>
      <div class="actions">
        <button class="btn primary" onclick={() => newModule()}><Icon name="plus" />{t("modules.new")}</button>
        <button class="btn" onclick={() => (openOpen = true)}><Icon name="folder" />{t("modules.open")}</button>
      </div>
    </div>
  {:else}
    <div class="rows">
      {#each modules as m (m.path)}
        {@const current = m.path === app.settings?.current_module}
        <div class="row-item module-row" class:current>
          <div class="text">
            <div class="title">
              <span class="module-short">{m.short_name}</span>
              <h3>{m.name}</h3>
              {#if current}<span class="tag ok">{t("modules.current")}</span>{/if}
              {#if !m.exists}<span class="tag red">{t("modules.missing")}</span>{/if}
            </div>
            <span class="path"><Icon name="folder" />{m.path}</span>
            {#if m.exists}
              <ul class="pool-list">
                {#each m.pools as p (p.path)}
                  <li>
                    <Icon name="questions" />
                    <span class="pool-name">{p.name}</span>
                    {#if p.exists}
                      <span class="muted">{t(p.questions === 1 ? "modules.question" : "modules.questions", { count: p.questions })}</span>
                    {:else}
                      <span class="tag red">{t("modules.poolMissing")}</span>
                    {/if}
                    <span class="pool-actions">
                      {#if p.exists}<button class="link-btn" onclick={() => reveal(p.path)}>{t("modules.reveal")}</button>{/if}
                      <button class="link-btn" onclick={() => removePool(m, p)}>{t("modules.removePool")}</button>
                    </span>
                  </li>
                {:else}
                  <li class="muted">{t("modules.noPool")}</li>
                {/each}
              </ul>
            {/if}
          </div>
          <div class="control row-actions">
            {#if m.exists && !current}
              <button class="btn" onclick={() => makeCurrent(m)}>{t("modules.makeCurrent")}</button>
            {/if}
            <Menu label={m.name} items={[
              ...(m.exists ? [
                { label: t("modules.addPool"), icon: "plus", onclick: () => { addPoolModule = m; addPoolOpen = true; } },
                { label: t("modules.reveal"), icon: "folder", onclick: () => reveal(m.path) },
              ] : []),
              { label: t("modules.forget"), icon: "remove", onclick: () => forget(m) },
            ]} />
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<NewModuleDialog bind:open={newOpen} preset={newPreset} />
<OpenFolderDialog bind:open={openOpen} onpool={(path) => newModule({ mode: "existing", path })} />
<AddPoolDialog bind:open={addPoolOpen} module={addPoolModule} />
