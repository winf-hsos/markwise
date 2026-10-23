<script>
  import { untrack } from "svelte";
  import Icon from "../components/Icon.svelte";
  import QuestionPreview from "../components/QuestionPreview.svelte";
  import QuestionEditor from "../components/QuestionEditor.svelte";
  import NewQuestionDialog from "../components/NewQuestionDialog.svelte";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { app, showToast } from "../lib/state.svelte.js";

  const modulePath = $derived(app.settings?.current_module || "");
  const module = $derived(app.workspace.modules.find((m) => m.path === modulePath) ?? null);

  let loading = $state(false);
  let error = $state("");
  let pools = $state([]);
  let questions = $state([]);
  let selected = $state(null); // { pool, id }
  let detail = $state(null);
  let editing = $state(null); // the detail of the question in the editor
  let newOpen = $state(false);

  const blank = { search: "", pool: "", concept: "", level: "", status: "", type: "", use: "", findings: "" };
  let filter = $state({ ...blank });

  async function load() {
    if (!modulePath) return;
    loading = true;
    error = "";
    try {
      const result = await call("list_questions", modulePath);
      pools = result.pools;
      questions = result.questions;
      if (selected && !questions.some((q) => q.id === selected.id && q.pool === selected.pool)) selected = null;
      if (selected) await show(selected);
    } catch (err) {
      error = errorText(err);
    } finally {
      loading = false;
    }
  }

  // Load again whenever another module becomes the current one.
  $effect(() => {
    modulePath;
    selected = null;
    detail = null;
    editing = null;
    untrack(() => {
      filter = { ...blank };
      load();
    });
  });

  const words = $derived(filter.search.toLowerCase().split(/\s+/).filter(Boolean));
  const shown = $derived(
    questions.filter(
      (q) =>
        (!filter.pool || q.pool === filter.pool) &&
        (!filter.concept || q.concept === filter.concept) &&
        (!filter.level || q.level === filter.level) &&
        (!filter.status || q.status === filter.status) &&
        (!filter.type || q.type === filter.type) &&
        (!filter.use || (filter.use === "practice" ? q.public : q.exam)) &&
        (!filter.findings ||
          (filter.findings === "errors" && q.errors > 0) ||
          (filter.findings === "warnings" && q.warnings > 0) ||
          (filter.findings === "none" && q.errors === 0 && q.warnings === 0)) &&
        words.every((w) => q.search.includes(w)),
    ),
  );
  // Sorting: the order is kept per computer, so that the list opens the way it was left.
  const SORTS = {
    id: (a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }),
    concept: (a, b) => a.concept.localeCompare(b.concept) || SORTS.id(a, b),
    modified: (a, b) => b.modified - a.modified,
    level: (a, b) => LEVELS.indexOf(a.level) - LEVELS.indexOf(b.level) || SORTS.id(a, b),
    status: (a, b) => STATUSES.indexOf(a.status) - STATUSES.indexOf(b.status) || SORTS.id(a, b),
    findings: (a, b) => b.errors - a.errors || b.warnings - a.warnings || SORTS.id(a, b),
  };
  const LEVELS = ["remember", "understand", "apply"];
  const STATUSES = ["draft", "reviewed", "piloted", "retired"];
  let sort = $state(readSort());
  function readSort() {
    try {
      const saved = localStorage.getItem("markwise-question-sort");
      return saved in SORTS ? saved : "id";
    } catch {
      return "id";
    }
  }
  $effect(() => {
    try {
      localStorage.setItem("markwise-question-sort", sort);
    } catch {
      /* no storage: the order is simply not kept */
    }
  });
  const sorted = $derived([...shown].sort(SORTS[sort]));

  const concepts = $derived([...new Set(questions.filter((q) => !filter.pool || q.pool === filter.pool).map((q) => q.concept))].sort());
  const filtered = $derived(Object.entries(filter).some(([, v]) => v));
  // The selection counts only while the question is in the list: a filter or search that drops it empties the
  // preview, and undoing the filter brings it back.
  const selectedRow = $derived(selected ? (shown.find((q) => q.id === selected.id && q.pool === selected.pool) ?? null) : null);

  async function show(row) {
    selected = { pool: row.pool, id: row.id };
    try {
      detail = await call("get_question", row.pool, row.id);
    } catch (err) {
      detail = null;
      showToast(errorText(err));
    }
  }

  // Up and down move through the list while the search field or the list has the focus.
  function onkeydown(event) {
    if (editing || !["ArrowDown", "ArrowUp"].includes(event.key) || event.target.closest?.("select, .preview")) return;
    if (!shown.length) return;
    event.preventDefault();
    const index = selectedRow ? sorted.indexOf(selectedRow) : -1;
    const next = sorted[Math.max(0, Math.min(sorted.length - 1, index + (event.key === "ArrowDown" ? 1 : -1)))];
    show(next);
    document.getElementById(`q-${next.pool}-${next.id}`)?.scrollIntoView({ block: "nearest" });
  }

  // The practice questions of the pool being edited, for the choice "exam variant of".
  const practice = $derived(editing ? questions.filter((q) => q.pool === editing.pool && q.public && q.type !== "free_text") : []);

  async function edit() {
    editing = await call("get_question", detail.pool, detail.id);
  }

  function created(fresh) {
    showToast(t("newQ.created", { id: fresh.id }));
    selected = { pool: fresh.pool, id: fresh.id };
    editing = fresh;
    load();
  }

  async function closeEditor() {
    editing = null;
    await load();
  }

  async function openFile(path) {
    try {
      await call("open_file", path);
    } catch (err) {
      showToast(errorText(err));
    }
  }
</script>

<svelte:window {onkeydown} />

<div class="page page-wide">
  <div class="page-head">
    <div>
      <h1>{t("questions.title")}</h1>
      <p>{pools.length ? t("q.from", { pools: pools.map((p) => p.name).join(t("q.and")) }) : t("questions.lead")}</p>
    </div>
    {#if module && !editing}
      <div class="actions">
        <button class="btn" onclick={load} disabled={loading}><Icon name="refresh" />{t("q.reload")}</button>
        {#if pools.some((p) => p.exists)}
          <button class="btn primary" onclick={() => (newOpen = true)}><Icon name="plus" />{t("q.new")}</button>
        {/if}
      </div>
    {/if}
  </div>

  {#if !module}
    <div class="empty">
      <div class="mark"><Icon name="questions" /></div>
      <h2>{t("q.noModule.title")}</h2>
      <p>{t("q.noModule.text")}</p>
      <div class="actions"><a class="btn primary" href="#/modules"><Icon name="modules" />{t("q.toModules")}</a></div>
    </div>
  {:else if error}
    <p class="form-error">{error}</p>
  {:else if editing}
    {#key editing.pool + editing.id}
      <QuestionEditor question={editing} {practice} onclose={closeEditor} onsaved={() => load()} />
    {/key}
  {:else if !loading && pools.length === 0}
    <div class="empty"><div class="mark"><Icon name="questions" /></div><p>{t("q.noPool")}</p></div>
  {:else}
    <div class="q-tools">
      <div class="search">
        <Icon name="search" />
        <input class="input" type="search" bind:value={filter.search} placeholder={t("q.search")} aria-label={t("q.search")} />
      </div>
      <div class="q-filters">
        {#if pools.length > 1}
          <select class="select" bind:value={filter.pool} aria-label={t("q.meta.pool")}>
            <option value="">{t("q.all.pools")}</option>
            {#each pools as p}<option value={p.path}>{p.name}</option>{/each}
          </select>
        {/if}
        <select class="select" bind:value={filter.concept} aria-label={t("q.meta.concept")}>
          <option value="">{t("q.all.concepts")}</option>
          {#each concepts as c}<option value={c}>{c}</option>{/each}
        </select>
        <select class="select" bind:value={filter.level} aria-label={t("q.meta.level")}>
          <option value="">{t("q.all.levels")}</option>
          {#each ["remember", "understand", "apply"] as v}<option value={v}>{t(`level.${v}`)}</option>{/each}
        </select>
        <select class="select" bind:value={filter.status} aria-label={t("q.meta.status")}>
          <option value="">{t("q.all.status")}</option>
          {#each ["draft", "reviewed", "piloted", "retired"] as v}<option value={v}>{t(`status.${v}`)}</option>{/each}
        </select>
        <select class="select" bind:value={filter.type} aria-label="Typ">
          <option value="">{t("q.all.types")}</option>
          {#each ["single", "multiple", "free_text"] as v}<option value={v}>{t(`type.${v}`)}</option>{/each}
        </select>
        <select class="select" bind:value={filter.use} aria-label={t("q.meta.use")}>
          <option value="">{t("q.all.use")}</option>
          <option value="practice">{t("use.practice")}</option>
          <option value="exam">{t("use.exam")}</option>
        </select>
        <select class="select" bind:value={filter.findings} aria-label={t("q.findings")}>
          <option value="">{t("q.all.findings")}</option>
          <option value="errors">{t("q.findings.errors")}</option>
          <option value="warnings">{t("q.findings.warnings")}</option>
          <option value="none">{t("q.findings.none")}</option>
        </select>
      </div>
      <div class="q-count">
        <span>{t("q.count", { shown: shown.length, total: questions.length })}</span>
        {#if filtered}<button class="link-btn" onclick={() => (filter = { ...blank })}>{t("q.reset")}</button>{/if}
        <label class="sort">
          <span>{t("sort.label")}</span>
          <select class="select select-small" bind:value={sort}>
            {#each Object.keys(SORTS) as key}<option value={key}>{t(`sort.${key}`)}</option>{/each}
          </select>
        </label>
      </div>
    </div>

    <div class="q-split">
      <div class="q-list-pane" role="listbox" aria-label={t("questions.title")}>
        {#if loading && questions.length === 0}
          <p class="muted pad">{t("q.loading")}</p>
        {:else if shown.length === 0}
          <p class="muted pad">{t("q.noMatch")}</p>
        {/if}
        {#each sorted as q (q.pool + q.id)}
          <button id={`q-${q.pool}-${q.id}`} class="q-row" class:on={selectedRow === q} role="option" aria-selected={selectedRow === q} onclick={() => show(q)}>
            <span class="q-row-head">
              <span class="qid">{q.id}</span>
              <span class="q-concept">{q.concept}</span>
              {#if q.errors}<span class="tag red"><i class="dot"></i>{q.errors} {t("sev.error")}</span>
              {:else if q.warnings}<span class="tag warn"><i class="dot"></i>{t("sev.warning")}</span>{/if}
              {#if q.exam}<span class="tag">{q.public ? t("use.both") : t("use.exam")}</span>{/if}
            </span>
            <span class="q-stem">{q.unreadable ? t("q.unreadable") : q.stem}</span>
          </button>
        {/each}
      </div>
      <div class="q-preview-pane">
        {#if detail && selectedRow}
          <QuestionPreview question={detail} variants={selectedRow.variants} onopen={openFile} onedit={edit} />
        {:else}
          <div class="empty quiet"><p>{t("q.select")}</p></div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<NewQuestionDialog bind:open={newOpen} {pools} preset={{ pool: filter.pool, concept: filter.concept }} oncreated={created} />
