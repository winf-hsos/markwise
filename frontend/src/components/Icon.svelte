<script>
  import { ICONS } from "../lib/icons.js";

  let { name } = $props();
</script>

<svg viewBox="0 0 24 24" aria-hidden="true">{@html ICONS[name]}</svg>
