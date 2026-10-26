<script>
  import Icon from "./Icon.svelte";
  import { t } from "../lib/i18n.svelte.js";
  import { route } from "../lib/router.svelte.js";

  let { ontoggle } = $props();

  const links = [
    ["/modules", "nav.modules", "modules"],
    ["/concepts", "nav.concepts", "concepts"],
    ["/questions", "nav.questions", "questions"],
    ["/exams", "nav.exams", "exams"],
  ];
</script>

<nav class="nav" aria-label={t("nav.main")}>
  <div class="brand">
    <svg class="brand-mark" viewBox="0 0 64 64" aria-hidden="true">
      <rect x="3" y="3" width="58" height="58" rx="14" fill="#1f8452" />
      <path d="M18.5 33.5 27.5 42.5 45.5 22" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" />
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
