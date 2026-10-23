<script>
  import { t } from "../lib/i18n.svelte.js";

  // A modal dialog on the native <dialog> element: Escape and the close button both close it.
  let { open = $bindable(false), title, lead = "", wide = false, children, footer } = $props();

  let element;

  $effect(() => {
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  });
</script>

<dialog bind:this={element} class="dialog" class:wide onclose={() => (open = false)}>
  <header class="dialog-head">
    <div>
      <h2>{title}</h2>
      {#if lead}<p>{lead}</p>{/if}
    </div>
    <button class="icon-btn" type="button" aria-label={t("dialog.close")} onclick={() => (open = false)}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" fill="none" stroke-width="1.8" stroke-linecap="round" /></svg>
    </button>
  </header>
  {#if children}<div class="dialog-body">{@render children()}</div>{/if}
  {#if footer}<footer class="dialog-foot">{@render footer()}</footer>{/if}
</dialog>
