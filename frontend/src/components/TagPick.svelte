<script>
  import { tick } from "svelte";
  import Icon from "./Icon.svelte";

  // A setting of a question as a label that opens a small choice on a click, like the answering time:
  // `options` ({ value, label }) are chips, the one equal to `value` marked, and `onchoose(value)` receives the
  // chip clicked. `actions` ({ label, icon, onclick, disabled, title }) are buttons below them, for steps such as a
  // release. `heading` names the choice, `note` and `hint` explain it, `tone` colours the label ("ok", "warn"),
  // and `faint` shows it lighter, for a setting a variant takes from its parent.
  let { label, heading = "", hint = "", note = "", tone = "", faint = false, value = undefined, options = [], actions = [],
    onchoose } = $props();

  let open = $state(false);
  let root;
  let pop = $state(null);

  async function toggle() {
    open = !open;
    if (open) {
      await tick();
      pop?.querySelector("button:not([disabled])")?.focus();
    }
  }

  function choose(option) {
    open = false;
    if (option.value !== value) onchoose?.(option.value);
  }

  function act(action) {
    open = false;
    action.onclick?.();
  }

  function closeOnOutside(event) {
    if (open && root && !root.contains(event.target)) open = false;
  }
</script>

<svelte:window onclick={closeOnOutside} onkeydown={(e) => open && e.key === "Escape" && (open = false)} />

<span class="tag-pick" bind:this={root}>
  <button type="button" class="tag tag-button {tone}" class:faint aria-haspopup="true" aria-expanded={open} title={hint || null}
    onclick={toggle}>{label}</button>
  {#if open}
    <div class="tag-pop" role="dialog" aria-label={heading} bind:this={pop}>
      {#if heading}<b>{heading}</b>{/if}
      {#if options.length}
        <div class="tag-pop-chips">
          {#each options as option (option.value)}
            <button type="button" class="chip" class:on={option.value === value} class:faint={option.faint}
              disabled={option.disabled} title={option.title || null} onclick={() => choose(option)}>{option.label}</button>
          {/each}
        </div>
      {/if}
      {#if actions.length}
        <div class="tag-pop-actions">
          {#each actions as action}
            <button type="button" class="btn btn-small" disabled={action.disabled} title={action.title || null}
              onclick={() => act(action)}>{#if action.icon}<Icon name={action.icon} />{/if}{action.label}</button>
          {/each}
        </div>
      {/if}
      {#if note}<span class="hint">{note}</span>{/if}
    </div>
  {/if}
</span>
