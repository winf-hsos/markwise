// One confirmation at a time, shown by ConfirmDialog in the app's own look instead of the browser's confirm().

export const confirmation = $state({ open: false, title: "", message: "", action: "", danger: false });

let settle = null;

// Resolves to true when the examiner confirms, false when they cancel or close the dialog.
export function ask({ title, message = "", action, danger = false }) {
  settle?.(false);
  Object.assign(confirmation, { open: true, title, message, action, danger });
  return new Promise((resolve) => (settle = resolve));
}

export function answer(yes) {
  confirmation.open = false;
  settle?.(yes);
  settle = null;
}
