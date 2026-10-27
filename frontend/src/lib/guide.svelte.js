import { helpFor } from "./help.js";

// The help dialog and the tour, shared by the top bar, the dialog and the overlay. `steps` holds the tour steps
// whose elements are on the page when the tour starts; `index` is the step shown.
export const guide = $state({ helpOpen: false, steps: null, index: 0 });

const OFFERED = "markwise-tour-offered";

const isShown = (element) => Boolean(element) && element.getClientRects().length > 0;
export const targetOf = (step) => document.querySelector(`[data-tour="${step.target}"]`);

// The steps of a page that can be shown right now: a step whose element is missing or hidden is left out.
export function stepsHere(path, lang) {
  return (helpFor(path, lang)?.tour ?? []).filter((step) => isShown(targetOf(step)));
}

export function startTour(path, lang) {
  const steps = stepsHere(path, lang);
  guide.helpOpen = false;
  if (!steps.length) return false;
  guide.index = 0;
  guide.steps = steps;
  return true;
}

export function endTour() {
  guide.steps = null;
  guide.index = 0;
}

// The tour is offered once per page and computer; whether it was taken or declined, it is not offered again.
function offered() {
  try {
    return JSON.parse(localStorage.getItem(OFFERED) ?? "[]");
  } catch {
    return [];
  }
}

export const wasOffered = (path) => offered().includes(path);

export function markOffered(path) {
  try {
    localStorage.setItem(OFFERED, JSON.stringify([...new Set([...offered(), path])]));
  } catch {
    /* no storage: the offer may come again */
  }
}
