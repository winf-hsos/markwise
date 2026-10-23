// What the interface knows about the core: version, settings, opened modules and pools.

import { call } from "./api.js";
import { ui } from "./i18n.svelte.js";

export const app = $state({
  loaded: false,
  error: null,
  info: null,
  settings: null,
  workspace: { modules: [], pools: [] },
});

export async function load() {
  try {
    const [info, settings, workspace] = await Promise.all([call("info"), call("get_settings"), call("workspace")]);
    app.info = info;
    app.settings = settings;
    app.workspace = workspace;
    ui.lang = settings.language;
    app.error = null;
  } catch (err) {
    app.error = err.message;
  }
  app.loaded = true;
}

export async function updateSettings(changes) {
  app.settings = await call("update_settings", changes);
  ui.lang = app.settings.language;
}
