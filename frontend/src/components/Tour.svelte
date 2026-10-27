<script>
  import { untrack } from "svelte";
  import { endTour, guide, targetOf } from "../lib/guide.svelte.js";
  import { t } from "../lib/i18n.svelte.js";

  // The tour: the page darkened, the element of the current step left bright, and next to it a card with what it
  // does. The position follows the element on every frame, so that scrolling and changes of the layout keep it
  // in place. Clicks on the page are held back while the tour runs; Escape ends it, the arrow keys move through it.
  const GAP = 12;
  const CARD_WIDTH = 340;
  const step = $derived(guide.steps?.[guide.index] ?? null);
  const total = $derived(guide.steps?.length ?? 0);
  let spot = $state(null); // { top, left, width, height } of the bright frame
  let place = $state({ top: 0, left: 0 });
  let card = $state(null);
  let frame = 0;

  function measure() {
    const element = step && targetOf(step);
    if (!element) {
      spot = null;
      return;
    }
    const r = element.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    // A frame no larger than the window, for elements taller than it, such as a long list.
    // Whole pixels, so that the four dark panels around it meet without a seam.
    const top = Math.round(Math.max(r.top - 6, 8));
    const bottom = Math.round(Math.min(r.bottom + 6, vh - 8));
    const left = Math.round(Math.max(r.left - 6, 8));
    const right = Math.round(Math.min(r.right + 6, vw - 8));
    spot = { top, left, width: right - left, height: Math.max(bottom - top, 24) };
    const height = card?.offsetHeight ?? 160;
    const x = Math.min(Math.max(spot.left, 16), vw - CARD_WIDTH - 16);
    if (spot.top + spot.height + GAP + height < vh - 8) place = { top: spot.top + spot.height + GAP, left: x };
    else if (spot.top - GAP - height > 8) place = { top: spot.top - GAP - height, left: x };
    else if (spot.left + spot.width + GAP + CARD_WIDTH < vw - 8) place = { top: Math.min(spot.top, vh - height - 16), left: spot.left + spot.width + GAP };
    else place = { top: vh - height - 24, left: vw - CARD_WIDTH - 24 };
  }

  function loop() {
    measure();
    frame = requestAnimationFrame(loop);
  }

  // Each step brings its element into view first.
  $effect(() => {
    if (!step) return;
    targetOf(step)?.scrollIntoView({ block: "nearest", inline: "nearest" });
    untrack(() => {
      card?.querySelector(".tour-next")?.focus();
      measure(); // reads and writes the frame, which must not make this effect run again
    });
    // Measured again once the card has its height, and on every frame after that.
    const settle = setTimeout(measure, 50);
    frame = requestAnimationFrame(loop);
    return () => {
      clearTimeout(settle);
      cancelAnimationFrame(frame);
    };
  });

  function go(by) {
    const next = guide.index + by;
    if (next < 0) return;
    if (next >= total) endTour();
    else guide.index = next;
  }

  function onkeydown(event) {
    if (!step) return;
    if (event.key === "Escape") endTour();
    else if (event.key === "ArrowRight" || event.key === "Enter") go(1);
    else if (event.key === "ArrowLeft") go(-1);
    else return;
    event.preventDefault();
    event.stopPropagation();
  }
</script>

<svelte:window onkeydowncapture={onkeydown} onresize={measure} onscrollcapture={measure} />

{#if step}
  <div class="tour-veil" aria-hidden="true">
    {#if spot}
      <!-- Four panels darken everything around the bright frame. -->
      <i style:top="0" style:left="0" style:right="0" style:height="{spot.top}px"></i>
      <i style:top="{spot.top + spot.height}px" style:left="0" style:right="0" style:bottom="0"></i>
      <i style:top="{spot.top}px" style:left="0" style:width="{spot.left}px" style:height="{spot.height}px"></i>
      <i style:top="{spot.top}px" style:left="{spot.left + spot.width}px" style:right="0" style:height="{spot.height}px"></i>
    {:else}
      <i style:inset="0"></i>
    {/if}
  </div>
  {#if spot}
    <div class="tour-spot" style:top="{spot.top}px" style:left="{spot.left}px" style:width="{spot.width}px" style:height="{spot.height}px"></div>
  {/if}
  <div class="tour-card" bind:this={card} role="dialog" aria-modal="true" aria-label={step.title}
    style:top="{place.top}px" style:left="{place.left}px" style:width="{CARD_WIDTH}px">
    <span class="tour-count">{t("tour.step", { n: guide.index + 1, total })}</span>
    <b>{step.title}</b>
    <p>{step.text}</p>
    <div class="tour-actions">
      <button class="btn ghost btn-small" type="button" onclick={endTour}>{t("tour.end")}</button>
      <span class="spacer"></span>
      <button class="btn btn-small" type="button" disabled={guide.index === 0} onclick={() => go(-1)}>{t("tour.back")}</button>
      <button class="btn primary btn-small tour-next" type="button" onclick={() => go(1)}>{guide.index === total - 1 ? t("tour.done") : t("tour.next")}</button>
    </div>
  </div>
{/if}
