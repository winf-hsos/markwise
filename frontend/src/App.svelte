<script>
  import Nav from "./components/Nav.svelte";
  import Topbar from "./components/Topbar.svelte";
  import Modules from "./pages/Modules.svelte";
  import Questions from "./pages/Questions.svelte";
  import Placeholder from "./pages/Placeholder.svelte";
  import Settings from "./pages/Settings.svelte";
  import { t } from "./lib/i18n.svelte.js";
  import { route } from "./lib/router.svelte.js";
  import { app, load, toast, updateSettings } from "./lib/state.svelte.js";
  import { transportName } from "./lib/api.js";

  let devMode = $state(false);
  transportName().then((name) => (devMode = name === "http"));
  load();

  const collapsed = $derived(app.settings?.nav_collapsed ?? false);

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
  <main class="main">
    {#if devMode}<div class="dev-banner">{t("dev.http")}</div>{/if}
    <Topbar />
    {#if app.error}
      <div class="error-banner">{t("error.core")}: {app.error}</div>
    {/if}
    {#if !app.loaded}
      <div class="page"><p class="muted">{t("loading")}</p></div>
    {:else if route.path === "/modules"}
      <Modules />
    {:else if route.path === "/questions"}
      <Questions />
    {:else if route.path === "/exams"}
      <Placeholder title="exams.title" lead="exams.lead" text="exams.empty" icon="exams" />
    {:else if route.path === "/settings"}
      <Settings />
    {/if}
  </main>
</div>
<div class="toast" class:show={toast.visible} role="status" aria-live="polite">{toast.text}</div>
