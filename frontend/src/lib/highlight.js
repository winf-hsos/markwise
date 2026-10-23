// Syntax highlighting for the code blocks of questions, bundled so that nothing loads from the internet.

import hljs from "highlight.js/lib/core";
import bash from "highlight.js/lib/languages/bash";
import c from "highlight.js/lib/languages/c";
import cpp from "highlight.js/lib/languages/cpp";
import csharp from "highlight.js/lib/languages/csharp";
import java from "highlight.js/lib/languages/java";
import javascript from "highlight.js/lib/languages/javascript";
import json from "highlight.js/lib/languages/json";
import python from "highlight.js/lib/languages/python";
import r from "highlight.js/lib/languages/r";
import sql from "highlight.js/lib/languages/sql";

// [id as stored in code_language, name shown]
export const CODE_LANGUAGES = [
  ["python", "Python"], ["javascript", "JavaScript"], ["java", "Java"], ["c", "C"], ["cpp", "C++"],
  ["csharp", "C#"], ["sql", "SQL"], ["r", "R"], ["bash", "Shell"], ["json", "JSON"],
];

const modules = { python, javascript, java, c, cpp, csharp, sql, r, bash, json };
for (const [id] of CODE_LANGUAGES) hljs.registerLanguage(id, modules[id]);
const ids = CODE_LANGUAGES.map(([id]) => id);

const escape = (text) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// Highlighted HTML for the code; hljs escapes the code itself, so the result is safe to insert.
export function highlight(code, language = "") {
  if (!code) return "";
  try {
    return language && hljs.getLanguage(language)
      ? hljs.highlight(code, { language, ignoreIllegals: true }).value
      : hljs.highlightAuto(code, ids).value;
  } catch {
    return escape(code);
  }
}
