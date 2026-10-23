<script>
  import Icon from "./Icon.svelte";
  import { t } from "../lib/i18n.svelte.js";
  import { app, setCurrentModule } from "../lib/state.svelte.js";

  let open = $state(false);

  const modules = $derived(app.workspace.modules);
  const current = $derived(modules.find((m) => m.path === app.settings?.current_module) ?? null);

  function closeOnOutside(event) {
    if (open && !event.target.closest(".module-switch")) open = false;
  }
</script>

<svelte:window onclick={closeOnOutside} />

<header class="topbar">
  <div class="module-switch" class:open>
    <button class="module-current" aria-haspopup="true" aria-expanded={open} onclick={() => (open = !open)}>
      {#if current}
        <span class="module-short">{current.short_name}</span><span>{current.name}</span>
      {:else}
        <span class="muted">{t("top.noModule")}</span>
      {/if}
      <Icon name="chevron" />
    </button>
    <div class="module-menu" role="menu">
      {#each modules as m}
        <button role="menuitem" class:on={m.path === current?.path} disabled={!m.exists}
          onclick={() => { open = false; setCurrentModule(m.path); }}><span class="module-short">{m.short_name}</span>{m.name}</button>
      {/each}
      <a role="menuitem" href="#/modules" class="all" onclick={() => (open = false)}>{t("top.allModules")}</a>
    </div>
  </div>
  {#if current}
    <span class="path"><Icon name="folder" />{current.path}</span>
  {/if}
</header>
