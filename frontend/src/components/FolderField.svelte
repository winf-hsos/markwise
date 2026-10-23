<script>
  import { call } from "../lib/api.js";
  import { t } from "../lib/i18n.svelte.js";
  import { app } from "../lib/state.svelte.js";

  // A path field with a Browse button (Windows dialog in the app window) and a line that says what the
  // chosen folder holds. `describe` turns what the core found into a text key, or null for no line.
  let { label, value = $bindable(""), hint = "", kind = "folder", describe = null, placeholder = "" } = $props();

  let note = $state("");
  let timer = null;
  const id = `path-${Math.random().toString(36).slice(2, 9)}`;

  async function browse() {
    const picked = await call(kind === "file" ? "pick_file" : "pick_folder", value || "");
    if (picked) value = picked;
  }

  $effect(() => {
    const path = value;
    clearTimeout(timer);
    if (!describe || !path.trim()) {
      note = "";
      return;
    }
    timer = setTimeout(async () => {
      try {
        const key = describe(await call("inspect_folder", path.trim()));
        note = key ? t(key) : "";
      } catch {
        note = "";
      }
    }, 250);
  });
</script>

<div class="field">
  <label for={id}>{label}</label>
  <div class="path-input">
    <input {id} class="input" bind:value {placeholder} spellcheck="false" />
    {#if app.info?.dialogs}
      <button class="btn" type="button" onclick={browse}>{t("dialog.browse")}</button>
    {/if}
  </div>
  {#if note}<small class="note">{note}</small>{:else if hint}<small class="hint">{hint}</small>{/if}
</div>
