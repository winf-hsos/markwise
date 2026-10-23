// One confirmation at a time, shown by ConfirmDialog in the app's own look instead of the browser's confirm().

export const confirmation = $state({ open: false, title: "", message: "", action: "", danger: false, choices: null });

let settle = null;

// Resolves to true when the examiner confirms, false when they cancel or close the dialog. With `choices`
// ([{ value, label, danger }], shown instead of the single action) it resolves to the chosen value.
export function ask({ title, message = "", action = "", danger = false, choices = null }) {
  settle?.(false);
  Object.assign(confirmation, { open: true, title, message, action, danger, choices });
  return new Promise((resolve) => (settle = resolve));
}

export function answer(value) {
  confirmation.open = false;
  settle?.(value);
  settle = null;
}
