<script>
  import { t } from "../lib/i18n.svelte.js";
  import { formatTotal } from "../lib/time.js";

  // A short overview of the questions the filters let through: total answering time, and how many of each type,
  // level, status, use and finding. A number with a filter behind it sets that filter, and clicking it again clears it.
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
    { title: t("stats.status"), key: "status", items: ["draft", "reviewed", "piloted", "retired"].map((v) => ({ value: v, label: t(`status.${v}`), n: count((r) => r.status === v) })) },
    { title: t("stats.use"), key: "use", items: [
      { value: "practice", label: t("use.practice"), n: count((r) => r.public) },
      { value: "exam", label: t("use.exam"), n: count((r) => r.exam) },
      { value: null, label: t("use.both"), n: count((r) => r.public && r.exam) },
    ] },
    { title: t("stats.findings"), key: "findings", items: [
      { value: "errors", label: t("stats.withErrors"), n: count((r) => r.errors > 0), tone: "red" },
      { value: "warnings", label: t("stats.withWarnings"), n: count((r) => r.warnings > 0), tone: "warn" },
      { value: "none", label: t("stats.clean"), n: count((r) => !r.errors && !r.warnings), tone: "ok" },
    ] },
  ]);

  function toggle(key, value) {
    filter[key] = filter[key] === value ? "" : value;
  }
</script>

<section class="q-stats" aria-label={t("stats.title")}>
  <div class="stat-block stat-main">
    <span class="stat-title">{t("stats.time")}</span>
    <b class="stat-big">{formatTotal(seconds)}</b>
    <span class="hint">{t(active.length === 1 ? "stats.forOne" : "stats.forMany", { n: active.length })}</span>
    {#if withoutTime}<span class="hint warn-text">{t("stats.withoutTime", { n: withoutTime })}</span>{/if}
  </div>
  {#each groups as group}
    <div class="stat-block">
      <span class="stat-title">{group.title}</span>
      <div class="stat-items">
        {#each group.items as item}
          {#if item.value}
            <button type="button" class="stat-item {item.tone ?? ''}" class:on={filter[group.key] === item.value} class:zero={!item.n}
              title={t(filter[group.key] === item.value ? "stats.clearFilter" : "stats.setFilter")} onclick={() => toggle(group.key, item.value)}>
              <span>{item.label}</span><b>{item.n}</b>
            </button>
          {:else}
            <span class="stat-item static" class:zero={!item.n}><span>{item.label}</span><b>{item.n}</b></span>
          {/if}
        {/each}
      </div>
    </div>
  {/each}
  <div class="stat-block">
    <span class="stat-title">{t("stats.variants")}</span>
    <div class="stat-items">
      <span class="stat-item static" class:zero={!variants}><span>{t("q.variants")}</span><b>{variants}</b></span>
      <span class="stat-item static" class:zero={!withoutVariant} class:warn={withoutVariant > 0}><span>{t("stats.withoutVariant")}</span><b>{withoutVariant}</b></span>
    </div>
  </div>
</section>
