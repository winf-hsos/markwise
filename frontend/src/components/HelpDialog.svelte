<script>
  import Dialog from "./Dialog.svelte";
  import Icon from "./Icon.svelte";
  import { helpFor } from "../lib/help.js";
  import { guide, startTour, stepsHere } from "../lib/guide.svelte.js";
  import { t, ui } from "../lib/i18n.svelte.js";
  import { route } from "../lib/router.svelte.js";
  import { showToast } from "../lib/state.svelte.js";

  // The help for the page that is open, behind the "?" in the top bar, with the way into the tour.
  const help = $derived(helpFor(route.path, ui.lang));
  // Counted when the dialog opens, so that the button says whether there is something to show.
  const available = $derived(guide.helpOpen ? stepsHere(route.path, ui.lang).length : 0);

  function tour() {
    if (!startTour(route.path, ui.lang)) showToast(t("tour.nothing"));
  }
</script>

{#if help}
  <Dialog bind:open={guide.helpOpen} title={help.title} lead={help.intro} wide>
    <ul class="help-points">
      {#each help.points as point}<li>{point}</li>{/each}
    </ul>
    {#snippet footer()}
      <span class="hint help-hint">{available ? t("help.tourHint", { n: available }) : t("tour.nothing")}</span>
      <button class="btn ghost" type="button" onclick={() => (guide.helpOpen = false)}>{t("dialog.close")}</button>
      <button class="btn primary" type="button" disabled={!available} onclick={tour}><Icon name="play" />{t("help.tour")}</button>
    {/snippet}
  </Dialog>
{/if}
