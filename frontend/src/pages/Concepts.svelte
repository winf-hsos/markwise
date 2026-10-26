<script>
  import { tick, untrack } from "svelte";
  import Icon from "../components/Icon.svelte";
  import Dialog from "../components/Dialog.svelte";
  import { ask } from "../lib/confirm.svelte.js";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { app, pending, showToast } from "../lib/state.svelte.js";
  import { slugify } from "../lib/slug.js";
  import { recall, remember } from "../lib/viewstate.svelte.js";
  import { questionsChanged, questionsOf } from "../lib/questions.svelte.js";

  const modulePath = $derived(app.settings?.current_module || "");
  const module = $derived(app.workspace.modules.find((m) => m.path === modulePath) ?? null);

  let concepts = $state([]);
  let loading = $state(false);
  let error = $state("");
  let search = $state("");
  let poolFilter = $state("");
  let selected = $state(null); // { pool, id }
  let draft = $state({ name: "", description: "" });
  let newOpen = $state(false);
  let added = $state({ pool: "", name: "", description: "" });
  let addError = $state("");
  let listPane = $state(null);
  let restoredFor = $state("");

  async function load() {
    if (!modulePath) return;
    loading = true;
    error = "";
    try {
      seen = questionsOf(modulePath).version;
      concepts = await call("concept_overview", modulePath);
    } catch (err) {
      error = errorText(err);
    } finally {
      loading = false;
    }
  }

  // Take up where the person left this module's concepts: search, pool filter, selection, scroll position.
  $effect(() => {
    modulePath;
    untrack(async () => {
      const kept = recall("concepts", modulePath);
      search = kept.search ?? "";
      poolFilter = kept.poolFilter ?? "";
      selected = null;
      restoredFor = ""; // remember nothing until the remembered state is back, or a half-done restore overwrites it
      await load();
      const again = kept.selected && concepts.find((c) => c.pool === kept.selected.pool && c.id === kept.selected.id);
      if (again) choose(again);
      await tick();
      if (listPane && kept.scroll) listPane.scrollTop = kept.scroll;
      restoredFor = modulePath;
    });
  });

  // The page stays open in the background: when the questions were read again after a change on another page,
  // the counts here follow.
  let seen = -1;
  $effect(() => {
    const version = questionsOf(modulePath).version;
    untrack(() => {
      if (restoredFor === modulePath && version !== seen) load();
    });
  });

  $effect(() => {
    const state = { search, poolFilter, selected: $state.snapshot(selected) };
    if (restoredFor === modulePath) untrack(() => remember("concepts", modulePath, state));
  });

  const pools = $derived([...new Map(concepts.map((c) => [c.pool, c.pool_name])).entries()]);
  const shown = $derived(
    concepts.filter((c) => {
      if (poolFilter && c.pool !== poolFilter) return false;
      const words = search.toLowerCase().split(/\s+/).filter(Boolean);
      const text = `${c.name} ${c.description} ${c.id}`.toLowerCase();
      return words.every((w) => text.includes(w));
    }),
  );
  // The selection counts only while the concept is in the list, as on the Questions page.
  const current = $derived(selected ? (shown.find((c) => c.pool === selected.pool && c.id === selected.id) ?? null) : null);
  const changed = $derived(current && (draft.name.trim() !== (current.named ? current.name : "") || draft.description.trim() !== current.description));

  function choose(c) {
    selected = { pool: c.pool, id: c.id };
    draft = { name: c.named ? c.name : "", description: c.description };
  }

  async function save(event) {
    event.preventDefault();
    try {
      await call("update_concept", current.pool, current.id, draft.name, draft.description);
      await load();
      questionsChanged(modulePath); // the questions show the concept's name
      showToast(t("concepts.saved"));
    } catch (err) {
      showToast(errorText(err));
    }
  }

  async function remove() {
    if (!(await ask({ title: t("concepts.delete"), message: t("concepts.confirmDelete", { name: current.name }), action: t("concepts.delete"), danger: true }))) return;
    try {
      await call("delete_concept", current.pool, current.id);
      selected = null;
      await load();
      questionsChanged(modulePath);
      showToast(t("concepts.deleted"));
    } catch (err) {
      showToast(errorText(err));
    }
  }

  function showQuestions() {
    pending.questionsFilter = { pool: current.pool, concept: current.id };
    location.hash = "#/questions";
  }

  function newQuestion() {
    pending.newQuestion = { pool: current.pool, concept: current.id };
    location.hash = "#/questions";
  }

  function openNew() {
    added = { pool: poolFilter || current?.pool || pools[0]?.[0] || "", name: "", description: "" };
    addError = "";
    newOpen = true;
  }

  async function add(event) {
    event.preventDefault();
    addError = "";
    try {
      const created = await call("add_concept", added.pool, added.name, added.description);
      newOpen = false;
      await load();
      questionsChanged(modulePath); // new questions can go into it
      choose(concepts.find((c) => c.pool === added.pool && c.id === created.id));
      showToast(t("concepts.added", { name: created.name }));
    } catch (err) {
      addError = errorText(err);
    }
  }

  // A bar per value, scaled to the largest count of its group.
  const bars = (group, keyPrefix) => {
    const max = Math.max(1, ...Object.values(group));
    return Object.entries(group).map(([key, n]) => ({ label: t(`${keyPrefix}.${key}`), n, width: (n / max) * 100 }));
  };
</script>

<div class="page page-wide">
  <div class="page-head">
    <div>
      <h1>{t("concepts.title")}</h1>
      <p>{t("concepts.pageLead")}</p>
    </div>
    {#if module && pools.length}
      <div class="actions">
        <button class="btn primary" onclick={openNew}><Icon name="plus" />{t("concepts.new")}</button>
      </div>
    {/if}
  </div>

  {#if !module}
    <div class="empty">
      <div class="mark"><Icon name="concepts" /></div>
      <h2>{t("q.noModule.title")}</h2>
      <p>{t("q.noModule.text")}</p>
      <div class="actions"><a class="btn primary" href="#/modules"><Icon name="modules" />{t("q.toModules")}</a></div>
    </div>
  {:else if error}
    <p class="form-error">{error}</p>
  {:else}
    <div class="q-tools concept-tools">
      <div class="search">
        <Icon name="search" />
        <input class="input" type="search" bind:value={search} placeholder={t("concepts.search")} aria-label={t("concepts.search")} />
      </div>
      {#if pools.length > 1}
        <select class="select" bind:value={poolFilter} aria-label={t("q.meta.pool")}>
          <option value="">{t("q.all.pools")}</option>
          {#each pools as [path, name]}<option value={path}>{name}</option>{/each}
        </select>
      {/if}
      <span class="q-count">{t("concepts.count", { shown: shown.length, total: concepts.length })}</span>
    </div>
    <div class="q-split">
      <div class="q-list-pane" role="listbox" aria-label={t("concepts.title")} bind:this={listPane}
        onscroll={() => remember("concepts", modulePath, { scroll: listPane.scrollTop })}>
        {#if loading && !concepts.length}<p class="muted pad">{t("loading")}</p>{/if}
        {#each shown as c (c.pool + c.id)}
          <button class="q-row concept-row" class:on={current === c} role="option" aria-selected={current === c} onclick={() => choose(c)}>
            <span class="q-row-head">
              <span class="concept-name" class:unnamed={!c.named}>{c.name}</span>
              {#if c.with_errors}<span class="tag red"><i class="dot"></i>{c.with_errors}</span>{/if}
              <span class="count">{c.questions}</span>
            </span>
            {#if c.description}<span class="q-stem">{c.description}</span>{/if}
            {#if pools.length > 1 && !poolFilter}<span class="q-concept">{c.pool_name}</span>{/if}
          </button>
        {/each}
      </div>
      <div class="q-preview-pane">
        {#if current}
          <article class="preview concept-detail">
            <form class="form" onsubmit={save}>
              <label class="field">
                <span>{t("concepts.name")}</span>
                <input class="input concept-title-input" bind:value={draft.name} placeholder={current.name} />
              </label>
              <label class="field">
                <span>{t("concepts.description")}</span>
                <textarea class="input grow-text" rows="2" bind:value={draft.description} placeholder={t("concepts.descriptionPlaceholder")}></textarea>
              </label>
              <div class="concept-actions">
                <span class="concept-id">{current.id}</span>
                <button class="btn" class:primary={changed} type="submit" disabled={!changed || !draft.name.trim()}>{t("settings.save")}</button>
              </div>
            </form>

            <section class="preview-section">
              <div class="concept-head-row">
                <h4 class="sub">{t(current.questions === 1 ? "modules.question" : "modules.questions", { count: current.questions })}</h4>
                <span class="spacer"></span>
                <button class="btn" onclick={showQuestions} disabled={!current.questions}><Icon name="questions" />{t("concepts.showQuestions")}</button>
                <button class="btn" onclick={newQuestion}><Icon name="plus" />{t("q.new")}</button>
              </div>
              {#if current.questions}
                <div class="stat-groups">
                  {#each [[t("q.meta.level"), bars(current.levels, "level")], [t("edit.type"), bars(current.types, "type")], [t("q.meta.status"), bars(current.statuses, "status")]] as [title, rows]}
                    <div class="stat-group">
                      <h5>{title}</h5>
                      {#each rows as row}
                        <div class="stat-row"><span>{row.label}</span><span class="stat-bar"><i style="width: {row.width}%"></i></span><b>{row.n}</b></div>
                      {/each}
                    </div>
                  {/each}
                </div>
                <ul class="concept-facts">
                  <li><span>{t("use.practice")}</span><b>{current.practice}</b></li>
                  <li><span>{t("use.exam")}</span><b>{current.exam}</b></li>
                  <li><span>{t("concepts.withoutVariant")}</span><b class:warn-text={current.without_variant}>{current.without_variant}</b></li>
                  <li><span>{t("q.findings.errors")}</span><b class:red-text={current.with_errors}>{current.with_errors}</b></li>
                  <li><span>{t("q.findings.warnings")}</span><b class:warn-text={current.with_warnings}>{current.with_warnings}</b></li>
                  {#if current.retired}<li><span>{t("status.retired")}</span><b>{current.retired}</b></li>{/if}
                </ul>
              {:else}
                <p class="muted">{t("concepts.noQuestions")}</p>
                <button class="btn ghost danger" onclick={remove}><Icon name="remove" />{t("concepts.delete")}</button>
              {/if}
            </section>
          </article>
        {:else}
          <div class="empty quiet"><p>{t("concepts.select")}</p></div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<Dialog bind:open={newOpen} title={t("concepts.new")} lead={t("concepts.newLead")}>
  <form id="new-concept" class="form" onsubmit={add} oninput={() => (addError = "")}>
    {#if pools.length > 1}
      <label class="field">
        <span>{t("newQ.pool")}</span>
        <select class="select" bind:value={added.pool}>
          {#each pools as [path, name]}<option value={path}>{name}</option>{/each}
        </select>
      </label>
    {/if}
    <label class="field">
      <span>{t("concepts.name")}</span>
      <input class="input" bind:value={added.name} placeholder={t("concepts.namePlaceholder")} />
      {#if added.name.trim()}<small class="hint">{t("concepts.idPreview", { id: slugify(added.name) })}</small>{/if}
    </label>
    <label class="field">
      <span>{t("concepts.description")}</span>
      <textarea class="input grow-text" rows="2" bind:value={added.description} placeholder={t("concepts.descriptionPlaceholder")}></textarea>
    </label>
    {#if addError}<p class="form-error" role="alert">{addError}</p>{/if}
  </form>
  {#snippet footer()}
    <button class="btn ghost" type="button" onclick={() => (newOpen = false)}>{t("dialog.cancel")}</button>
    <button class="btn primary" type="submit" form="new-concept" disabled={!added.name.trim()}>{t("concepts.add")}</button>
  {/snippet}
</Dialog>
