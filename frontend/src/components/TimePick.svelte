<script>
  import { tick } from "svelte";
  import { t } from "../lib/i18n.svelte.js";
  import { formatTime } from "../lib/time.js";

  // A question's answering time as a label that opens a small choice on a click: the usual steps, or any other
  // time in minutes and seconds. `onchoose(seconds)` receives the time chosen; `title` names the question.
  // For a variant, `inherited` is its parent's time and `parent` its identifier: the label then shows that time
  // lighter while the variant has none of its own, and the choice offers to take it again (`onchoose(null)`).
  // `note` replaces the remark that the time belongs to the question in its pool.
  // `align` "left" opens the choice to the right of the label instead of to its left.
  let { seconds = null, title = "", onchoose, inherited = null, parent = "", note = null, align = "right" } = $props();
  const fromParent = $derived(seconds == null && inherited != null);
  const shown = $derived(seconds ?? inherited);

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
    minutes = shown ? Math.floor(shown / 60) : 1;
    rest = shown ? shown % 60 : 0;
    if (open) {
      await tick();
      first?.focus();
    }
  }

  function choose(value) {
    open = false;
    if ((value || value === null) && value !== seconds) onchoose?.(value);
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
  <button type="button" class="tag tag-button" class:warn={!shown} class:faint={fromParent} aria-haspopup="true" aria-expanded={open}
    title={fromParent ? t("edit.inheritedHint", { id: parent }) : t("timePick.hint")} onclick={toggle}>{shown ? formatTime(shown) : t("exams.noTime")}</button>
  {#if open}
    <div class="time-pop tag-pop" class:left={align === "left"} role="dialog" aria-label={t("timePick.title", { id: title })}>
      <b>{t("timePick.title", { id: title })}</b>
      <div class="time-pop-chips">
        {#each PRESETS as preset, i}
          {#if i === 0}
            <button type="button" class="chip" class:on={!other && !fromParent && shown === preset} bind:this={first} onclick={() => choose(preset)}>{formatTime(preset)}</button>
          {:else}
            <button type="button" class="chip" class:on={!other && !fromParent && shown === preset} onclick={() => choose(preset)}>{formatTime(preset)}</button>
          {/if}
        {/each}
        <button type="button" class="chip" class:on={other} onclick={() => (other = true)}>{t("edit.timeOther")}</button>
        {#if inherited != null}
          <button type="button" class="chip faint" class:on={fromParent} title={t("edit.inheritAgainHint", { id: parent })}
            onclick={() => choose(null)}>{t("sheet.inherit", { value: formatTime(inherited) })}</button>
        {/if}
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
      {#if note !== ""}<span class="hint">{note ?? t("timePick.note")}</span>{/if}
    </div>
  {/if}
</span>
