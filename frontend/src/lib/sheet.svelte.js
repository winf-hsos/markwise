import { call } from "./api.js";

// What the question sheet keeps across pages and visits: whether the details below a question are open (on this
// computer, the same on the Questions page and in the exam), and the name Markwise notes on releases.
const DETAILS = "markwise-question-details";

function readDetails() {
  try {
    return localStorage.getItem(DETAILS) === "open";
  } catch {
    return false;
  }
}

export const sheet = $state({ details: readDetails(), me: "" });

export function setDetails(open) {
  sheet.details = open;
  try {
    localStorage.setItem(DETAILS, open ? "open" : "closed");
  } catch {
    /* no storage: the choice is simply not kept */
  }
}

call("whoami").then((name) => (sheet.me = name)).catch(() => {});
