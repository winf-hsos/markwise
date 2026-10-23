<script>
  import Dialog from "./Dialog.svelte";
  import { answer, confirmation } from "../lib/confirm.svelte.js";
  import { t } from "../lib/i18n.svelte.js";

  // Escape or the close button count as cancelling.
  $effect(() => {
    if (!confirmation.open) answer(false);
  });
</script>

<Dialog bind:open={confirmation.open} title={confirmation.title} lead={confirmation.message}>
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => answer(false)}>{t("dialog.cancel")}</button>
    <button class="btn {confirmation.danger ? 'decide' : 'primary'}" type="button" onclick={() => answer(true)}>{confirmation.action}</button>
  {/snippet}
</Dialog>
