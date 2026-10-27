<script>
  import { tick } from "svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { showToast } from "../lib/state.svelte.js";

  // The concept of a question as a label that opens the list of its pool's concepts on a click, like the other
  // labels of a question. Choosing one moves the question there, with its exam variants (the page does that in
  // `onchoose(conceptId)`); the identifier stays. A variant belongs to the concept of the question it varies, so
  // its label only says so. `quiet` draws the label as plain text, for the narrow bar of a question in an exam.
  let { pool, concept, name, variantOf = null, variants = 0, quiet = false, onchoose } = $props();

  let open = $state(false);
  let concepts = $state(null);
  let root = $state(null);
  let list = $state(null);

  async function toggle() {
    open = !open;
    if (!open) return;
    try {
      concepts = await call("list_concepts", pool);
    } catch (err) {
      showToast(errorText(err));
      open = false;
      return;
    }
    await tick();
    list?.querySelector(".on")?.scrollIntoView({ block: "nearest" });
    list?.querySelector(".on, button")?.focus();
  }

  function choose(id) {
    open = false;
    if (id !== concept) onchoose?.(id);
  }

  function closeOnOutside(event) {
    if (open && root && !root.contains(event.target)) open = false;
  }
</script>

<svelte:window onclick={closeOnOutside} onkeydown={(e) => open && e.key === "Escape" && (open = false)} />

{#if variantOf}
  <span class="tag" class:concept-quiet={quiet} title={t("conceptPick.variant", { id: variantOf })}>{name}</span>
{:else}
  <span class="tag-pick concept-pick" bind:this={root}>
    <button type="button" class="tag tag-button" class:concept-quiet={quiet} aria-haspopup="true" aria-expanded={open}
      title={t("conceptPick.hint")} onclick={toggle}>{name}</button>
    {#if open && concepts}
      <div class="tag-pop concept-pop" role="dialog" aria-label={t("conceptPick.title")}>
        <b>{t("conceptPick.title")}</b>
        <div class="concept-list" bind:this={list}>
          {#each concepts as c (c.id)}
            <button type="button" class:on={c.id === concept} onclick={() => choose(c.id)}>
              <span>{c.name}</span><span class="count">{c.questions}</span>
            </button>
          {/each}
        </div>
        <span class="hint">{variants ? t("conceptPick.noteVariants", { n: variants }) : t("conceptPick.note")}</span>
      </div>
    {/if}
  </span>
{/if}
