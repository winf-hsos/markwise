<script>
  import Icon from "../components/Icon.svelte";
  import { t } from "../lib/i18n.svelte.js";

  // A page whose content comes in a later step: title, lead and what will be there.
  let { title, lead, text, icon } = $props();
</script>

<div class="page">
  <div class="page-head">
    <div>
      <h1>{t(title)}</h1>
      <p>{t(lead)}</p>
    </div>
  </div>
  <div class="empty">
    <div class="mark"><Icon name={icon} /></div>
    <p>{t(text)}</p>
  </div>
</div>
