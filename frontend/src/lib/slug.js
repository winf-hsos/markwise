// The identifier Markwise makes from a concept name; the core does the same (pool.slugify) and has the last word.

const UMLAUTS = { ä: "ae", ö: "oe", ü: "ue", ß: "ss", Ä: "ae", Ö: "oe", Ü: "ue" };

export function slugify(name) {
  const text = name.replace(/[äöüßÄÖÜ]/g, (c) => UMLAUTS[c]).toLowerCase();
  return text.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "concept";
}
