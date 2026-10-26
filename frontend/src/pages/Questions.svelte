<script>
  import { tick, untrack } from "svelte";
  import Icon from "../components/Icon.svelte";
  import QuestionPreview from "../components/QuestionPreview.svelte";
  import QuestionEditor from "../components/QuestionEditor.svelte";
  import QuestionStats from "../components/QuestionStats.svelte";
  import MultiSelect from "../components/MultiSelect.svelte";
  import { TIME_BUCKETS, bucketLabel, timeBucket } from "../lib/time.js";
  import NewQuestionDialog from "../components/NewQuestionDialog.svelte";
  import { ask } from "../lib/confirm.svelte.js";
  import { call } from "../lib/api.js";
  import { errorText, t } from "../lib/i18n.svelte.js";
  import { app, pending, showToast } from "../lib/state.svelte.js";
  import { drafts, recall, remember } from "../lib/viewstate.svelte.js";
  import { dropQuestions, ensureQuestions, questionsOf, refreshQuestions } from "../lib/questions.svelte.js";
  import { route } from "../lib/router.svelte.js";

  const modulePath = $derived(app.settings?.current_module || "");
  const module = $derived(app.workspace.modules.find((m) => m.path === modulePath) ?? null);

  // The questions come from memory, shared with the other pages; see lib/questions.svelte.js.
  const store = $derived(questionsOf(modulePath));
  const pools = $derived(store.pools);
  const questions = $derived(store.questions);
  const loading = $derived(store.loading);
  const error = $derived(store.error && !store.loaded ? errorText(store.error) : "");
  let selected = $state(null); // { pool, id }
  let detail = $state(null);
  let editing = $state(null); // the detail of the question in the editor
  let newOpen = $state(false);
  let newPreset = $state({});
  let listPane = $state(null);
  let restoredFor = $state(""); // the module whose remembered state this page shows
  let collapsed = $state([]); // keys of the questions whose variants are folded away

  // Every filter but the search is a list: several values of one filter count as "or", the filters as "and".
  const blank = { search: "", pool: [], concept: [], level: [], status: [], type: [], use: [], findings: [], time: [] };
  let filter = $state(normalized({}));

  // Filters remembered or handed over as single values, from before they took several, become lists.
  function normalized(given) {
    const result = { ...blank };
    for (const [key, value] of Object.entries(given ?? {})) {
      if (!(key in blank)) continue;
      result[key] = key === "search" ? String(value ?? "") : Array.isArray(value) ? value : value ? [value] : [];
    }
    return result;
  }

  // Read the pools again, here or on another page: the selection follows, and its preview shows the new state.
  const load = () => refreshQuestions(modulePath);
  $effect(() => {
    store.version;
    untrack(() => {
      if (!selected || !store.loaded) return;
      if (!questions.some((q) => q.id === selected.id && q.pool === selected.pool)) selected = null;
      else if (detail) show(selected);
    });
  });
  $effect(() => {
    if (store.error && store.loaded) untrack(() => showToast(errorText(store.error)));
  });

  // Whenever the page opens or another module becomes the current one: take up where the person left this
  // module (filters, selection, scroll position, an open editor), then load.
  $effect(() => {
    modulePath;
    untrack(() => restore());
  });

  async function restore() {
    const kept = recall("questions", modulePath);
    detail = null;
    editing = null;
    selected = kept.selected ?? null;
    filter = normalized(kept.filter);
    collapsed = kept.collapsed ?? [];
    // Another page may have sent the person here for one concept, or to add a question to it.
    if (pending.questionsFilter) {
      filter = normalized(pending.questionsFilter);
      pending.questionsFilter = null;
    }
    const wanted = pending.newQuestion;
    pending.newQuestion = null;
    restoredFor = ""; // remember nothing until the remembered state is back, or a half-done restore overwrites it
    await ensureQuestions(modulePath);
    if (selected) await show(selected);
    await tick();
    if (listPane && kept.scroll && !wanted) listPane.scrollTop = kept.scroll;
    if (wanted) {
      newPreset = wanted;
      newOpen = true;
    } else if (kept.editing) {
      try {
        editing = await call("get_question", kept.editing.pool, kept.editing.id);
      } catch {
        editing = null; // the question is gone; the list shows what is there
      }
    }
    restoredFor = modulePath;
  }

  // The page stays open in the background, so a hand-over from another page can arrive while it lives.
  $effect(() => {
    const wanted = pending.questionsFilter;
    const create = pending.newQuestion;
    if (!wanted && !create) return;
    untrack(() => {
      if (restoredFor !== modulePath) return; // restore() takes it up
      editing = null; // unsaved changes stay among the drafts
      if (wanted) filter = normalized(wanted);
      if (create) {
        newPreset = create;
        newOpen = true;
      }
      pending.questionsFilter = null;
      pending.newQuestion = null;
    });
  });

  // Remember what the page shows, for the next visit.
  $effect(() => {
    const state = {
      filter: $state.snapshot(filter),
      selected: $state.snapshot(selected),
      collapsed: $state.snapshot(collapsed),
      editing: editing ? { pool: editing.pool, id: editing.id } : null,
    };
    if (restoredFor === modulePath) untrack(() => remember("questions", modulePath, state));
  });

  function onListScroll() {
    remember("questions", modulePath, { scroll: listPane.scrollTop });
  }

  const draftKey = (q) => `${q.pool}\n${q.id}`;

  const words = $derived(filter.search.toLowerCase().split(/\s+/).filter(Boolean));
  const any = (chosen, test) => !chosen.length || chosen.some(test);
  const shown = $derived(
    questions.filter(
      (q) =>
        any(filter.pool, (v) => q.pool === v) &&
        any(filter.concept, (v) => q.concept === v) &&
        any(filter.level, (v) => q.level === v) &&
        any(filter.status, (v) => q.status === v) &&
        any(filter.type, (v) => q.type === v) &&
        any(filter.use, (v) => (v === "practice" ? q.public : q.exam)) &&
        any(filter.findings, (v) => (v === "errors" ? q.errors > 0 : v === "warnings" ? q.warnings > 0 : !q.errors && !q.warnings)) &&
        any(filter.time, (v) => timeBucket(q.time_seconds) === v) &&
        words.every((w) => q.search.includes(w)),
    ),
  );
  // Sorting: the order is kept per computer, so that the list opens the way it was left.
  const SORTS = {
    id: (a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }),
    concept: (a, b) => a.concept_name.localeCompare(b.concept_name) || SORTS.id(a, b),
    modified: (a, b) => b.modified - a.modified,
    level: (a, b) => LEVELS.indexOf(a.level) - LEVELS.indexOf(b.level) || SORTS.id(a, b),
    status: (a, b) => STATUSES.indexOf(a.status) - STATUSES.indexOf(b.status) || SORTS.id(a, b),
    findings: (a, b) => b.errors - a.errors || b.warnings - a.warnings || SORTS.id(a, b),
  };
  const LEVELS = ["remember", "understand", "apply"];
  const TYPE_ICONS = { single: "single", multiple: "multiple", free_text: "freetext" };
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

  // The overview above the list, shown or hidden as it was left on this computer.
  let statsOpen = $state(readStatsOpen());
  function readStatsOpen() {
    try {
      return localStorage.getItem("markwise-question-stats") === "open";
    } catch {
      return false;
    }
  }
  $effect(() => {
    try {
      localStorage.setItem("markwise-question-stats", statsOpen ? "open" : "closed");
    } catch {
      /* no storage: the choice is simply not kept */
    }
  });
  // Variants stand right below the question they vary, in the order of their identifiers. A variant whose
  // parent is filtered out stands on its own, with a note which question it varies.
  const listed = $derived.by(() => {
    const key = (pool, id) => `${pool}\n${id}`;
    const inList = new Set(shown.map((q) => key(q.pool, q.id)));
    const below = new Map();
    for (const q of shown) {
      if (q.variant_of && inList.has(key(q.pool, q.variant_of))) {
        const parent = key(q.pool, q.variant_of);
        below.set(parent, [...(below.get(parent) ?? []), q]);
      }
    }
    const rows = [];
    for (const q of sorted) {
      if (q.variant_of && inList.has(key(q.pool, q.variant_of))) continue;
      const own = key(q.pool, q.id);
      const kids = below.get(own) ?? [];
      const folded = collapsed.includes(own);
      rows.push({ q, child: false, orphan: Boolean(q.variant_of), kids: kids.length, folded });
      if (!folded) for (const v of kids.sort(SORTS.id)) rows.push({ q: v, child: true, orphan: false, kids: 0, folded: false });
    }
    return rows;
  });

  // Variants fold away below their question, one question at a time or all at once, and open again the same way.
  const rowKey = (q) => `${q.pool}\n${q.id}`;
  const withVariants = $derived(listed.filter((r) => r.kids).map((r) => rowKey(r.q)));
  const allFolded = $derived(withVariants.length > 0 && withVariants.every((k) => collapsed.includes(k)));
  function toggleVariants(q) {
    const k = rowKey(q);
    collapsed = collapsed.includes(k) ? collapsed.filter((c) => c !== k) : [...collapsed, k];
  }
  function toggleAllVariants() {
    collapsed = allFolded ? collapsed.filter((k) => !withVariants.includes(k)) : [...new Set([...collapsed, ...withVariants])];
  }
  const order = $derived(listed.map((r) => r.q));

  // Concepts for the filter, by name: [id, name], from the questions of the chosen pool.
  const concepts = $derived(
    [...new Map(questions.filter((q) => any(filter.pool, (v) => q.pool === v)).map((q) => [q.concept, q.concept_name])).entries()]
      .sort((a, b) => a[1].localeCompare(b[1])),
  );
  const filtered = $derived(Object.entries(filter).some(([, v]) => v.length > 0));
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

  // --- changes made in the preview, saved one by one, in the order they were made ---------------------
  let queue = Promise.resolve();
  let refreshLater = null;
  let saving = $state(0);
  function saveFields(fields) {
    const { pool, id } = detail;
    const since = detail.mtime_ns;
    saving += 1;
    queue = queue.then(async () => {
      try {
        // The file's time from the last save of this question, so that saves in a row do not take each other for edits elsewhere.
        const mtime = detail?.pool === pool && detail?.id === id ? detail.mtime_ns : since;
        const result = await call("save_question", pool, id, fields, mtime, false);
        const wasReviewed = detail?.data?.status === "reviewed";
        if (detail?.pool === pool && detail?.id === id) detail = result.question;
        if (result.changed) {
          showToast(wasReviewed && result.question.data.status === "draft" ? t("edit.savedDraft") : t("edit.saved"));
          // The list is read again once the edits pause, so that it does not hold up the next save.
          clearTimeout(refreshLater);
          refreshLater = setTimeout(load, 900);
        }
      } catch (err) {
        showToast(err.code === "conflict" ? t("sheet.conflict") : errorText(err));
        if (detail?.pool === pool && detail?.id === id) show({ pool, id });
      } finally {
        saving -= 1;
      }
    });
  }

  // Paging through the questions as the list shows them, also while the list is hidden.
  const position = $derived(selectedRow ? order.indexOf(selectedRow) : -1);
  function step(by) {
    const next = order[Math.max(0, Math.min(order.length - 1, position + by))];
    if (!next || next === selectedRow) return;
    show(next);
    document.getElementById(`q-${next.pool}-${next.id}`)?.scrollIntoView({ block: "nearest" });
  }

  // The list beside the question, shown or hidden as it was left on this computer.
  // The width of the list, dragged at its edge and kept on this computer; a double click gives the default back.
  const LIST_WIDTH = 340;
  let listWidth = $state(readListWidth());
  let split = $state(null);
  function readListWidth() {
    try {
      const saved = Number(localStorage.getItem("markwise-question-list-width"));
      return saved >= 240 ? saved : LIST_WIDTH;
    } catch {
      return LIST_WIDTH;
    }
  }
  function keepListWidth(width) {
    const most = split ? Math.max(240, split.getBoundingClientRect().width - 380) : 900;
    listWidth = Math.round(Math.max(240, Math.min(most, width)));
    try {
      localStorage.setItem("markwise-question-list-width", String(listWidth));
    } catch {
      /* no storage: the width is simply not kept */
    }
  }
  function dragEdge(event) {
    if (event.button !== 0) return;
    event.preventDefault();
    const start = event.clientX;
    const from = listWidth;
    const edge = event.currentTarget;
    try {
      edge.setPointerCapture(event.pointerId); // the drag goes on when the pointer leaves the narrow edge
    } catch {
      /* no pointer to capture: moves over the edge still count */
    }
    document.body.classList.add("resizing");
    const move = (e) => keepListWidth(from + e.clientX - start);
    const stop = () => {
      edge.removeEventListener("pointermove", move);
      edge.removeEventListener("pointerup", stop);
      document.body.classList.remove("resizing");
    };
    edge.addEventListener("pointermove", move);
    edge.addEventListener("pointerup", stop);
  }
  function edgeKey(event) {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      keepListWidth(listWidth + (event.key === "ArrowLeft" ? -24 : 24));
    }
  }

  let listOpen = $state(readListOpen());
  function readListOpen() {
    try {
      return localStorage.getItem("markwise-question-list") !== "closed";
    } catch {
      return true;
    }
  }
  $effect(() => {
    try {
      localStorage.setItem("markwise-question-list", listOpen ? "open" : "closed");
    } catch {
      /* no storage: the choice is simply not kept */
    }
  });
  // Without the list there is always a question to see.
  $effect(() => {
    if (!listOpen && !selectedRow && order.length) untrack(() => show(order[0]));
  });

  // Up and down move through the list while the search field or the list has the focus; Alt with left and right,
  // or Page Up and Down, page through the questions from anywhere but a text field.
  function onkeydown(event) {
    if (route.path === "/questions" && !editing && !event.target.closest?.("textarea, input, select")
      && ((event.altKey && ["ArrowLeft", "ArrowRight"].includes(event.key)) || ["PageUp", "PageDown"].includes(event.key))) {
      event.preventDefault();
      step(event.key === "ArrowLeft" || event.key === "PageUp" ? -1 : 1);
      return;
    }
    if (route.path !== "/questions" || editing || !["ArrowDown", "ArrowUp"].includes(event.key) || event.target.closest?.("select, .preview")) return;
    if (!shown.length) return;
    event.preventDefault();
    const index = selectedRow ? order.indexOf(selectedRow) : -1;
    const next = order[Math.max(0, Math.min(order.length - 1, index + (event.key === "ArrowDown" ? 1 : -1)))];
    show(next);
    document.getElementById(`q-${next.pool}-${next.id}`)?.scrollIntoView({ block: "nearest" });
  }

  // The practice questions of the pool being edited, for the choice "exam variant of".
  const practice = $derived(editing ? questions.filter((q) => q.pool === editing.pool && q.public && !q.variant_of) : []);

  async function edit() {
    editing = await call("get_question", detail.pool, detail.id);
  }

  function created(fresh) {
    showToast(t("newQ.created", { id: fresh.id }));
    selected = { pool: fresh.pool, id: fresh.id };
    editing = fresh;
    load();
  }

  function closeEditor() {
    editing = null; // what was saved is being read again already (onsaved)
  }

  // A step of a question's life, from the preview: release, withdraw, variant, retire, restore, delete.
  let me = $state("");
  call("whoami").then((name) => (me = name)).catch(() => {});

  async function act(name) {
    const { pool, id } = detail;
    if (name === "retire" && !(await ask({ title: t("life.retireTitle", { id }), message: t("life.confirmRetire", { id }), action: t("life.retire") }))) return;
    // Deleting a question that has variants asks what becomes of them: deleted too, or questions of their own.
    const variants = selectedRow?.variants ?? [];
    let withVariants = null;
    if (name === "delete" && variants.length && detail.data.status === "draft") {
      const n = variants.length;
      withVariants = await ask({
        title: t("life.deleteTitle", { id }),
        message: t(n === 1 ? "life.deleteWithVariant" : "life.deleteWithVariants", { id, n, ids: variants.join(", ") }),
        choices: [
          { value: "detach", label: t("life.keepVariants") },
          { value: "delete", label: t(n === 1 ? "life.deleteVariant" : "life.deleteVariants"), danger: true },
        ],
      });
      if (!withVariants) return;
    } else if (name === "delete" && !(await ask({ title: t("life.deleteTitle", { id }), message: t("life.confirmDelete", { id }), action: t("life.delete"), danger: true }))) return;
    try {
      if (name === "delete") {
        const result = await call("delete_question", pool, id, withVariants);
        const done = t(result.outcome === "deleted" ? "life.deleted" : "life.retiredToast", { id });
        const detached = result.variants.filter((v) => v.new_id).map((v) => v.new_id);
        showToast(detached.length ? t("life.variantsDetached", { done, ids: detached.join(", ") })
          : result.variants.length ? t("life.variantsDeleted", { done, n: result.variants.length }) : done);
        // Out of the list at once; reading the pools again takes a moment.
        dropQuestions(modulePath, pool, [id, ...result.variants.map((v) => v.id)]);
        selected = null;
        detail = null;
        load();
        return;
      }
      const method = { release: "release_question", withdraw: "withdraw_release", variant: "create_variant",
        retire: "retire_question", restore: "restore_question" }[name];
      const result = await call(method, pool, id);
      load();
      if (name === "variant") {
        selected = { pool: result.pool, id: result.id };
        editing = result;
        showToast(t("life.variantCreated", { id: result.id }));
      } else {
        detail = result;
        showToast(t(`life.${name}Toast`, { id }));
      }
    } catch (err) {
      showToast(errorText(err));
    }
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
          <button class="btn primary" onclick={() => { newPreset = { pool: filter.pool.length === 1 ? filter.pool[0] : "", concept: filter.concept.length === 1 ? filter.concept[0] : "" }; newOpen = true; }}><Icon name="plus" />{t("q.new")}</button>
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
      <QuestionEditor question={editing} {practice} onclose={closeEditor} onsaved={() => load()}
        draft={drafts.get(draftKey(editing))}
        ondraft={(d) => (d ? drafts.set(draftKey(editing), d) : drafts.delete(draftKey(editing)))} />
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
          <MultiSelect bind:selected={filter.pool} label={t("q.meta.pool")} allLabel={t("q.all.pools")}
            options={pools.map((p) => ({ value: p.path, label: p.name }))} />
        {/if}
        <MultiSelect bind:selected={filter.concept} label={t("q.meta.concept")} allLabel={t("q.all.concepts")}
          options={concepts.map(([id, name]) => ({ value: id, label: name }))} />
        <MultiSelect bind:selected={filter.level} label={t("q.meta.level")} allLabel={t("q.all.levels")}
          options={["remember", "understand", "apply"].map((v) => ({ value: v, label: t(`level.${v}`) }))} />
        <MultiSelect bind:selected={filter.status} label={t("q.meta.status")} allLabel={t("q.all.status")}
          options={["draft", "reviewed", "piloted", "retired"].map((v) => ({ value: v, label: t(`status.${v}`) }))} />
        <MultiSelect bind:selected={filter.type} label={t("stats.type")} allLabel={t("q.all.types")}
          options={["single", "multiple", "free_text"].map((v) => ({ value: v, label: t(`type.${v}`) }))} />
        <MultiSelect bind:selected={filter.use} label={t("q.meta.use")} allLabel={t("q.all.use")}
          options={[{ value: "practice", label: t("use.practice") }, { value: "exam", label: t("use.exam") }]} />
        <MultiSelect bind:selected={filter.findings} label={t("q.findings")} allLabel={t("q.all.findings")}
          options={[{ value: "errors", label: t("q.findings.errors") }, { value: "warnings", label: t("q.findings.warnings") }, { value: "none", label: t("q.findings.none") }]} />
        <MultiSelect bind:selected={filter.time} label={t("edit.time")} allLabel={t("q.all.times")}
          options={TIME_BUCKETS.map((v) => ({ value: v, label: bucketLabel(v, t) }))} />
      </div>
      <div class="q-count">
        <span>{t("q.count", { shown: shown.length, total: questions.length })}</span>
        {#if filtered}
          <button class="icon-btn small-icon" title={t("q.reset")} aria-label={t("q.reset")} onclick={() => (filter = normalized({}))}><Icon name="filter-off" /></button>
        {/if}
        {#if withVariants.length}
          <button class="icon-btn small-icon" title={t(allFolded ? "q.unfoldAll" : "q.foldAll")} aria-label={t(allFolded ? "q.unfoldAll" : "q.foldAll")}
            onclick={toggleAllVariants}><Icon name={allFolded ? "unfold" : "fold"} /></button>
        {/if}
        <button class="icon-btn small-icon" class:on={listOpen} aria-pressed={listOpen} title={t(listOpen ? "q.listHide" : "q.listShow")}
          aria-label={t(listOpen ? "q.listHide" : "q.listShow")} onclick={() => (listOpen = !listOpen)}><Icon name="panel" /></button>
        <button class="icon-btn small-icon" class:on={statsOpen} aria-pressed={statsOpen} title={t(statsOpen ? "stats.hide" : "stats.show")}
          aria-label={t(statsOpen ? "stats.hide" : "stats.show")} onclick={() => (statsOpen = !statsOpen)}><Icon name="chart" /></button>
        <label class="sort">
          <span>{t("sort.label")}</span>
          <select class="select select-small" bind:value={sort}>
            {#each Object.keys(SORTS) as key}<option value={key}>{t(`sort.${key}`)}</option>{/each}
          </select>
        </label>
      </div>
    </div>

    {#if statsOpen && questions.length}<QuestionStats rows={shown} bind:filter />{/if}

    <div class="q-split" class:solo={!listOpen} bind:this={split}
      style:grid-template-columns={listOpen ? `${listWidth}px minmax(0, 1fr)` : null}>
      {#if listOpen}
        <div class="pane-edge" role="separator" aria-orientation="vertical" aria-label={t("q.listWidth")} title={t("q.listWidth")}
          aria-valuenow={listWidth} tabindex="0" style:left="{listWidth - 3}px"
          onpointerdown={dragEdge} ondblclick={() => keepListWidth(LIST_WIDTH)} onkeydown={edgeKey}></div>
      {/if}
      <div class="q-list-pane" role="listbox" hidden={!listOpen} aria-label={t("questions.title")} bind:this={listPane} onscroll={onListScroll}>
        {#if loading && questions.length === 0}
          <p class="muted pad">{t("q.loading")}</p>
        {:else if shown.length === 0}
          <p class="muted pad">{t("q.noMatch")}</p>
        {/if}
        {#each listed as { q, child, orphan, kids, folded } (q.pool + q.id)}
          <div class="q-row-wrap">
          <button id={`q-${q.pool}-${q.id}`} class="q-row" class:variant-row={child} class:retired={q.status === "retired"} class:on={selectedRow === q} role="option" aria-selected={selectedRow === q} onclick={() => show(q)}>
            <span class="q-row-head">
              {#if child}<span class="variant-branch" aria-hidden="true"></span>{/if}
              <span class="type-icon" title={t(`type.${q.type}`)} aria-label={t(`type.${q.type}`)}><Icon name={TYPE_ICONS[q.type] ?? "questions"} /></span>
              <span class="qid">{q.id}</span>
              {#if child}<span class="q-concept">{t("q.variantLabel")}</span>
              {:else if orphan}<span class="q-concept">{t("q.variantOf", { id: q.variant_of })}</span>
              {:else}<span class="q-concept">{q.concept_name}</span>{/if}
              {#if !child && q.variants.length}<span class="tag variant-count">{t(q.variants.length === 1 ? "q.variantCount1" : "q.variantCount", { n: q.variants.length })}</span>{/if}
              {#if q.errors}<span class="tag red"><i class="dot"></i>{q.errors} {t("sev.error")}</span>
              {:else if q.warnings}<span class="tag warn"><i class="dot"></i>{t("sev.warning")}</span>{/if}
              {#if q.status === "reviewed"}<span class="status-mark" title={t("status.reviewed")}><Icon name="check" /></span>{/if}
              {#if q.status === "retired"}<span class="tag">{t("status.retired")}</span>{/if}
              {#if q.exam}<span class="tag">{q.public ? t("use.both") : t("use.exam")}</span>{/if}
            </span>
            <span class="q-stem">{q.unreadable ? t("q.unreadable") : q.stem}</span>
          </button>
          {#if kids}
            <button class="variant-toggle" class:folded aria-expanded={!folded} title={t(folded ? "q.unfold" : "q.fold", { n: kids })}
              aria-label={t(folded ? "q.unfold" : "q.fold", { n: kids })} onclick={() => toggleVariants(q)}><Icon name="chevron" /></button>
          {/if}
          </div>
        {/each}
      </div>
      <div class="q-preview-pane">
        {#if detail && selectedRow}
          <div class="sheet-nav">
            <button class="icon-btn small-icon" title={t("sheet.prev")} aria-label={t("sheet.prev")} disabled={position <= 0} onclick={() => step(-1)}><Icon name="back" /></button>
            <span>{t("sheet.position", { n: position + 1, total: order.length })}</span>
            <button class="icon-btn small-icon flip" title={t("sheet.next")} aria-label={t("sheet.next")} disabled={position >= order.length - 1} onclick={() => step(1)}><Icon name="back" /></button>
            {#if saving}<span class="hint">{t("sheet.saving")}</span>{/if}
          </div>
          <QuestionPreview question={detail} variants={selectedRow.variants} onopen={openFile} onedit={edit} onaction={act} {me}
            editable onchange={saveFields} />
        {:else}
          <div class="empty quiet"><p>{t("q.select")}</p></div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<NewQuestionDialog bind:open={newOpen} {pools} preset={newPreset} oncreated={created} />
