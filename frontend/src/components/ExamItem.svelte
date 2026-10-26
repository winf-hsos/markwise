<script>
  import { highlight } from "../lib/highlight.js";
  import { inline } from "../lib/inline.js";

  // One question as the printed booklet shows it: number and points, what kind of answer is expected, the text,
  // code and figures, the options with empty boxes, or the lines and the point strip of a free-text question.
  // `item` comes from exam_items, `words` are the booklet's words in the exam's language.
  let { item, number, points, words } = $props();

  const unit = $derived(points === 1 ? words.point : words.points);
  const strip = $derived.by(() => {
    const top = Math.max(0, Math.floor(points));
    const steps = Array.from({ length: Math.min(top, 20) + 1 }, (_, i) => String(i));
    return item.half_points ? [...steps, "½"] : steps;
  });
</script>

<div class="booklet-item">
  <div class="booklet-head">
    <b>{words.question} {number}</b>
    <span>{points.toLocaleString(undefined, { maximumFractionDigits: 1 })} {unit}</span>
  </div>
  {#if item.type === "single" || item.type === "multiple"}<div class="booklet-hint">{words[item.type]}</div>{/if}
  <div class="booklet-stem">{@html inline(item.stem)}</div>
  {#if item.code}<pre class="booklet-code hljs"><code>{@html highlight(item.code, item.code_language)}</code></pre>{/if}
  {#if item.figures.length}
    <div class="booklet-figures" style="--columns: {item.figures.length > 1 ? item.image_columns || 1 : 1}">
      {#each item.figures as f (f.name)}<img src={f.data} alt={f.name} />{/each}
    </div>
  {/if}
  {#if item.type === "free_text"}
    <div class="booklet-lines" style="--lines: {item.lines}"></div>
    <div class="booklet-strip">
      <span>{words.examiners_only}</span>
      {#each strip as s}<span class="cell"><small>{s}</small><i></i></span>{/each}
    </div>
  {:else}
    <ol class="booklet-options">
      {#each item.options as o (o.id)}
        <li><i class="booklet-box"></i><b>{o.id}</b><span>{@html inline(o.text)}</span></li>
      {/each}
    </ol>
  {/if}
</div>
