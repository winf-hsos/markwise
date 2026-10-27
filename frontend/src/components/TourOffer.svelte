<script>
  import { untrack } from "svelte";
  import Icon from "./Icon.svelte";
  import { guide, markOffered, startTour, stepsHere, wasOffered } from "../lib/guide.svelte.js";
  import { helpFor } from "../lib/help.js";
  import { t, ui } from "../lib/i18n.svelte.js";
  import { route } from "../lib/router.svelte.js";
  import { app } from "../lib/state.svelte.js";

  // The first time a page is opened on this computer, a small card offers its tour. A page with nothing to show
  // yet (no module, say) offers it on a later visit instead.
  let offering = $state("");
  let timer = null;

  $effect(() => {
    const path = route.path;
    if (!app.loaded) return;
    untrack(() => {
      offering = "";
      clearTimeout(timer);
      if (!helpFor(path, ui.lang) || wasOffered(path)) return;
      // A moment for the page to show what it loads, so that the tour finds its elements.
      timer = setTimeout(() => {
        if (route.path === path && !guide.steps && !guide.helpOpen && stepsHere(path, ui.lang).length) offering = path;
      }, 1200);
    });
    return () => clearTimeout(timer);
  });

  function answer(take) {
    markOffered(offering);
    const path = offering;
    offering = "";
    if (take) startTour(path, ui.lang);
  }
</script>

{#if offering && offering === route.path && !guide.steps}
  <div class="tour-offer" role="dialog" aria-label={t("tour.offerTitle")}>
    <span class="tour-offer-icon"><Icon name="help" /></span>
    <div>
      <b>{t("tour.offerTitle")}</b>
      <p>{t("tour.offer", { page: helpFor(offering, ui.lang).title })}</p>
      <div class="tour-actions">
        <button class="btn ghost btn-small" type="button" onclick={() => answer(false)}>{t("tour.offerNo")}</button>
        <button class="btn primary btn-small" type="button" onclick={() => answer(true)}>{t("tour.offerYes")}</button>
      </div>
    </div>
  </div>
{/if}
