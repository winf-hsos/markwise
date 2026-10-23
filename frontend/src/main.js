import "@fontsource/source-serif-4/400.css";
import "@fontsource/source-serif-4/600.css";
import "./app.css";
import { mount } from "svelte";
import App from "./App.svelte";

// The colour scheme of the last session, before the first paint, so that the page does not flash in another one.
try {
  document.documentElement.dataset.theme = localStorage.getItem("markwise-theme") || "markwise";
} catch {
  /* no storage: the scheme follows once the settings are loaded */
}

mount(App, { target: document.getElementById("app") });
