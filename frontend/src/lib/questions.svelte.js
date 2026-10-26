import { call } from "./api.js";

// The questions of each module, kept in memory for every page that shows them. Reading the pools takes a
// moment, so it happens once per module; after a change the list is read again in the background while the
// pages keep showing what they have. `version` counts the readings, for pages that derive their own data.

const cache = $state({}); // module path -> { pools, questions, loaded, loading, error, version }
const EMPTY = Object.freeze({ pools: [], questions: [], loaded: false, loading: false, error: null, version: 0 });
const running = new Map(); // module path -> the reading under way
const again = new Set(); // modules changed while being read: read once more afterwards

// What is known of a module's questions; safe to use in templates and derived values.
export function questionsOf(module) {
  return cache[module] ?? EMPTY;
}

function entry(module) {
  cache[module] ??= { pools: [], questions: [], loaded: false, loading: false, error: null, version: 0 };
  return cache[module];
}

// The questions of a module, read only if they are not in memory yet.
export function ensureQuestions(module) {
  if (!module) return Promise.resolve();
  if (running.has(module)) return running.get(module);
  return entry(module).loaded ? Promise.resolve() : refreshQuestions(module);
}

// Read the module's questions again: after a change, or when the person asks for it.
export function refreshQuestions(module) {
  if (!module) return Promise.resolve();
  if (running.has(module)) {
    again.add(module); // the reading under way may have started before the change
    return running.get(module);
  }
  const state = entry(module);
  state.loading = true;
  const reading = call("list_questions", module)
    .then((result) => {
      state.pools = result.pools;
      state.questions = result.questions;
      state.loaded = true;
      state.error = null;
      state.version += 1;
    })
    .catch((err) => {
      state.error = err;
    })
    .finally(() => {
      state.loading = false;
      running.delete(module);
      if (again.delete(module)) refreshQuestions(module);
    });
  running.set(module, reading);
  return reading;
}

// Something changed the questions, such as a renamed concept: read them again where they are in memory already.
export function questionsChanged(module) {
  return cache[module]?.loaded || running.has(module) ? refreshQuestions(module) : Promise.resolve();
}

// Pools were added, removed or changed their languages, or the interface speaks another language: every module
// in memory is read again.
export function refreshAllQuestions() {
  return Promise.all(Object.keys(cache).filter((m) => cache[m].loaded).map((m) => refreshQuestions(m)));
}

// Take questions out of the list at once, before the pools are read again.
export function dropQuestions(module, pool, ids) {
  const state = cache[module];
  if (state) state.questions = state.questions.filter((q) => q.pool !== pool || !ids.includes(q.id));
}
