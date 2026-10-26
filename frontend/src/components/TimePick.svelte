<script>
  import { tick } from "svelte";
  import { t } from "../lib/i18n.svelte.js";
  import { formatTime } from "../lib/time.js";

  // A question's answering time as a label that opens a small choice on a click: the usual steps, or any other
  // time in minutes and seconds. `onchoose(seconds)` receives the time chosen; `title` names the question.
  let { seconds = null, title = "", onchoose } = $props();

  const PRESETS = [15, 30, 45, 60, 120, 300];
  let open = $state(false);
  let other = $state(false);
  let minutes = $state(1);
  let rest = $state(0);
  let root;
  let first = $state(null);

  async function toggle() {
    open = !open;
    other = seconds != null && !PRESETS.includes(seconds);
    minutes = seconds ? Math.floor(seconds / 60) : 1;
    rest = seconds ? seconds % 60 : 0;
    if (open) {
      await tick();
      first?.focus();
    }
  }

  function choose(value) {
    open = false;
    if (value && value !== seconds) onchoose?.(value);
  }

  function chooseOther(event) {
    event.preventDefault();
    choose(Math.max(0, Math.round(Number(minutes) || 0)) * 60 + Math.max(0, Math.round(Number(rest) || 0)));
  }

  function closeOnOutside(event) {
    if (open && root && !root.contains(event.target)) open = false;
  }
</script>

<svelte:window onclick={closeOnOutside} onkeydown={(e) => open && e.key === "Escape" && (open = false)} />

<span class="time-pick" bind:this={root}>
  <button type="button" class="tag tag-button" class:warn={!seconds} aria-haspopup="true" aria-expanded={open}
    title={t("timePick.hint")} onclick={toggle}>{seconds ? formatTime(seconds) : t("exams.noTime")}</button>
  {#if open}
    <div class="time-pop" role="dialog" aria-label={t("timePick.title", { id: title })}>
      <b>{t("timePick.title", { id: title })}</b>
      <div class="time-pop-chips">
        {#each PRESETS as preset, i}
          {#if i === 0}
            <button type="button" class="chip" class:on={seconds === preset} bind:this={first} onclick={() => choose(preset)}>{formatTime(preset)}</button>
          {:else}
            <button type="button" class="chip" class:on={seconds === preset} onclick={() => choose(preset)}>{formatTime(preset)}</button>
          {/if}
        {/each}
        <button type="button" class="chip" class:on={other} onclick={() => (other = true)}>{t("edit.timeOther")}</button>
      </div>
      {#if other}
        <form class="time-pop-other" onsubmit={chooseOther}>
          <input class="input" type="number" min="0" max="120" bind:value={minutes} aria-label={t("timePick.minutes")} />
          <span>{t("timePick.minutes")}</span>
          <input class="input" type="number" min="0" max="59" step="5" bind:value={rest} aria-label={t("timePick.seconds")} />
          <span>{t("timePick.seconds")}</span>
          <button type="submit" class="btn btn-small primary">{t("timePick.set")}</button>
        </form>
      {/if}
      <span class="hint">{t("timePick.note")}</span>
    </div>
  {/if}
</span>
