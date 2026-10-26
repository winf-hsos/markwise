// Answering times and dates as people read them.

import { ui } from "./i18n.svelte.js";

// 45 → "45 s", 60 → "1 min", 90 → "1 min 30 s".
export function formatTime(seconds) {
  if (seconds == null) return "";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (!m) return `${s} s`;
  return s ? `${m} min ${s} s` : `${m} min`;
}

// A total of answering times: 2730 → "45 min 30 s", 7500 → "2 h 5 min", 0 → "0 min".
export function formatTotal(seconds) {
  if (!seconds) return "0 min";
  if (seconds < 3600) return formatTime(seconds);
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return m ? `${h} h ${m} min` : `${h} h`;
}

// "2026-10-24" → "24.10.2026" or "24 Oct 2026".
export function formatDate(iso) {
  if (!iso) return "";
  const date = new Date(`${iso}T12:00:00`);
  return isNaN(date) ? iso : date.toLocaleDateString(ui.lang === "de" ? "de-DE" : "en-GB", { dateStyle: "medium" });
}
