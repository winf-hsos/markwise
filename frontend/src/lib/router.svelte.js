// Hash routes: #/modules, #/concepts, #/questions, #/exams, #/settings.

export const ROUTES = ["/modules", "/concepts", "/questions", "/exams", "/settings"];

function current() {
  const path = location.hash.replace(/^#/, "");
  return ROUTES.includes(path) ? path : "/modules";
}

export const route = $state({ path: current() });

window.addEventListener("hashchange", () => {
  route.path = current();
});
