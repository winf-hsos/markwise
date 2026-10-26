<script>
  import { untrack } from "svelte";
  import Icon from "../components/Icon.svelte";
  import MultiSelect from "../components/MultiSelect.svelte";
  import NewExamDialog from "../components/NewExamDialog.svelte";
  import PrintExamDialog from "../components/PrintExamDialog.svelte";
  import { call } from "../lib/api.js";
  import { errorText, findingText, t } from "../lib/i18n.svelte.js";
  import { formatDate, formatTime, formatTotal } from "../lib/time.js";
  import { app, showToast } from "../lib/state.svelte.js";
  import { drafts, recall, remember } from "../lib/viewstate.svelte.js";
  import { ensureQuestions, questionsOf, refreshQuestions } from "../lib/questions.svelte.js";
  import QuestionEditor from "../components/QuestionEditor.svelte";
  import ExamItem from "../components/ExamItem.svelte";

  // The exams of the current module, and putting one together by hand: its questions in order, with points.
  const modulePath = $derived(app.settings?.current_module || "");

  let exams = $state([]);
  let loading = $state(false);
  let current = $state(null); // the exam being put together, as get_exam answers
  // Every question of the module's pools, as rows of the question list, from memory (lib/questions.svelte.js).
  const store = $derived(questionsOf(modulePath));
  const pools = $derived(store.pools);
  const questions = $derived(store.questions);
  let editing = $state(null); // the detail of a question opened from the exam, in the editor
  let newOpen = $state(false);
  let printOpen = $state(false);

  $effect(() => {
    modulePath;
    untrack(() => start());
  });

  async function start() {
    current = null;
    editing = null;
    exams = [];
    if (!modulePath) return;
    loading = true;
    try {
      exams = await call("list_exams", modulePath);
      const kept = recall("exams", modulePath);
      if (kept.open && exams.some((e) => e.path === kept.open)) await openExam(kept.open);
    } catch (err) {
      showToast(errorText(err));
    } finally {
      loading = false;
    }
  }

  const loadQuestions = () => ensureQuestions(modulePath);

  async function openExam(path) {
    try {
      const [exam] = await Promise.all([call("get_exam", path), loadQuestions()]);
      current = exam;
      remember("exams", modulePath, { open: path });
    } catch (err) {
      showToast(errorText(err));
    }
  }

  function closeExam() {
    current = null;
    remember("exams", modulePath, { open: null });
    call("list_exams", modulePath).then((list) => (exams = list)).catch(() => {});
  }

  function created(exam) {
    exams = [exam, ...exams];
    openExam(exam.path);
    showToast(t("exams.created", { title: exam.title }));
  }

  const languages = $derived([...new Set(pools.filter((p) => p.exists).flatMap((p) => p.languages ?? []))]);
  const key = (pool, id) => `${pool}\n${id}`;
  const rows = $derived(new Map(questions.map((q) => [key(q.pool, q.id), q])));

  // --- the exam's questions ------------------------------------------------------------------

  const entries = $derived((current?.entries ?? []).map((e) => ({ ...e, row: rows.get(key(e.pool, e.id)) })));
  const inExam = $derived(new Set((current?.entries ?? []).map((e) => key(e.pool, e.id))));
  const seconds = $derived(entries.reduce((sum, e) => sum + (e.row?.time_seconds ?? 0), 0));
  const withoutTime = $derived(entries.filter((e) => e.row && e.row.time_seconds == null).length);
  const points = $derived(entries.reduce((sum, e) => sum + Number(e.points || 0), 0));
  const findingsFor = (id) => (current?.findings ?? []).filter((f) => f.question === id && f.severity !== "note");
  const examFindings = $derived((current?.findings ?? []).filter((f) => !f.question || f.severity === "note"));

  let saving = null;
  async function save(fields) {
    try {
      const answer = await call("update_exam", current.path, fields);
      if (answer.path !== current.path) remember("exams", modulePath, { open: answer.path }); // the folder moved
      current = answer;
      return true;
    } catch (err) {
      showToast(errorText(err));
      return false;
    }
  }

  const plainEntries = (list) => list.map(({ pool, id, points }) => ({ pool, id, points: Number(points) }));
  const suggest = (s) => (s ? Math.max(1, Math.round((s / 60) * 2) / 2) : 1);

  function add(row) {
    current.entries = [...current.entries, { pool: row.pool, id: row.id, points: suggest(row.time_seconds) }];
    save({ entries: plainEntries(current.entries) });
  }

  function removeRow(row) {
    removeAt(current.entries.findIndex((e) => e.pool === row.pool && e.id === row.id));
  }

  function removeAt(index) {
    current.entries = current.entries.filter((_, i) => i !== index);
    save({ entries: plainEntries(current.entries) });
  }

  function move(index, step) {
    const list = [...current.entries];
    const target = index + step;
    if (target < 0 || target >= list.length) return;
    [list[index], list[target]] = [list[target], list[index]];
    current.entries = list;
    save({ entries: plainEntries(list) });
  }

  function setPoints(index, value) {
    current.entries[index].points = value;
    clearTimeout(saving);
    saving = setTimeout(() => save({ entries: plainEntries(current.entries) }), 400);
  }

  // `input` gets its saved value back when the change is refused, say a title another exam has on that date.
  async function saveSetting(name, value, input) {
    if (!(await save({ [name]: value })) && input) input.value = current[name];
  }

  // --- the questions as the booklet shows them ----------------------------------------------------------

  // Read once per question and kept; read anew for another language or after the questions changed. Until the
  // new readings are there, the old ones stay on screen.
  let rendered = $state({}); // key(pool, id) -> item from exam_items
  let printWords = $state(null); // the booklet's words in the exam's language
  let renderedFor = "";
  $effect(() => {
    const lang = current?.language;
    const version = store.version;
    const refs = (current?.entries ?? []).map((e) => ({ pool: e.pool, id: e.id }));
    untrack(() => {
      if (!current) return;
      const stamp = `${current.path}|${lang}|${version}`;
      const fresh = stamp !== renderedFor;
      renderedFor = stamp;
      const wanted = fresh ? refs : refs.filter((r) => !(key(r.pool, r.id) in rendered));
      if (!wanted.length) return;
      call("exam_items", lang, wanted)
        .then((answer) => {
          if (renderedFor !== stamp) return;
          printWords = answer.words;
          const next = fresh ? {} : { ...rendered };
          for (const item of answer.items) next[key(item.pool, item.id)] = item;
          rendered = next;
        })
        .catch((err) => showToast(errorText(err)));
    });
  });

  // --- editing a question without leaving the exam ----------------------------------------------------

  async function editQuestion(pool, id) {
    try {
      editing = await call("get_question", pool, id);
    } catch (err) {
      showToast(errorText(err));
    }
  }

  // The practice questions of the pool being edited, for the choice "exam variant of".
  const practice = $derived(editing ? questions.filter((q) => q.pool === editing.pool && q.public && !q.variant_of) : []);
  const draftKey = (q) => `${q.pool}\n${q.id}`;

  // Whenever the questions were read again, here or on another page, the exam checks itself anew: a time
  // added or an error fixed changes what it says.
  $effect(() => {
    store.version;
    untrack(() => {
      if (current && store.loaded) call("get_exam", current.path).then((exam) => (current = exam)).catch(() => {});
    });
  });

  // --- choosing questions ---------------------------------------------------------------------

  let search = $state("");
  let filter = $state({ pool: [], concept: [], level: [], type: [], use: ["exam"] });
  const words = $derived(search.toLowerCase().split(/\s+/).filter(Boolean));
  const anyOf = (chosen, test) => !chosen.length || chosen.some(test);
  const candidates = $derived(
    questions.filter(
      (q) =>
        q.status !== "retired" &&
        anyOf(filter.pool, (v) => q.pool === v) &&
        anyOf(filter.concept, (v) => q.concept === v) &&
        anyOf(filter.level, (v) => q.level === v) &&
        anyOf(filter.type, (v) => q.type === v) &&
        anyOf(filter.use, (v) => (v === "practice" ? q.public : q.exam)) &&
        words.every((w) => q.search.includes(w)),
    ),
  );
  const concepts = $derived(
    [...new Map(questions.filter((q) => anyOf(filter.pool, (v) => q.pool === v)).map((q) => [q.concept, q.concept_name])).entries()]
      .sort((a, b) => a[1].localeCompare(b[1])),
  );
  const TYPE_ICONS = { single: "single", multiple: "multiple", free_text: "freetext" };
</script>

<div class="page page-wide">
  {#if !modulePath}
    <div class="page-head"><div><h1>{t("exams.title")}</h1><p>{t("exams.lead")}</p></div></div>
    <div class="empty"><div class="mark"><Icon name="exams" /></div><p>{t("exams.noModule")}</p></div>
  {:else if current}
    {#if editing}
      {#key editing.pool + editing.id}
        <QuestionEditor question={editing} {practice} back={t("exams.backToExam")} onclose={() => (editing = null)}
          onsaved={() => refreshQuestions(modulePath)} draft={drafts.get(draftKey(editing))}
          ondraft={(d) => (d ? drafts.set(draftKey(editing), d) : drafts.delete(draftKey(editing)))} />
      {/key}
    {/if}
    <!-- Hidden, not closed, while a question is being edited: search, filters and scroll positions stay. -->
    <div class="exam-shell" style:display={editing ? "none" : null}>
      <header class="editor-bar">
        <button class="btn ghost" onclick={closeExam}><Icon name="back" />{t("exams.back")}</button>
        <b class="exam-title">{current.title}</b>
        <span class="tag">{formatDate(current.date)}</span>
        <span class="tag">{current.semester}</span>
        <span class="spacer"></span>
        <button class="btn ghost" onclick={() => call("reveal", current.path).catch((err) => showToast(errorText(err)))}><Icon name="folder" />{t("modules.reveal")}</button>
        <button class="btn primary" onclick={() => (printOpen = true)}><Icon name="print" />{t("exams.print")}</button>
      </header>
      <PrintExamDialog bind:open={printOpen} exam={current} onprinted={(exam) => (current = exam)} />

      <div class="exam-settings">
        <label class="field" title={t("exams.renameHint")}><span>{t("exams.examTitle")}</span>
          <input class="input" value={current.title} onchange={(e) => saveSetting("title", e.currentTarget.value, e.currentTarget)} /></label>
        <label class="field" title={t("exams.renameHint")}><span>{t("exams.date")}</span>
          <input class="input" type="date" value={current.date} onchange={(e) => saveSetting("date", e.currentTarget.value, e.currentTarget)} /></label>
        {#if languages.length > 1}
          <div class="field">
            <span>{t("exams.language")}</span>
            <div class="seg" role="group">
              {#each languages as l}<button type="button" class:on={current.language === l} onclick={() => saveSetting("language", l)}>{l === "de" ? "Deutsch" : "English"}</button>{/each}
            </div>
          </div>
        {/if}
        <div class="field">
          <span>{t("exams.answers")}</span>
          <div class="seg" role="group">
            {#each ["sheet", "inline"] as mode}
              <button type="button" class:on={current.answers === mode} title={t(`exams.answers.${mode}Hint`)} onclick={() => saveSetting("answers", mode)}>{t(`exams.answers.${mode}`)}</button>
            {/each}
          </div>
        </div>
        <label class="field grow"><span>{t("exams.examiners")}</span>
          <input class="input" value={current.examiners.join(", ")} placeholder={t("exams.examinersPlaceholder")}
            onchange={(e) => saveSetting("examiners", e.currentTarget.value.split(","))} /></label>
      </div>

      <div class="exam-totals">
        <span><b>{entries.length}</b> {t(entries.length === 1 ? "exams.question" : "exams.questions")}</span>
        <span><b>{points.toLocaleString(undefined, { maximumFractionDigits: 1 })}</b> {t("exams.points")}</span>
        <span><b>{formatTotal(seconds)}</b> {t("exams.time")}</span>
        {#if withoutTime}<span class="warn-text">{t("stats.withoutTime", { n: withoutTime })}</span>{/if}
        {#each examFindings as f}<span class="tag {f.severity === 'error' ? 'red' : f.severity === 'warning' ? 'warn' : ''}">{findingText(f)}</span>{/each}
      </div>

      <div class="exam-split">
        <section class="exam-picker" aria-label={t("exams.choose")}>
          <h3 class="pane-title">{t("exams.choose")}</h3>
          <div class="q-tools">
            <div class="search">
              <Icon name="search" />
              <input class="input" type="search" bind:value={search} placeholder={t("q.search")} aria-label={t("q.search")} />
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
              <MultiSelect bind:selected={filter.type} label={t("stats.type")} allLabel={t("q.all.types")}
                options={["single", "multiple", "free_text"].map((v) => ({ value: v, label: t(`type.${v}`) }))} />
              <MultiSelect bind:selected={filter.use} label={t("q.meta.use")} allLabel={t("q.all.use")}
                options={[{ value: "practice", label: t("use.practice") }, { value: "exam", label: t("use.exam") }]} />
            </div>
            <span class="hint">{t("q.count", { shown: candidates.length, total: questions.length })}</span>
          </div>
          <div class="picker-list">
            {#each candidates as q (q.pool + q.id)}
              {@const added = inExam.has(key(q.pool, q.id))}
              <div class="picker-row" class:added title={added ? t("exams.inExam") : null}>
                <div class="entry-main">
                  <div class="q-row-head">
                    <span class="type-icon"><Icon name={TYPE_ICONS[q.type] ?? "questions"} /></span>
                    <span class="qid">{q.id}</span>
                    <span class="q-concept">{q.variant_of ? t("q.variantOf", { id: q.variant_of }) : q.concept_name}</span>
                    {#if q.errors}<span class="tag red"><i class="dot"></i>{q.errors} {t("sev.error")}</span>{/if}
                    {#if q.time_seconds}<span class="tag">{formatTime(q.time_seconds)}</span>{/if}
                  </div>
                  <span class="q-stem">{q.stem}</span>
                </div>
                <button class="icon-btn small-icon" title={t("exams.edit")} aria-label={t("exams.edit")} onclick={() => editQuestion(q.pool, q.id)}><Icon name="edit" /></button>
                {#if added}
                  <button class="btn btn-small" onclick={() => removeRow(q)}><Icon name="remove" />{t("exams.take")}</button>
                {:else}
                  <button class="btn btn-small" onclick={() => add(q)}><Icon name="plus" />{t("exams.add")}</button>
                {/if}
              </div>
            {/each}
          </div>
        </section>
        <section class="exam-list" aria-label={t("exams.content")}>
          <h3 class="pane-title">{t("exams.content")}</h3>
          {#if !entries.length}<p class="muted pad">{t("exams.emptyExam")}</p>{/if}
          <ol class="exam-entries">
            {#each entries as entry, i (entry.pool + entry.id)}
              {@const item = rendered[key(entry.pool, entry.id)]}
              <li class="exam-entry">
                <div class="entry-bar">
                  <span class="type-icon"><Icon name={TYPE_ICONS[entry.row?.type] ?? "questions"} /></span>
                  <span class="qid">{entry.id}</span>
                  <span class="q-concept">{entry.row?.concept_name ?? ""}</span>
                  {#if entry.row?.level}<span class="tag">{t(`level.${entry.row.level}`)}</span>{/if}
                  {#if entry.row?.time_seconds}<span class="tag">{formatTime(entry.row.time_seconds)}</span>
                  {:else if entry.row}<span class="tag warn">{t("exams.noTime")}</span>{/if}
                  <label class="entry-points" title={t("exams.pointsHint")}>
                    <input class="input" type="number" min="0.5" step="0.5" value={entry.points}
                      oninput={(e) => setPoints(i, Number(e.currentTarget.value))} aria-label={t("exams.points")} />
                    <span>{t("exams.pointsShort")}</span>
                  </label>
                  <span class="entry-tools">
                    <button class="icon-btn small-icon" title={t("exams.edit")} aria-label={t("exams.edit")} disabled={!entry.row} onclick={() => editQuestion(entry.pool, entry.id)}><Icon name="edit" /></button>
                    <button class="icon-btn small-icon up" title={t("exams.up")} aria-label={t("exams.up")} disabled={i === 0} onclick={() => move(i, -1)}><Icon name="chevron" /></button>
                    <button class="icon-btn small-icon" title={t("exams.down")} aria-label={t("exams.down")} disabled={i === entries.length - 1} onclick={() => move(i, 1)}><Icon name="chevron" /></button>
                    <button class="icon-btn small-icon danger" title={t("exams.remove")} aria-label={t("exams.remove")} onclick={() => removeAt(i)}><Icon name="remove" /></button>
                  </span>
                </div>
                {#each findingsFor(entry.id) as f}<span class="entry-finding {f.severity}">{findingText(f)}</span>{/each}
                {#if !item || !printWords}
                  <div class="booklet-item waiting">{entry.row?.stem ?? ""}</div>
                {:else if item.missing}
                  <div class="booklet-item waiting">{t("exams.missing")}</div>
                {:else}
                  <ExamItem {item} number={i + 1} points={Number(entry.points)} words={printWords} />
                {/if}
              </li>
            {/each}
          </ol>
        </section>
      </div>
    </div>
  {:else}
    <div class="page-head">
      <div><h1>{t("exams.title")}</h1><p>{t("exams.lead")}</p></div>
      <div class="actions">
        <button class="btn primary" onclick={async () => { if (!pools.length) await loadQuestions(); newOpen = true; }}><Icon name="plus" />{t("exams.new")}</button>
      </div>
    </div>
    {#if loading}
      <p class="muted">{t("q.loading")}</p>
    {:else if !exams.length}
      <div class="empty"><div class="mark"><Icon name="exams" /></div><p>{t("exams.none")}</p></div>
    {:else}
      <div class="rows">
        {#each exams as exam (exam.path)}
          <button class="row-item exam-row" onclick={() => openExam(exam.path)}>
            <div class="text">
              <b>{exam.title}</b>
              <span class="hint">{formatDate(exam.date)} · {exam.semester} · {exam.language === "de" ? "Deutsch" : "English"} · {t(`exams.answers.${exam.answers}`)}</span>
            </div>
            <span class="muted">{t(exam.questions === 1 ? "exams.countOne" : "exams.count", { n: exam.questions, points: exam.points.toLocaleString(undefined, { maximumFractionDigits: 1 }) })}</span>
          </button>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<NewExamDialog bind:open={newOpen} module={modulePath} languages={languages.length ? languages : ["de", "en"]} oncreated={created} />
