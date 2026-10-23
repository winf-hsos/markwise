<script>
  import { t } from "../lib/i18n.svelte.js";
  import { formatTime } from "../lib/time.js";

  // How long answering takes: the usual steps as buttons, any other time in minutes and seconds.
  let { value = $bindable(null) } = $props();

  const PRESETS = [15, 30, 45, 60, 120, 300];
  let custom = $state(value != null && !PRESETS.includes(value));
  let minutes = $state(value != null ? Math.floor(value / 60) : 1);
  let seconds = $state(value != null ? value % 60 : 0);

  function choose(preset) {
    custom = false;
    value = preset;
  }

  function openCustom() {
    custom = true;
    minutes = value != null ? Math.floor(value / 60) : 1;
    seconds = value != null ? value % 60 : 0;
  }

  function setCustom() {
    const total = Math.max(0, Math.round(Number(minutes) || 0)) * 60 + Math.max(0, Math.round(Number(seconds) || 0));
    value = total > 0 ? total : null;
  }
</script>

<div class="time-choice" role="group" aria-label={t("edit.time")}>
  {#each PRESETS as preset}
    <button type="button" class="chip" class:on={!custom && value === preset} aria-pressed={!custom && value === preset} onclick={() => choose(preset)}>
      {formatTime(preset)}
    </button>
  {/each}
  <button type="button" class="chip" class:on={custom} aria-pressed={custom} onclick={openCustom}>{t("edit.timeOther")}</button>
  {#if custom}
    <span class="time-custom">
      <input class="input" type="number" min="0" max="60" bind:value={minutes} oninput={setCustom} aria-label={t("edit.minutes")} />
      <span>{t("edit.minutesShort")}</span>
      <input class="input" type="number" min="0" max="59" step="5" bind:value={seconds} oninput={setCustom} aria-label={t("edit.seconds")} />
      <span>{t("edit.secondsShort")}</span>
    </span>
  {/if}
</div>
