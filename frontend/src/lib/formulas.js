// Formulas in question texts: LaTeX math between dollar signs, `$…$` in the running text and `$$…$$` set apart.
// The same rules as markwise.formulas in the core, after Pandoc: the opening dollar is followed by something other
// than a space, the closing one preceded by something other than a space and not followed by a digit; `\$` is a
// dollar sign as such, and code between backticks never holds a formula.

import katex from "katex";

export function split(text) {
  const out = [];
  let buffer = "";
  const flush = () => {
    if (buffer) out.push(["text", buffer]);
    buffer = "";
  };
  let i = 0;
  while (i < text.length) {
    const c = text[i];
    if (c === "\\" && text[i + 1] === "$") {
      buffer += "$";
      i += 2;
      continue;
    }
    if (c === "`") {
      const end = text.indexOf("`", i + 1);
      if (end > i + 1) {
        flush();
        out.push(["code", text.slice(i, end + 1)]);
        i = end + 1;
        continue;
      }
    }
    if (text.startsWith("$$", i)) {
      const end = text.indexOf("$$", i + 2);
      if (end > i + 2 && text.slice(i + 2, end).trim()) {
        flush();
        out.push(["display", text.slice(i + 2, end).trim()]);
        i = end + 2;
        continue;
      }
    }
    if (c === "$" && i + 1 < text.length && !/\s/.test(text[i + 1]) && text[i + 1] !== "$") {
      const end = closing(text, i + 1);
      if (end != null) {
        flush();
        out.push(["inline", text.slice(i + 1, end)]);
        i = end + 1;
        continue;
      }
    }
    buffer += c;
    i += 1;
  }
  flush();
  return out;
}

function closing(text, start) {
  let j = start;
  while (j < text.length) {
    const c = text[j];
    if (c === "\n" && text[j + 1] === "\n") return null;
    if (c === "\\") {
      j += 2;
      continue;
    }
    if (c === "$") return !/\s/.test(text[j - 1]) && !/\d/.test(text[j + 1] ?? "") ? j : null;
    j += 1;
  }
  return null;
}

// A formula as HTML; one that KaTeX cannot read shows its source in red instead of breaking the text.
export function renderFormula(latex, display = false) {
  return katex.renderToString(latex, { displayMode: display, throwOnError: false, strict: "ignore", output: "html" });
}

// What KaTeX cannot read in the formulas of a text, one message per formula.
export function formulaErrors(text) {
  const errors = [];
  for (const [kind, latex] of split(text ?? "")) {
    if (kind !== "inline" && kind !== "display") continue;
    try {
      katex.renderToString(latex, { displayMode: kind === "display", throwOnError: true, strict: "ignore" });
    } catch (err) {
      errors.push(`$${latex}$: ${String(err.message ?? err).replace(/^KaTeX parse error: /, "")}`);
    }
  }
  return errors;
}

export const hasFormula = (text) => split(text ?? "").some(([kind]) => kind === "inline" || kind === "display");
