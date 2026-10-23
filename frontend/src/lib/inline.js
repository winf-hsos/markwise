// The inline Markdown that question texts use: **bold**, *italic* and `code`, as safe HTML.

const escape = (text) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export function inline(text) {
  if (!text) return "";
  // Code first, so that stars inside code stay stars.
  const parts = escape(String(text)).split(/(`[^`\n]+`)/g);
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
