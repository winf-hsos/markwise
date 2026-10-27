<script>
  import { t } from "../lib/i18n.svelte.js";
  import { TIME_BUCKETS, bucketLabel, formatTotal, timeBucket } from "../lib/time.js";

  // A short overview of the questions the filters let through: total answering time, and as bars how many of each
  // type, level, status, use, finding and answering time. A bar with a filter behind it adds that value to the
  // filter, and clicking it again takes it out.
  let { rows = [], filter = $bindable() } = $props();

  const active = $derived(rows.filter((r) => r.status !== "retired"));
  const seconds = $derived(active.reduce((sum, r) => sum + (r.time_seconds ?? 0), 0));
  const withoutTime = $derived(active.filter((r) => r.time_seconds == null).length);
  const variants = $derived(rows.filter((r) => r.variant_of).length);
  const withoutVariant = $derived(
    active.filter((r) => r.public && !r.exam && r.type !== "free_text" && !r.variant_of && !r.variants.length).length,
  );

  const count = (test) => rows.filter(test).length;
  const groups = $derived([
    { title: t("stats.type"), key: "type", items: ["single", "multiple", "free_text"].map((v) => ({ value: v, label: t(`type.${v}`), n: count((r) => r.type === v) })) },
    { title: t("stats.level"), key: "level", items: ["remember", "understand", "apply"].map((v) => ({ value: v, label: t(`level.${v}`), n: count((r) => r.level === v) })) },
    { title: t("stats.status"), key: "status", items: ["draft", "released", "piloted", "retired"].map((v) => ({ value: v, label: t(`status.${v}`), n: count((r) => r.status === v) })) },
    { title: t("stats.use"), key: "use", items: [
      { value: "practice", label: t("use.practice"), n: count((r) => r.public) },
      { value: "exam", label: t("use.exam"), n: count((r) => r.exam) },
      { value: null, label: t("stats.both"), n: count((r) => r.public && r.exam) },
    ] },
    { title: t("stats.findings"), key: "findings", items: [
      { value: "errors", label: t("stats.withErrors"), n: count((r) => r.errors > 0), tone: "red" },
      { value: "warnings", label: t("stats.withWarnings"), n: count((r) => r.warnings > 0), tone: "warn" },
      { value: "none", label: t("stats.clean"), n: count((r) => !r.errors && !r.warnings), tone: "ok" },
    ] },
    { title: t("stats.times"), key: "time", items: TIME_BUCKETS.map((v) => ({ value: v, label: bucketLabel(v, t), n: count((r) => timeBucket(r.time_seconds) === v), tone: v === "none" ? "warn" : "" })).filter((item) => item.n || item.value === "none") },
  ]);

  const share = (n) => (rows.length ? Math.round((100 * n) / rows.length) : 0);

  function toggle(key, value) {
    filter[key] = filter[key].includes(value) ? filter[key].filter((v) => v !== value) : [...filter[key], value];
  }
</script>

<section class="q-stats" aria-label={t("stats.title")}>
  <div class="stat-block stat-main">
    <span class="stat-title">{t("stats.time")}</span>
    <b class="stat-big">{formatTotal(seconds)}</b>
    <span class="hint">{t(active.length === 1 ? "stats.forOne" : "stats.forMany", { n: active.length })}</span>
    {#if withoutTime}<span class="hint warn-text">{t("stats.withoutTime", { n: withoutTime })}</span>{/if}
    <span class="stat-title stat-sub">{t("stats.variants")}</span>
    <span class="hint">{t("stats.variantCount", { n: variants })}</span>
    {#if withoutVariant}<span class="hint warn-text">{t("stats.withoutVariantCount", { n: withoutVariant })}</span>{/if}
  </div>
  {#each groups as group}
    <div class="stat-block stat-bars">
      <span class="stat-title">{group.title}</span>
      {#each group.items as item}
        {#if item.value}
          <button type="button" class="bar-row {item.tone ?? ''}" class:on={filter[group.key].includes(item.value)} class:zero={!item.n}
            title={t(filter[group.key].includes(item.value) ? "stats.clearFilter" : "stats.setFilter")} onclick={() => toggle(group.key, item.value)}>
            <span class="bar-label">{item.label}</span>
            <span class="bar"><span style="width: {share(item.n)}%"></span></span>
            <b>{item.n}</b>
          </button>
        {:else}
          <span class="bar-row static" class:zero={!item.n}>
            <span class="bar-label">{item.label}</span>
            <span class="bar"><span style="width: {share(item.n)}%"></span></span>
            <b>{item.n}</b>
          </span>
        {/if}
      {/each}
    </div>
  {/each}
</section>
