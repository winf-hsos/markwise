// Hash routes: #/modules, #/concepts, #/questions, #/exams, #/settings. Without a hash, Markwise opens on the
// page the person was on last.

import { lastRoute, rememberRoute } from "./viewstate.svelte.js";

export const ROUTES = ["/modules", "/concepts", "/questions", "/exams", "/settings"];

function current() {
  const path = location.hash.replace(/^#/, "") || lastRoute() || "";
  return ROUTES.includes(path) ? path : "/modules";
}

export const route = $state({ path: current() });

window.addEventListener("hashchange", () => {
  route.path = current();
  rememberRoute(route.path);
});

if (!location.hash && route.path !== "/modules") history.replaceState(null, "", `#${route.path}`);
