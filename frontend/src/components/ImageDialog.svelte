<script>
  import Dialog from "./Dialog.svelte";
  import Icon from "./Icon.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { app } from "../lib/state.svelte.js";

  // Choose the figure of a question from the pool's images, or bring a new image file into the pool.
  let { open = $bindable(false), pool = "", current = "", onapply } = $props();

  let images = $state([]);
  let chosen = $state("");
  let path = $state("");
  let error = $state("");
  let busy = $state(false);

  async function load() {
    images = await call("list_images", pool);
  }

  $effect(() => {
    if (open) {
      chosen = current;
      path = "";
      error = "";
      load();
    }
  });

  async function addImage(source) {
    if (!source) return;
    busy = true;
    error = "";
    try {
      const added = await call("add_image", pool, source);
      await load();
      chosen = added.name;
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
    const image = images.find((i) => i.name === chosen);
    if (image) onapply?.(image.name, image.data);
    open = false;
  }
</script>

<Dialog bind:open title={t("attach.imageTitle")} lead={t("attach.imageLead")} wide>
  {#if images.length}
    <div class="image-grid" role="listbox" aria-label={t("attach.imageTitle")}>
      {#each images as image (image.name)}
        <button type="button" class="image-tile" class:on={chosen === image.name} role="option" aria-selected={chosen === image.name}
          onclick={() => (chosen = image.name)} ondblclick={apply}>
          <span class="image-thumb"><img src={image.data} alt="" /></span>
          <span class="image-name">{image.name}</span>
        </button>
      {/each}
    </div>
  {:else}
    <p class="muted">{t("attach.noImages")}</p>
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
    <button class="btn primary" type="button" onclick={apply} disabled={!chosen}>{t("attach.apply")}</button>
  {/snippet}
</Dialog>
