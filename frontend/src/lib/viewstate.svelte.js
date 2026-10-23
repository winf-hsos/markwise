// What each page remembers when the person leaves it: filters, selection, scroll position, the last page.
// Kept per module, written to the window's storage so that it survives a restart. Unsaved edits are kept
// only in memory, so that nothing half-typed reappears after Markwise was closed.

const KEY = "markwise-view";

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) ?? {};
  } catch {
    return {};
  }
}

const stored = read();
let timer = null;

function persist() {
  clearTimeout(timer);
  timer = setTimeout(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(stored));
    } catch {
      /* no storage: the pages simply start fresh next time */
    }
  }, 250);
}

// The remembered state of a page for a module, as a plain object; change it through remember().
export function recall(page, module) {
  return stored[page]?.[module] ?? {};
}

export function remember(page, module, values) {
  if (!module) return;
  stored[page] ??= {};
  stored[page][module] = { ...(stored[page][module] ?? {}), ...values };
  persist();
}

export function lastRoute() {
  return stored.route ?? null;
}

export function rememberRoute(path) {
  stored.route = path;
  persist();
}

// Unsaved edits by question (pool + id), for the time the window is open.
export const drafts = new Map();
