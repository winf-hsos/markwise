<script>
  import Dialog from "./Dialog.svelte";
  import Icon from "./Icon.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { inline } from "../lib/inline.js";

  // Ask the language model for wrong options and let the examiner pick which ones become options.
  let { open = $bindable(false), pool = "", fields = null, lang = "de", room = 3, onapply } = $props();

  let count = $state(2);
  let proposals = $state([]);
  let chosen = $state([]);
  let busy = $state(false);
  let error = $state("");

  $effect(() => {
    if (open) {
      count = Math.max(1, Math.min(room || 1, 3));
      proposals = [];
      chosen = [];
      error = "";
    }
  });

  async function ask() {
    busy = true;
    error = "";
    try {
      proposals = await call("assist_distractors", pool, $state.snapshot(fields), count);
      chosen = proposals.map(() => true);
    } catch (err) {
      error = errorText(err);
    } finally {
      busy = false;
    }
  }

  function apply() {
    onapply?.(proposals.filter((_, i) => chosen[i]));
    open = false;
  }
</script>

<Dialog bind:open title={t("assist.distractorsTitle")} lead={t("assist.distractorsLead")} wide>
  <div class="assist-ask">
    <label class="field">
      <span>{t("assist.count")}</span>
      <select class="select" bind:value={count}>
        {#each [1, 2, 3, 4] as n}<option value={n}>{n}</option>{/each}
      </select>
    </label>
    <button type="button" class="btn" onclick={ask} disabled={busy}><Icon name="spark" />{busy ? t("assist.working") : proposals.length ? t("assist.again") : t("assist.propose")}</button>
  </div>
  {#if proposals.length}
    <ul class="proposals">
      {#each proposals as p, i}
        <li>
          <label>
            <input type="checkbox" bind:checked={chosen[i]} />
            <span>
              <span class="proposal-text">{@html inline(p.text[lang] ?? Object.values(p.text)[0])}</span>
              <span class="option-feedback">{@html inline(p.feedback[lang] ?? Object.values(p.feedback)[0])}</span>
              {#if p.misconception}<span class="proposal-why">{t("assist.misconception")}: {p.misconception}</span>{/if}
            </span>
          </label>
        </li>
      {/each}
    </ul>
  {/if}
  {#if error}<p class="form-error" role="alert">{error}</p>{/if}
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (open = false)}>{t("dialog.cancel")}</button>
    <button class="btn primary" type="button" onclick={apply} disabled={!chosen.some(Boolean)}>{t("assist.addChosen")}</button>
  {/snippet}
</Dialog>
