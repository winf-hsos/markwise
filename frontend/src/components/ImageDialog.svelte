<script>
  import Dialog from "./Dialog.svelte";
  import Icon from "./Icon.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { app } from "../lib/state.svelte.js";

  // Choose the figures of a question from the pool's images, in the order clicked, and how they are laid out;
  // a new image file can be brought into the pool on the way.
  let { open = $bindable(false), pool = "", current = [], columns = 1, onapply } = $props();

  let images = $state([]);
  let chosen = $state([]); // names in the order they were chosen
  let layout = $state(1); // 1: one below the other; n: n columns
  let path = $state("");
  let error = $state("");
  let busy = $state(false);

  async function load() {
    images = await call("list_images", pool);
  }

  $effect(() => {
    if (open) {
      chosen = [...current];
      layout = columns;
      path = "";
      error = "";
      load();
    }
  });

  // The layouts that fit the number of figures: below each other, side by side, or a grid of 2 or 3 columns.
  const layouts = $derived(
    chosen.length < 2
      ? []
      : [
          [1, t("attach.layoutRows")],
          [Math.min(chosen.length, 4), t("attach.layoutSide")],
          ...[2, 3].filter((n) => n < chosen.length).map((n) => [n, t("attach.layoutColumns", { n })]),
        ],
  );

  $effect(() => {
    if (layouts.length && !layouts.some(([n]) => n === layout)) layout = 1;
  });

  function toggle(name) {
    chosen = chosen.includes(name) ? chosen.filter((n) => n !== name) : [...chosen, name];
  }

  async function addImage(source) {
    if (!source) return;
    busy = true;
    error = "";
    try {
      const added = await call("add_image", pool, source);
      await load();
      if (!chosen.includes(added.name)) chosen = [...chosen, added.name];
      path = "";
    } catch (err) {
      error = errorText(err);
    } finally {
      busy = false;
    }
  }

  async function browse() {
    const picked = await call("pick_file", "", "image");
    if (picked) await addImage(picked);
  }

  function apply() {
    const figures = chosen.map((name) => ({ name, data: images.find((i) => i.name === name)?.data ?? null }));
    onapply?.(figures, chosen.length > 1 ? layout : 1);
    open = false;
  }
</script>

<Dialog bind:open title={t("attach.imageTitle")} lead={t("attach.imageLead")} wide>
  {#if images.length}
    <div class="image-grid" role="listbox" aria-multiselectable="true" aria-label={t("attach.imageTitle")}>
      {#each images as image (image.name)}
        {@const position = chosen.indexOf(image.name)}
        <button type="button" class="image-tile" class:on={position >= 0} role="option" aria-selected={position >= 0}
          onclick={() => toggle(image.name)}>
          <span class="image-thumb"><img src={image.data} alt="" />{#if position >= 0}<span class="image-order">{position + 1}</span>{/if}</span>
          <span class="image-name">{image.name}</span>
        </button>
      {/each}
    </div>
  {:else}
    <p class="muted">{t("attach.noImages")}</p>
  {/if}

  {#if layouts.length}
    <div class="field image-layout">
      <span>{t("attach.layout")}</span>
      <div class="seg" role="group" aria-label={t("attach.layout")}>
        {#each layouts as [n, label]}
          <button type="button" class:on={layout === n} onclick={() => (layout = n)}>{label}</button>
        {/each}
      </div>
      <small class="hint">{t("attach.orderHint")}</small>
    </div>
  {/if}

  <div class="image-add">
    {#if app.info?.dialogs}
      <button type="button" class="btn" onclick={browse} disabled={busy}><Icon name="upload" />{t("attach.imageFromFile")}</button>
    {:else}
      <input class="input" bind:value={path} placeholder={t("attach.imagePath")} aria-label={t("attach.imagePath")} />
      <button type="button" class="btn" onclick={() => addImage(path.trim())} disabled={busy || !path.trim()}>{t("attach.imageAdd")}</button>
    {/if}
    <small class="hint">{t("attach.imageHint")}</small>
  </div>
  {#if error}<p class="form-error" role="alert">{error}</p>{/if}

  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (open = false)}>{t("dialog.cancel")}</button>
    <button class="btn primary" type="button" onclick={apply}>{t("attach.apply")}</button>
  {/snippet}
</Dialog>
