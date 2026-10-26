<script>
  import Nav from "./components/Nav.svelte";
  import Topbar from "./components/Topbar.svelte";
  import Modules from "./pages/Modules.svelte";
  import Questions from "./pages/Questions.svelte";
  import Concepts from "./pages/Concepts.svelte";
  import Exams from "./pages/Exams.svelte";
  import Settings from "./pages/Settings.svelte";
  import ConfirmDialog from "./components/ConfirmDialog.svelte";
  import { tick, untrack } from "svelte";
  import { t } from "./lib/i18n.svelte.js";
  import { route } from "./lib/router.svelte.js";
  import { app, load, toast, updateSettings } from "./lib/state.svelte.js";
  import { transportName } from "./lib/api.js";

  let devMode = $state(false);
  transportName().then((name) => (devMode = name === "http"));
  load();

  const collapsed = $derived(app.settings?.nav_collapsed ?? false);

  // A page, once opened, stays open in the background: switching back finds it as it was left, with its
  // filters, selection, open editor and scroll position, and without reading anything again.
  const PAGES = { "/modules": Modules, "/concepts": Concepts, "/questions": Questions, "/exams": Exams, "/settings": Settings };
  const opened = $state({ [route.path]: true });
  const scrolls = {};
  let main;
  let shown = route.path;
  $effect.pre(() => {
    const path = route.path;
    untrack(() => {
      opened[path] = true;
      if (!main || path === shown) return;
      scrolls[shown] = main.scrollTop;
      shown = path;
      tick().then(() => (main.scrollTop = scrolls[path] ?? 0));
    });
  });

  function toggleNav() {
    updateSettings({ nav_collapsed: !collapsed });
  }

  function onkeydown(event) {
    if (event.ctrlKey && event.key.toLowerCase() === "b") {
      event.preventDefault();
      toggleNav();
    }
  }
</script>

<svelte:window {onkeydown} />

<div class="app" class:collapsed>
  <Nav ontoggle={toggleNav} />
  <main class="main" bind:this={main}>
    {#if devMode}<div class="dev-banner">{t("dev.http")}</div>{/if}
    <Topbar />
    {#if app.error}
      <div class="error-banner">{t("error.core")}: {app.error}</div>
    {/if}
    {#if !app.loaded}
      <div class="page"><p class="muted">{t("loading")}</p></div>
    {:else}
      {#each Object.entries(PAGES) as [path, Page] (path)}
        {#if opened[path]}<div class="route" style:display={route.path === path ? null : "none"}><Page /></div>{/if}
      {/each}
    {/if}
  </main>
</div>
<ConfirmDialog />
<div class="toast" class:show={toast.visible} role="status" aria-live="polite">{toast.text}</div>
