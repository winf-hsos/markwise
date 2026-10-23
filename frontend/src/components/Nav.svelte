<script>
  import Icon from "./Icon.svelte";
  import { t } from "../lib/i18n.svelte.js";
  import { route } from "../lib/router.svelte.js";

  let { ontoggle } = $props();

  const links = [
    ["/modules", "nav.modules", "modules"],
    ["/questions", "nav.questions", "questions"],
    ["/exams", "nav.exams", "exams"],
  ];
</script>

<nav class="nav" aria-label={t("nav.main")}>
  <div class="brand">
    <svg class="brand-mark" viewBox="0 0 64 64" aria-hidden="true">
      <circle cx="32" cy="32" r="30" fill="#dff3e7" />
      <path d="M19 33.5 28 42 46 22" fill="none" stroke="#24895a" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
    <span class="brand-name">Markwise</span>
  </div>
  {#each links as [path, label, icon]}
    <a href={"#" + path} title={t(label)} class:active={route.path === path}><Icon name={icon} /><span class="label">{t(label)}</span></a>
  {/each}
  <div class="spacer"></div>
  <a href="#/settings" title={t("nav.settings")} class:active={route.path === "/settings"}><Icon name="settings" /><span class="label">{t("nav.settings")}</span></a>
  <button class="nav-toggle" onclick={ontoggle} title={t("nav.toggle")} aria-label={t("nav.toggle")}>
    <Icon name="panel" /><span class="label">{t("nav.collapse")}</span>
  </button>
</nav>
