<script>
  import Icon from "./Icon.svelte";

  // A button with a small list of actions: [{ label, icon, onclick, disabled, hint }]. Without `buttonLabel`
  // the button is the "more" icon; with it, a labelled button.
  let { items, label, buttonLabel = "", buttonIcon = "plus", align = "right" } = $props();

  let open = $state(false);
  let root;

  function closeOnOutside(event) {
    if (open && root && !root.contains(event.target)) open = false;
  }

  function choose(item) {
    if (item.disabled) return;
    open = false;
    item.onclick();
  }
</script>

<svelte:window onclick={closeOnOutside} onkeydown={(e) => e.key === "Escape" && (open = false)} />

<div class="menu" class:open bind:this={root}>
  {#if buttonLabel}
    <button type="button" class="btn ghost" aria-haspopup="true" aria-expanded={open} onclick={() => (open = !open)}>
      <Icon name={buttonIcon} />{buttonLabel}
    </button>
  {:else}
    <button type="button" class="icon-btn" aria-label={label} aria-haspopup="true" aria-expanded={open} onclick={() => (open = !open)}>
      <Icon name="more" />
    </button>
  {/if}
  {#if open}
    <div class="menu-list" class:align-left={align === "left"} role="menu">
      {#each items as item}
        <button type="button" role="menuitem" disabled={item.disabled} aria-disabled={item.disabled} onclick={() => choose(item)}>
          {#if item.icon}<Icon name={item.icon} />{/if}
          <span>{item.label}</span>
          {#if item.hint}<span class="menu-hint">{item.hint}</span>{/if}
        </button>
      {/each}
    </div>
  {/if}
</div>
