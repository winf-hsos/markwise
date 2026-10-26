// The inline Markdown that question texts use: **bold**, *italic* and `code`, as safe HTML.

const escape = (text) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// As Markdown reads a text: a single line break is a space, a blank line starts a paragraph. List items, fenced
// code, quotes, headings and hard breaks (two spaces or a backslash at the end of a line) keep their lines.
// The same rules as markwise.text.unwrap in the core.
const LIST_ITEM = /^\s*([-*+]|\d+[.)])\s+/;
const BLOCK_START = ["```", ">", "#", "|"];

export function softBreaks(text) {
  const out = [];
  let joinable = false;
  let fence = false;
  for (const line of String(text).replace(/^\n+|\n+$/g, "").split("\n")) {
    const stripped = line.trim();
    if (stripped.startsWith("```")) {
      fence = !fence;
      out.push(line);
      joinable = false;
    } else if (fence || !stripped) {
      out.push(line);
      joinable = false;
    } else if (BLOCK_START.some((b) => stripped.startsWith(b)) || LIST_ITEM.test(line) || !joinable) {
      out.push(line);
      joinable = !BLOCK_START.some((b) => stripped.startsWith(b));
    } else if (/( {2}|\\)$/.test(out[out.length - 1])) {
      out.push(stripped);
    } else {
      out[out.length - 1] = `${out[out.length - 1].trimEnd()} ${stripped}`;
    }
  }
  return out.join("\n");
}

export function inline(text) {
  if (!text) return "";
  // Code first, so that stars inside code stay stars.
  const parts = escape(softBreaks(text)).split(/(`[^`\n]+`)/g);
  return parts
    .map((part) =>
      part.startsWith("`") && part.endsWith("`") && part.length > 1
        ? `<code>${part.slice(1, -1)}</code>`
        : part
            .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
            .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>"),
    )
    .join("");
}
