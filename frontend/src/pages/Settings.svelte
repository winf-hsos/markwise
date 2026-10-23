<script>
  import { t } from "../lib/i18n.svelte.js";
  import { app, updateSettings } from "../lib/state.svelte.js";
  import { transportName } from "../lib/api.js";

  let examiner = $state(app.settings?.examiner ?? "");
  let saved = $state(false);
  let transport = $state("");
  transportName().then((name) => (transport = name));

  const THEMES = [["markwise", "#1f8452"], ["hsos", "#009ee3"]];

  const changed = $derived(examiner.trim() !== (app.settings?.examiner ?? ""));

  async function setLanguage(lang) {
    await updateSettings({ language: lang });
  }

  async function saveExaminer(event) {
    event.preventDefault();
    await updateSettings({ examiner: examiner.trim() });
    saved = true;
    setTimeout(() => (saved = false), 1600);
  }
</script>

<div class="page">
  <div class="page-head">
    <div>
      <h1>{t("settings.title")}</h1>
      <p>{t("settings.lead")}</p>
    </div>
  </div>

  <div class="settings">
    <section>
      <h2 class="section-title">{t("settings.general")}</h2>
      <div class="rows">
        <div class="row-item">
          <div class="text"><b>{t("settings.language")}</b></div>
          <div class="seg" role="group" aria-label={t("settings.language")}>
            <button class:on={app.settings?.language === "de"} onclick={() => setLanguage("de")}>Deutsch</button>
            <button class:on={app.settings?.language === "en"} onclick={() => setLanguage("en")}>English</button>
          </div>
        </div>
        <div class="row-item">
          <div class="text"><b>{t("settings.theme")}</b><span class="hint">{t("settings.themeHint")}</span></div>
          <div class="theme-choice" role="radiogroup" aria-label={t("settings.theme")}>
            {#each THEMES as [id, swatch]}
              <button type="button" role="radio" aria-checked={(app.settings?.theme ?? "markwise") === id}
                class="theme-option" class:on={(app.settings?.theme ?? "markwise") === id} onclick={() => updateSettings({ theme: id })}>
                <span class="swatch" style="background: {swatch}"></span>{t(`settings.theme.${id}`)}
              </button>
            {/each}
          </div>
        </div>
        <form class="row-item" onsubmit={saveExaminer}>
          <div class="text">
            <b>{t("settings.examiner")}</b>
            <span class="hint">{t("settings.examinerHint")}</span>
          </div>
          <div class="control">
            <input class="input" bind:value={examiner} placeholder="Prof. Dr. …" aria-label={t("settings.examiner")} />
            <button class="btn" class:primary={changed} type="submit" disabled={!changed && !saved}>
              {saved ? t("settings.saved") : t("settings.save")}
            </button>
          </div>
        </form>
      </div>
    </section>

    <section>
      <h2 class="section-title">{t("settings.about")}</h2>
      <div class="rows">
        <dl class="about">
          <dt>{t("settings.version")}</dt><dd>{app.info?.version}</dd>
          <dt>{t("settings.file")}</dt><dd class="small">{app.info?.settings_file}</dd>
          <dt>{t("settings.bridge")}</dt><dd>{transport ? t("settings.bridge." + transport) : ""}</dd>
        </dl>
      </div>
    </section>
  </div>
</div>
