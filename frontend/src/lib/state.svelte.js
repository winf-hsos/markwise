// What the interface knows about the core: version, settings, opened modules and pools.

import { call } from "./api.js";
import { ui } from "./i18n.svelte.js";
import { refreshAllQuestions } from "./questions.svelte.js";

export const app = $state({
  loaded: false,
  error: null,
  info: null,
  settings: null,
  workspace: { modules: [], pools: [] },
  llm: null, // { enabled, model, has_key }
});

export async function load() {
  try {
    const [info, settings, workspace] = await Promise.all([call("info"), call("get_settings"), call("workspace")]);
    app.info = info;
    app.settings = settings;
    app.workspace = workspace;
    ui.lang = settings.language;
    applyTheme(settings.theme);
    app.error = null;
    loadLlm();
  } catch (err) {
    app.error = err.message;
  }
  app.loaded = true;
}

// Whether help from the language model can be offered: switched on, a key stored, a model chosen.
export async function loadLlm() {
  try {
    app.llm = await call("llm_status");
  } catch {
    app.llm = null;
  }
}

export const llmReady = () => Boolean(app.llm?.enabled && app.llm?.has_key && app.llm?.model);

export async function updateSettings(changes) {
  app.settings = await call("update_settings", changes);
  ui.lang = app.settings.language;
  applyTheme(app.settings.theme);
}

// The colour scheme is a data attribute on the page; the styles define each scheme's accent colours.
export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme || "markwise";
  try {
    localStorage.setItem("markwise-theme", theme || "markwise"); // read by main.js before the first paint
  } catch {
    /* no storage: the scheme appears once the settings are loaded */
  }
}

export async function refreshWorkspace() {
  app.workspace = await call("workspace");
  app.settings = await call("get_settings");
  refreshAllQuestions(); // a pool may have come, gone or changed its languages
}

export async function setCurrentModule(path) {
  app.settings = await call("set_current_module", path);
}

// What one page asks of another when it sends the person there, for example the Concepts page opening the
// question list filtered to a concept. The receiving page takes it and clears it.
export const pending = $state({ questionsFilter: null, newQuestion: null });

// A short message at the bottom of the window that answers what the person just did.
export const toast = $state({ text: "", visible: false });
let toastTimer = null;

export function showToast(text) {
  toast.text = text;
  toast.visible = true;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (toast.visible = false), 2600);
}
