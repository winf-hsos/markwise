<script>
  import Icon from "./Icon.svelte";

  // A "more" button with a small list of actions: [{ label, icon, onclick }].
  let { items, label } = $props();

  let open = $state(false);
  let root;

  function closeOnOutside(event) {
    if (open && root && !root.contains(event.target)) open = false;
  }

  function choose(item) {
    open = false;
    item.onclick();
  }
</script>

<svelte:window onclick={closeOnOutside} onkeydown={(e) => e.key === "Escape" && (open = false)} />

<div class="menu" class:open bind:this={root}>
  <button class="icon-btn" aria-label={label} aria-haspopup="true" aria-expanded={open} onclick={() => (open = !open)}>
    <Icon name="more" />
  </button>
  {#if open}
    <div class="menu-list" role="menu">
      {#each items as item}
        <button role="menuitem" onclick={() => choose(item)}>
          {#if item.icon}<Icon name={item.icon} />{/if}{item.label}
        </button>
      {/each}
    </div>
  {/if}
</div>
