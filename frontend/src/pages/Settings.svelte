<script>
  import { t } from "../lib/i18n.svelte.js";
  import { app, updateSettings } from "../lib/state.svelte.js";
  import { transportName } from "../lib/api.js";

  let examiner = $state(app.settings?.examiner ?? "");
  let saved = $state(false);
  let transport = $state("");
  transportName().then((name) => (transport = name));

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
    <section class="panel">
      <div class="panel-head"><h2>{t("settings.general")}</h2></div>
      <div class="panel-body">
        <div class="switch-row">
          <div class="text"><b>{t("settings.language")}</b></div>
          <div class="seg" role="group" aria-label={t("settings.language")}>
            <button class:on={app.settings?.language === "de"} onclick={() => setLanguage("de")}>Deutsch</button>
            <button class:on={app.settings?.language === "en"} onclick={() => setLanguage("en")}>English</button>
          </div>
        </div>
        <form class="switch-row" onsubmit={saveExaminer}>
          <div class="text">
            <b>{t("settings.examiner")}</b>
            <span class="muted small">{t("settings.examinerHint")}</span>
          </div>
          <input class="input" bind:value={examiner} placeholder="Prof. Dr. …" />
          <button class="btn" type="submit">{saved ? t("settings.saved") : t("settings.save")}</button>
        </form>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head"><h2>{t("settings.about")}</h2></div>
      <div class="panel-body">
        <table class="table">
          <tbody>
            <tr><td class="muted">{t("settings.version")}</td><td class="mono">{app.info?.version}</td></tr>
            <tr><td class="muted">{t("settings.file")}</td><td class="mono">{app.info?.settings_file}</td></tr>
            <tr><td class="muted">{t("settings.bridge")}</td><td>{transport ? t("settings.bridge." + transport) : ""}</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</div>
