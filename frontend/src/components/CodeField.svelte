<script>
  import { highlight } from "../lib/highlight.js";

  // A textarea for code with highlighting: the highlighted text lies under a transparent textarea of the
  // same size and font, so typing, selecting and pasting stay those of a plain text field.
  let { value = $bindable(""), language = "", label = "" } = $props();

  // A trailing line break needs a character after it, or the layer below is one line shorter.
  const html = $derived(highlight(value, language) + (value.endsWith("\n") ? " " : ""));
</script>

<div class="code-field">
  <pre class="code-layer hljs" aria-hidden="true"><code>{@html html}</code></pre>
  <textarea class="code-input" bind:value spellcheck="false" aria-label={label} rows="3"
    onkeydown={(e) => {
      // Tab inserts four spaces instead of leaving the field, as in a code editor.
      if (e.key !== "Tab" || e.shiftKey) return;
      e.preventDefault();
      const el = e.currentTarget;
      const { selectionStart: start, selectionEnd: end } = el;
      value = value.slice(0, start) + "    " + value.slice(end);
      requestAnimationFrame(() => el.setSelectionRange(start + 4, start + 4));
    }}></textarea>
</div>
