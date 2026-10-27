<script>
  import { t } from "../lib/i18n.svelte.js";

  // A filter with several choices: a button that names what is chosen, and a list of check boxes below it.
  // Nothing chosen means everything is shown; the button then names the filter and says "all" on pointing at it.
  let { selected = $bindable([]), options = [], allLabel, label } = $props();

  let open = $state(false);
  let root;

  const chosen = $derived(options.filter((o) => selected.includes(o.value)));
  const summary = $derived(
    chosen.length === 0 ? label : chosen.length === 1 ? chosen[0].label : `${chosen[0].label} +${chosen.length - 1}`,
  );

  function toggle(value) {
    selected = selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value];
  }

  function onwindowclick(event) {
    if (open && root && !root.contains(event.target)) open = false;
  }

  function onkeydown(event) {
    if (event.key === "Escape" && open) {
      open = false;
      event.stopPropagation();
    }
  }
</script>

<svelte:window onclick={onwindowclick} />

<div class="multi" bind:this={root} {onkeydown}>
  <button type="button" class="select multi-button" class:active={chosen.length} aria-haspopup="true" aria-expanded={open}
    aria-label={label} title={chosen.length ? `${label}: ${chosen.map((o) => o.label).join(", ")}` : allLabel} onclick={() => (open = !open)}>
    <span>{summary}</span>
  </button>
  {#if open}
    <div class="multi-panel" role="group" aria-label={label}>
      <button type="button" class="multi-all" disabled={!chosen.length} onclick={() => (selected = [])}>{t("filter.all")}</button>
      {#each options as option (option.value)}
        <label class="multi-option">
          <input type="checkbox" checked={selected.includes(option.value)} onchange={() => toggle(option.value)} />
          <span>{option.label}</span>
          {#if option.count != null}<span class="multi-count">{option.count}</span>{/if}
        </label>
      {/each}
    </div>
  {/if}
</div>
