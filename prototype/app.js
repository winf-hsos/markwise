// Markwise click prototype: every view with sample data, no real logic.
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);

// --- icons (simple strokes, 24px grid; the gear follows Lucide, ISC licence) ----
const ICON = {
  panel: '<rect x="3.5" y="4.5" width="17" height="15" rx="2" fill="none" stroke-width="1.8"/><path d="M9 4.5v15" fill="none" stroke-width="1.8"/>',
  modules: '<path d="M3.5 7.5 12 3l8.5 4.5L12 12 3.5 7.5Z" fill="none" stroke-width="1.7" stroke-linejoin="round"/><path d="M3.5 12 12 16.5 20.5 12M3.5 16.5 12 21l8.5-4.5" fill="none" stroke-width="1.7" stroke-linejoin="round"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" fill="none" stroke-width="1.7" stroke-linejoin="round"/>',
  questions: '<path d="M4 5h16M4 10h16M4 15h10M4 20h7" fill="none" stroke-width="1.8" stroke-linecap="round"/>',
  exams: '<rect x="5" y="3" width="14" height="18" rx="2" fill="none" stroke-width="1.8"/><path d="M9 8h6M9 12h6M9 16h3" fill="none" stroke-width="1.8" stroke-linecap="round"/>',
  settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" fill="none" stroke-width="1.7" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" fill="none" stroke-width="1.7"/>',
  search: '<circle cx="11" cy="11" r="6.5" fill="none" stroke-width="1.8"/><path d="m16 16 4.5 4.5" fill="none" stroke-width="1.8" stroke-linecap="round"/>',
  plus: '<path d="M12 5v14M5 12h14" fill="none" stroke-width="1.8" stroke-linecap="round"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
  warn: '<path d="M12 4 2.8 19.5h18.4L12 4Z" fill="none" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 10v4.5M12 17.2v.1" fill="none" stroke-width="1.8" stroke-linecap="round"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
  print: '<path d="M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z" fill="none" stroke-width="1.8" stroke-linejoin="round"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6" fill="none" stroke-width="1.8" stroke-linecap="round"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke-width="1.8"/><path d="M8 11V8a4 4 0 0 1 8 0v3" fill="none" stroke-width="1.8"/>',
  download: '<path d="M12 4v12M7 11l5 5 5-5M4 20h16" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
};
const icon = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON[name]}</svg>`;

// --- sample data (question texts from the LiFi pool, people are invented) ---------
const CONCEPTS = [
  ["algorithms-and-programs", "Algorithms and Programs", 15],
  ["problem-decomposition", "Cutting Problems", 13],
  ["input-processing-output", "Solving Problems", 12],
  ["measurement-and-experiments", "Measuring and Experimenting", 14],
  ["analog-and-digital", "Analog and Digital", 14],
  ["symbols-and-information", "Symbols and Information", 13],
  ["signal-and-noise", "Signal and Noise", 15],
  ["number-systems", "Number Systems", 14],
];

const QUESTIONS = [
  { id: "aa-014", type: "Einfachwahl", level: "anwenden", status: "geprüft",
    stem: "Was zeigt die LED, wenn dieses Programm läuft?",
    code: "led.set_color(255, 0, 0)\nled.set_color(0, 0, 255)\ntime.sleep(1)",
    options: [
      ["Eine Sekunde Rot, dann Blau: Das time.sleep(1) gehört erkennbar zur roten Phase.", false, "Die Maschine ordnet nichts um; die Pause steht nach beiden Farbwechseln."],
      ["Eine Sekunde Blau, dann Rot: Die erste Zeile wird danach nachgeholt.", false, "Nachgeholt wird nichts; jede Zeile läuft genau einmal."],
      ["Rot nur für einen Sekundenbruchteil, dann eine Sekunde Blau.", true, "Rot wird sofort überschrieben, erst dann wartet die Maschine."],
      ["Das Programm startet nicht, weil time.sleep(1) als letzte Zeile nicht erlaubt ist.", false, "Jede Zeile ist für sich gültig, in jeder Reihenfolge."],
    ] },
  { id: "aa-007", type: "Einfachwahl", level: "anwenden", status: "geprüft",
    stem: "Wie lange läuft dieses Programm ungefähr, und was zeigt die LED?" },
  { id: "aa-011", type: "Einfachwahl", level: "anwenden", status: "Entwurf",
    stem: "Wann endet dieses Programm?" },
  { id: "aa-016", type: "Freitext", level: "verstehen", status: "Entwurf", points: 4,
    stem: "Erklären Sie an einem eigenen Beispiel, warum zwei korrekte Verfahren sich im Aufwand stark unterscheiden können." },
  { id: "aa-005", type: "Einfachwahl", level: "erinnern", status: "geprüft",
    stem: "Welche Rolle spielt der Teil (255, 0, 0) in der Zeile led.set_color(255, 0, 0)?" },
  { id: "aa-008", type: "Mehrfachwahl", level: "anwenden", status: "geprüft",
    stem: "Welche Aussagen über diese Schleife mit Bedingung treffen zu?" },
  { id: "aa-003", type: "Einfachwahl", level: "anwenden", status: "Entwurf",
    stem: "Was seht ihr an der LED, wenn dieses Programm läuft?" },
];

const MODULES = [
  { id: "dup", name: "Digitalisierung und Programmierung", short: "DuP", folder: "OneDrive › Lehre › Digitalisierung und Programmierung",
    exams: "OneDrive › Klausuren (privat) › DuP", questions: 246, concepts: 18, examCount: 2, last: "Klausur WS 2026/27 in Vorbereitung", po: "BPO Wirtschaftsinformatik, § 5 Abs. 3 AT" },
  { id: "ai", name: "Artificial Intelligence", short: "AI", folder: "OneDrive › Lehre › Artificial Intelligence",
    exams: "OneDrive › Klausuren (privat) › AI", questions: 132, concepts: 11, examCount: 1, last: "Fragen werden gesammelt", po: "BPO Wirtschaftsinformatik, § 5 Abs. 3 AT" },
  { id: "da", name: "Data Analytics", short: "DA", folder: "Teams › Data Analytics › Klausurfragen (geteilt)",
    exams: "OneDrive › Klausuren (privat) › DA", questions: 87, concepts: 9, examCount: 4, last: "letzte Klausur SS 2026, ausgewertet", po: "MPO Data Science, § 7 AT" },
];
let currentModule = MODULES[0];

const PEOPLE = [
  ["Albers, Jana", "1048231"], ["Brandt, Tobias", "1049120"], ["Çelik, Deniz", "1050774"],
  ["Diekmann, Lea", "1047302"], ["Engel, Marvin", "1051188"], ["Fischer, Sophie", "1049967"],
  ["Gerdes, Jonas", "1050012"], ["Hoffmann, Mila", "1048845"],
];

// --- shell ---------------------------------------------------------------------------
const navLink = (href, label, ic, active) =>
  `<a href="${href}" title="${label}" class="${active === href ? "active" : ""}">${icon(ic)}<span class="label">${label}</span></a>`;

function shell(active, content) {
  return `
  <div class="app ${navCollapsed() ? "collapsed" : ""}">
    <nav class="nav" aria-label="Hauptnavigation">
      <div class="brand">
        <svg class="brand-mark" viewBox="0 0 64 64" aria-hidden="true">
          <circle cx="32" cy="32" r="30" fill="#dff3e7"/>
          <path d="M19 33.5 28 42 46 22" fill="none" stroke="#24895a" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="brand-name">Markwise</span>
      </div>
      ${navLink("#/module", "Module", "modules", active)}
      <div class="nav-group" title="${currentModule.name}"><span class="label">${currentModule.name}</span><span class="short">${currentModule.short}</span></div>
      ${navLink("#/fragen", "Fragen", "questions", active)}
      ${navLink("#/klausuren", "Klausuren", "exams", active)}
      <div class="spacer"></div>
      ${navLink("#/einstellungen", "Einstellungen", "settings", active)}
      <button class="nav-toggle" data-toggle-nav title="Menü ein- und ausklappen (Strg+B)" aria-label="Menü ein- und ausklappen">${icon("panel")}<span class="label">Menü einklappen</span></button>
    </nav>
    <main class="main" id="main">${content}</main>
  </div>
  <div class="toast" id="toast"></div>`;
}

// the menu remembers whether it was collapsed (per viewer, not shared)
function navCollapsed() {
  try { return localStorage.getItem("markwise-nav") === "collapsed"; } catch { return false; }
}
function toggleNav() {
  const app = $(".app");
  const collapsed = app.classList.toggle("collapsed");
  try { localStorage.setItem("markwise-nav", collapsed ? "collapsed" : "open"); } catch { /* no storage, fine */ }
}

function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove("show"), 1800);
}

// --- view: questions ---------------------------------------------------------------
function typeTag(q) {
  return q.type === "Freitext" ? `<span class="tag">Freitext · ${q.points} P.</span>` : `<span class="tag">${q.type}</span>`;
}
function statusTag(q) {
  return q.status === "geprüft" ? `<span class="tag ok"><i class="dot"></i>geprüft</span>` : `<span class="tag warn"><i class="dot"></i>Entwurf</span>`;
}

function viewQuestions(sel = "aa-014") {
  const q = QUESTIONS.find((x) => x.id === sel) || QUESTIONS[0];
  const opts = q.options || QUESTIONS[0].options;
  const letters = "ABCDE";
  return `
  <div class="page">
    <div class="page-head">
      <div>
        <h1>Fragen</h1>
        <p>Fragenpool von ${currentModule.name}: ${currentModule.questions} Fragen in ${currentModule.concepts} Konzepten <span class="path">${icon("folder")}${currentModule.folder}</span></p>
      </div>
      <div class="actions">
        <button class="btn" data-toast="Import gestartet">Fragen importieren</button>
        <button class="btn primary" data-toast="Neue Frage angelegt: aa-017">${icon("plus")}Neue Frage</button>
      </div>
    </div>

    <div class="q-layout">
      <section class="panel q-list" aria-label="Fragenliste">
        <div class="list-tools">
          <div class="search">${icon("search")}<input class="input" placeholder="In Fragen suchen" aria-label="In Fragen suchen"></div>
          <div class="filter-bar">
            <select class="select" aria-label="Konzept">${CONCEPTS.map(([s, n, c]) => `<option>${n} (${c})</option>`).join("")}<option>Alle Konzepte (246)</option></select>
            <select class="select" aria-label="Typ"><option>Alle Typen</option><option>Einfachwahl</option><option>Mehrfachwahl</option><option>Freitext</option></select>
            <select class="select" aria-label="Status"><option>Jeder Status</option><option>Entwurf</option><option>geprüft</option></select>
          </div>
        </div>
        ${QUESTIONS.map((x) => `
          <a class="q-item ${x.id === q.id ? "on" : ""}" href="#/fragen/${x.id}">
            <div class="meta"><span class="id">${x.id}</span>${typeTag(x)}${statusTag(x)}</div>
            <div class="stem">${x.stem}</div>
          </a>`).join("")}
      </section>

      <section class="editor">
        <div class="editor-form panel panel-body">
          <div class="row">
            <label class="field"><span>Typ</span><select class="select"><option>${q.type}</option><option>Einfachwahl</option><option>Mehrfachwahl</option><option>Freitext</option></select></label>
            <label class="field"><span>Niveau</span><select class="select"><option>${q.level}</option><option>erinnern</option><option>verstehen</option><option>anwenden</option></select></label>
          </div>
          <div class="field"><span>Sprache</span><div class="seg" role="group"><button class="on">Deutsch</button><button>Englisch</button></div></div>
          <label class="field"><span>Frage</span><textarea class="input" rows="2">${q.stem}</textarea></label>
          <label class="field"><span>Code</span><textarea class="input mono" rows="3">${q.code || ""}</textarea></label>
          ${q.type === "Freitext" ? `
            <div class="row">
              <label class="field"><span>Höchstpunktzahl</span><input class="input" value="${q.points}"></label>
              <label class="field"><span>Halbe Punkte</span><select class="select"><option>erlaubt</option><option>nicht erlaubt</option></select></label>
              <label class="field"><span>Antwortfeld</span><select class="select"><option>12 Zeilen</option><option>halbe Seite</option></select></label>
            </div>
            <label class="field"><span>Erwartungshorizont</span><textarea class="input" rows="4">Beispiel mit zwei Verfahren für dieselbe Aufgabe (2 P.), Aufwand beider beziffert (1 P.), Wachstum mit der Problemgröße benannt (1 P.).</textarea></label>
          ` : `
          <div class="field"><span>Antworten (Haken = richtig)</span>
            ${opts.map(([text, ok, why], i) => `
              <div class="opt">
                <span class="mark ${ok ? "correct" : ""}" role="checkbox" aria-checked="${ok}" tabindex="0">${ok ? icon("check") : ""}</span>
                <div><textarea class="input" rows="2" style="width:100%">${text}</textarea><div class="why">${why}</div></div>
              </div>`).join("")}
          </div>`}
          <div class="checks">${q.type === "Freitext" ? `
            <div class="check ok">${icon("check")}Erwartungshorizont verteilt alle 4 Punkte</div>
            <div class="check warn">${icon("warn")}Englische Fassung fehlt noch</div>` : `
            <div class="check ok">${icon("check")}Vier Antworten, genau eine richtig</div>
            <div class="check ok">${icon("check")}Deutsche und englische Fassung vollständig</div>
            <div class="check warn">${icon("warn")}Antwort A ist deutlich länger als die anderen und könnte sich dadurch verraten</div>`}
          </div>
          <div class="row" style="flex:none">
            <button class="btn" data-toast="Frage gelöscht">Löschen</button>
            <span></span>
            <button class="btn" data-advice>${icon("spark")}Didaktisch prüfen</button>
            <button class="btn primary" data-toast="Gespeichert">Speichern</button>
          </div>
          <div id="advice"></div>
        </div>

        <div>
          <p class="preview-label">${icon("print")}So erscheint die Frage im Klausurheft</p>
          <div class="paper">
            <div class="q-num">Aufgabe 7</div>
            <div>${q.stem}</div>
            ${q.code ? `<pre>${q.code}</pre>` : ""}
            ${q.type === "Freitext" ? `<div style="height:220px;border:1px solid #bbb;margin-top:12px;background:repeating-linear-gradient(#fff 0 27px,#e5e5e5 27px 28px)"></div>` :
            `<ol>${opts.map(([text], i) => `<li><span class="box"></span><span><span class="letter">${letters[i]}</span>${text}</span></li>`).join("")}</ol>`}
          </div>
        </div>
      </section>
    </div>
    <p class="proto-note">Klickprototyp: Daten sind Beispiele, Schaltflächen zeigen nur, was passieren würde.</p>
  </div>`;
}

function showAdvice() {
  $("#advice").innerHTML = `
    <div class="advice">
      <p><b>Didaktische Prüfung</b> <span class="src">Vorschlag des Sprachmodells, nichts wird ohne dich geändert</span></p>
      <p>Die Frage prüft genau eine Vorstellung (die Maschine führt Zeilen der Reihe nach aus) und ist ohne die Antworten lösbar. Gut.</p>
      <p>Antwort A ist mit 87 Zeichen fast doppelt so lang wie C. Vorschlag: „Eine Sekunde Rot, dann Blau.“</p>
      <p>D ist für Leute ohne Vorwissen wenig plausibel. Stärker wäre: „Nur Blau, Rot wird übersprungen.“</p>
      <div class="row" style="margin-top:8px"><button class="btn" data-toast="Vorschlag übernommen">Vorschläge übernehmen</button><button class="btn ghost" data-close-advice>Verwerfen</button></div>
    </div>`;
}

// --- view: modules -------------------------------------------------------------------
function viewModules(editing) {
  return `
  <div class="page">
    <div class="page-head">
      <div><h1>Module</h1><p>Jedes Modul hat seinen Fragenpool und seine Klausuren in eigenen Ordnern.</p></div>
      <div class="actions">
        <button class="btn" data-toast="Ordner gewählt: das Modul erscheint in der Liste">${icon("folder")}Vorhandenen Modulordner öffnen</button>
        <a class="btn primary" href="#/module/neu">${icon("plus")}Neues Modul</a>
      </div>
    </div>
    <div class="modules-layout ${editing ? "with-form" : ""}">
      <div class="module-list">
        ${MODULES.map((m) => `
          <article class="panel module-card ${m.id === currentModule.id ? "current" : ""}">
            <div class="module-main">
              <div class="module-title"><span class="module-short">${m.short}</span><h3>${m.name}</h3></div>
              <div class="path">${icon("folder")}${m.folder}</div>
              <div class="module-facts"><span>${m.questions} Fragen</span><span>${m.examCount} ${m.examCount === 1 ? "Klausur" : "Klausuren"}</span><span>${m.last}</span></div>
            </div>
            <div class="module-actions">
              <a class="btn" href="#/module/${m.id}/einstellungen">Einstellungen</a>
              <a class="btn ${m.id === currentModule.id ? "" : "primary"}" href="#/oeffnen/${m.id}">${m.id === currentModule.id ? "Geöffnet" : "Öffnen"}</a>
            </div>
          </article>`).join("")}
      </div>
      ${editing ? moduleForm(editing === "neu" ? null : MODULES.find((m) => m.id === editing)) : ""}
    </div>
  </div>`;
}

function moduleForm(m) {
  return `
  <section class="panel module-form">
    <div class="panel-head"><h2>${m ? "Modul einrichten" : "Neues Modul"}</h2><a class="btn ghost" href="#/module">Schließen</a></div>
    <div class="panel-body" style="display:grid;gap:14px">
      <div class="row">
        <label class="field" style="flex:3"><span>Name</span><input class="input" value="${m ? m.name : ""}" placeholder="z. B. Datenbanken"></label>
        <label class="field" style="flex:1"><span>Kürzel</span><input class="input" value="${m ? m.short : ""}" placeholder="DB"></label>
      </div>
      <div class="field"><span>Modulordner (Fragenpool)</span>
        <div class="folder-pick"><span class="path">${icon("folder")}${m ? m.folder : "noch kein Ordner gewählt"}</span><button class="btn" data-toast="Ordnerauswahl von Windows öffnet sich">Ordner wählen</button></div>
        <span class="muted small">Ein geteilter Ordner (OneDrive, Teams, Netzlaufwerk) erlaubt es Kolleg:innen, am selben Pool zu arbeiten.</span>
      </div>
      <div class="field"><span>Klausurordner</span>
        <div class="folder-pick"><span class="path">${icon("folder")}${m ? m.exams : "noch kein Ordner gewählt"}</span><button class="btn" data-toast="Ordnerauswahl von Windows öffnet sich">Ordner wählen</button></div>
        <span class="muted small">Hier liegen Teilnehmende, Scans und Noten. Wähle einen Ort, auf den nur du Zugriff hast; er darf vom Modulordner getrennt sein.</span>
      </div>
      <div class="row">
        <label class="field"><span>Prüfungsordnung</span><select class="select"><option>${m ? m.po : "BPO Wirtschaftsinformatik, § 5 Abs. 3 AT"}</option><option>MPO Data Science, § 7 AT</option><option>Eigene Regeln …</option></select></label>
        <label class="field"><span>Sprachen der Fragen</span><select class="select"><option>Deutsch und Englisch</option><option>Deutsch</option><option>Englisch</option></select></label>
      </div>
      <div class="row" style="flex:none;justify-content:flex-end"><a class="btn" href="#/module">Abbrechen</a><button class="btn primary" data-toast="${m ? "Gespeichert" : "Modul angelegt"}">${m ? "Speichern" : "Modul anlegen"}</button></div>
    </div>
  </section>`;
}

// --- view: exams overview -----------------------------------------------------------
function viewExams() {
  const exams = [
    ["Klausur WS 2026/27", "Freitag 05.02.2027, 60 Minuten", "Zusammenstellen", 20, "#/klausuren/dup/zusammenstellen"],
    ["Probeklausur", "Testlauf mit Scans vom Kopierer", "Zweifelsfälle", 75, "#/klausuren/dup/zweifelsfaelle"],
  ];
  return `
  <div class="page">
    <div class="page-head">
      <div><h1>Klausuren</h1><p>${currentModule.name}: jede Klausur ist ein eigener Ordner mit allem, was zu ihr gehört <span class="path">${icon("folder")}${currentModule.exams}</span></p></div>
      <div class="actions"><button class="btn primary" data-toast="Neue Klausur angelegt">${icon("plus")}Neue Klausur</button></div>
    </div>
    <div class="exam-list">
      ${exams.map(([t, sub, step, p, href]) => `
        <a class="panel exam-row" href="${href}" style="text-decoration:none;color:inherit">
          <div><h3>${t}</h3><div class="muted small">${sub}</div></div>
          <div><span class="tag">${step}</span></div>
          <div class="progress" title="${p} %"><i style="width:${p}%"></i></div>
          <div class="muted small" style="text-align:right">${p} % erledigt</div>
        </a>`).join("")}
    </div>
  </div>`;
}

// --- exam workflow ------------------------------------------------------------------
const STEPS = [
  ["zusammenstellen", "Zusammenstellen"],
  ["druck", "Teilnehmende und Druck"],
  ["einlesen", "Einlesen"],
  ["zweifelsfaelle", "Zweifelsfälle"],
  ["ergebnisse", "Ergebnisse"],
];

function examFrame(step, body) {
  const idx = STEPS.findIndex(([s]) => s === step);
  return `
  <div class="page">
    <div class="page-head">
      <div><h1>Klausur WS 2026/27</h1><p>${currentModule.name}, Freitag 05.02.2027, 60 Minuten</p></div>
    </div>
    <ol class="steps">
      ${STEPS.map(([s, label], i) => `
        <li class="${i < idx ? "done" : i === idx ? "current" : ""}"><a href="#/klausuren/dup/${s}">${label}${s === "zweifelsfaelle" && (idx === 2 || idx === 3) ? '<span class="badge">11</span>' : ""}</a></li>`).join("")}
    </ol>
    ${body}
  </div>`;
}

function viewCompose() {
  const rows = [
    ["Cutting Problems", 3, 3, 4], ["Solving Problems", 2, 2, 3], ["Algorithms and Programs", 4, 4, 5],
    ["Measuring and Experimenting", 3, 3, 3], ["Analog and Digital", 3, 3, 4], ["Symbols and Information", 3, 3, 4],
    ["Signal and Noise", 3, 2, 2], ["Number Systems", 3, 3, 3],
  ];
  return examFrame("zusammenstellen", `
    <div class="grid-2">
      <section class="panel">
        <div class="panel-head"><h2>Blueprint</h2><span class="aside">23 von 24 Aufgaben gezogen</span></div>
        <div class="panel-body">
          <table class="table">
            <thead><tr><th>Konzept</th><th class="num">Soll</th><th class="num">Gezogen</th><th class="num">geprüft vorhanden</th><th></th></tr></thead>
            <tbody>${rows.map(([c, soll, ist, verf]) => `
              <tr><td>${c}</td><td class="num">${soll}</td><td class="num">${ist}</td><td class="num">${verf}</td>
              <td>${ist < soll ? '<span class="tag warn">1 fehlt</span>' : '<span class="tag ok">passt</span>'}</td></tr>`).join("")}
            </tbody>
          </table>
        </div>
      </section>
      <div style="display:grid;gap:16px">
        <section class="panel">
          <div class="panel-head"><h2>Prüfung der Zusammenstellung</h2></div>
          <div class="panel-body checks">
            <div class="check ok">${icon("check")}Nur geprüfte Klausurvarianten, keine Übungsfragen</div>
            <div class="check ok">${icon("check")}Keine zwei Varianten derselben Übungsfrage</div>
            <div class="check ok">${icon("check")}Niveaus: 19 % erinnern, 41 % verstehen, 40 % anwenden</div>
            <div class="check warn">${icon("warn")}Signal and Noise: Es gibt nur zwei geprüfte Varianten, verlangt sind drei</div>
          </div>
        </section>
        <section class="panel">
          <div class="panel-head"><h2>Mischen</h2></div>
          <div class="panel-body option-cards">
            <label class="option-card on"><span class="radio"></span><span><b>Eigene Reihenfolge je Person</b><span class="muted small">Aufgaben und Antworten für jede Person neu gemischt</span></span></label>
            <label class="option-card"><span class="radio"></span><span><b>Gruppen A bis D</b><span class="muted small">vier feste Reihenfolgen</span></span></label>
            <label class="option-card"><span class="radio"></span><span><b>Nur Antworten mischen</b><span class="muted small">gleiche Aufgabenfolge für alle</span></span></label>
          </div>
        </section>
        <div class="row" style="flex:none;justify-content:flex-end">
          <button class="btn">Klausurheft ansehen</button>
          <button class="btn primary" data-toast="Klausur eingefroren">${icon("lock")}Einfrieren</button>
        </div>
      </div>
    </div>`);
}

function answerSheet() {
  // the cover of a personalised answer booklet, drawn like the printed page
  const qr = [];
  for (let y = 0; y < 9; y++) for (let x = 0; x < 9; x++) {
    const on = (x < 3 && y < 3) || (x > 5 && y < 3) || (x < 3 && y > 5) || ((x * 7 + y * 13 + x * y) % 5 < 2);
    if (on) qr.push(`<rect x="${x * 5}" y="${y * 5}" width="5" height="5"/>`);
  }
  let boxes = "";
  for (let r = 0; r < 8; r++) {
    boxes += `<text x="20" y="${236 + r * 22}" font-size="10" font-family="Source Serif 4, Georgia">${r + 1}</text>`;
    for (let c = 0; c < 5; c++) boxes += `<rect x="${44 + c * 22}" y="${226 + r * 22}" width="12" height="12" fill="none" stroke="#222" stroke-width="0.9"/>`;
  }
  for (let c = 0; c < 5; c++) boxes += `<text x="${47 + c * 22}" y="216" font-size="9" font-family="Source Serif 4, Georgia">${"ABCDE"[c]}</text>`;
  return `
  <svg viewBox="0 0 210 297" style="width:100%;max-width:340px;display:block;margin:auto;background:#fff;box-shadow:0 1px 2px rgba(23,32,43,.08),0 10px 30px -14px rgba(23,32,43,.3)">
    <g fill="#111"><rect x="8" y="8" width="8" height="8"/><rect x="194" y="8" width="8" height="8"/><rect x="8" y="281" width="8" height="8"/><rect x="194" y="281" width="8" height="8"/></g>
    <g transform="translate(152 22) scale(0.86)" fill="#111">${qr.join("")}</g>
    <text x="22" y="34" font-size="12" font-weight="600" font-family="Source Serif 4, Georgia">Antwortheft</text>
    <text x="22" y="47" font-size="7.5" font-family="Source Serif 4, Georgia">Digitalisierung und Programmierung</text>
    <text x="22" y="57" font-size="7.5" font-family="Source Serif 4, Georgia">Klausur WS 2026/27</text>
    <rect x="22" y="70" width="166" height="44" fill="none" stroke="#999" stroke-width="0.6"/>
    <text x="28" y="84" font-size="7.5" fill="#666" font-family="Source Serif 4, Georgia">Name</text>
    <text x="28" y="98" font-size="11" font-family="Source Serif 4, Georgia">Albers, Jana</text>
    <text x="118" y="84" font-size="7.5" fill="#666" font-family="Source Serif 4, Georgia">Matrikelnummer</text>
    <text x="118" y="98" font-size="11" font-family="Source Serif 4, Georgia">1048231</text>
    <text x="22" y="134" font-size="7" fill="#444" font-family="Source Serif 4, Georgia">Je Aufgabe das Kästchen der richtigen Antwort ankreuzen.</text>
    <text x="22" y="144" font-size="7" fill="#444" font-family="Source Serif 4, Georgia">Zum Korrigieren das Kästchen ganz ausmalen.</text>
    <text x="22" y="196" font-size="9" font-weight="600" font-family="Source Serif 4, Georgia">Aufgaben 1 bis 32</text>
    ${boxes}
    <text x="22" y="272" font-size="7" fill="#888" font-family="Source Serif 4, Georgia">Seite 1 von 3</text>
  </svg>`;
}

function viewPrint() {
  return examFrame("druck", `
    <div class="grid-2">
      <div style="display:grid;gap:16px">
        <section class="panel">
          <div class="panel-head"><h2>Teilnehmende</h2><span class="aside">48 aus dem Export des Prüfungssystems, 15.01.2027</span></div>
          <div class="panel-body">
            <table class="table">
              <thead><tr><th>Name</th><th>Matrikelnummer</th><th>Bogen</th></tr></thead>
              <tbody>${PEOPLE.map(([n, m], i) => `<tr><td>${n}</td><td class="mono">${m}</td><td class="muted small">Nr. ${String(i + 1).padStart(3, "0")}</td></tr>`).join("")}
              <tr><td colspan="3" class="muted small">und 40 weitere</td></tr></tbody>
            </table>
            <div class="drop" style="margin-top:14px">${icon("upload")}<strong>Neuen Export hierher ziehen</strong>CSV oder Excel aus dem Prüfungssystem</div>
          </div>
        </section>
      </div>
      <div style="display:grid;gap:16px">
        <section class="panel">
          <div class="panel-head"><h2>Antworthefte</h2></div>
          <div class="panel-body option-cards">
            <label class="option-card on"><span class="radio"></span><span><b>Personalisiert</b><span class="muted small">je angemeldeter Person ein Heft mit Name und Matrikelnummer</span></span></label>
            <label class="option-card"><span class="radio"></span><span><b>Anonym</b><span class="muted small">Matrikelnummer wird angekreuzt und beim Einlesen erkannt</span></span></label>
            <div class="row" style="margin-top:6px;align-items:center"><span class="muted">Reservehefte (anonym)</span><input class="input" value="5" style="max-width:70px;flex:none"></div>
          </div>
        </section>
        <section class="panel">
          <div class="panel-head"><h2>Vorschau Antwortheft</h2><span class="aside">Seite 1 von 3</span></div>
          <div class="panel-body" style="background:#f3f5f7">${answerSheet()}</div>
        </section>
        <div class="row" style="flex:none;justify-content:flex-end">
          <button class="btn">Probedruck (1 Heft)</button>
          <button class="btn primary" data-toast="PDF für den Kopierer erzeugt: 53 Hefte, 159 Seiten">${icon("print")}Druck-PDF erzeugen</button>
        </div>
      </div>
    </div>`);
}

function viewScan() {
  const pages = [];
  for (let i = 0; i < 159; i++) {
    let cls = i < 141 ? "read" : "";
    if ([17, 40, 41, 77, 93, 120].includes(i)) cls = "doubt";
    if (i === 102) cls = "problem";
    pages.push(`<i class="${cls}" title="Seite ${i + 1}"></i>`);
  }
  return examFrame("einlesen", `
    <div class="grid-2">
      <section class="panel">
        <div class="panel-head"><h2>Scans</h2><span class="aside">141 von 159 Seiten gelesen</span></div>
        <div class="panel-body">
          <div class="pages">${pages.join("")}</div>
          <div class="legend"><span><i style="background:#dfe5ec"></i>gelesen</span><span><i style="background:var(--red-soft)"></i>mit Zweifelsfall</span><span><i style="background:var(--amber-soft)"></i>Problem</span><span><i></i>noch nicht gelesen</span></div>
          <div class="progress" style="margin-top:16px"><i style="width:89%"></i></div>
        </div>
      </section>
      <div style="display:grid;gap:16px">
        <div class="drop">${icon("upload")}<strong>Scan-PDF vom Kopierer hierher ziehen</strong>300 dpi, Graustufen; mehrere Dateien in beliebiger Reihenfolge</div>
        <section class="panel">
          <div class="panel-head"><h2>Probleme</h2><span class="aside">1</span></div>
          <div class="panel-body">
            <div class="check warn">${icon("warn")}<span><b>Seite 103: QR-Code nicht lesbar.</b><br><span class="muted">Die Seite ist vermutlich verknickt eingezogen worden. Ordne sie von Hand zu oder scanne sie neu.</span></span></div>
            <div class="row" style="margin-top:10px"><button class="btn">Von Hand zuordnen</button><button class="btn">Seite ansehen</button></div>
          </div>
        </section>
        <section class="panel">
          <div class="panel-head"><h2>Stand</h2></div>
          <div class="panel-body">
            <table class="table">
              <tr><td>Hefte vollständig</td><td class="num">46 von 48</td></tr>
              <tr><td>Reservehefte benutzt</td><td class="num">2</td></tr>
              <tr><td>nicht abgegeben</td><td class="num">2</td></tr>
              <tr><td>Zweifelsfälle</td><td class="num"><a href="#/klausuren/dup/zweifelsfaelle">11 entscheiden</a></td></tr>
            </table>
          </div>
        </section>
      </div>
    </div>`);
}

// the scanned crop: one row of tick boxes with pencil marks
function scanCrop() {
  const pen = "#3b4048";
  const box = (x, y) => `<rect x="${x}" y="${y}" width="26" height="26" fill="none" stroke="#1d1d1d" stroke-width="1.6"/>`;
  return `
  <svg class="scan-crop" viewBox="0 0 640 170" role="img" aria-label="Scan-Ausschnitt Aufgabe 17">
    <defs><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" result="n"/><feColorMatrix in="n" type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 0.08"/></feComponentTransfer><feBlend in="SourceGraphic" mode="multiply"/></filter></defs>
    <g filter="url(#grain)">
      <rect width="640" height="170" fill="#f4f3ef"/>
      <text x="34" y="96" font-family="Source Serif 4, Georgia" font-size="22" fill="#1d1d1d">17</text>
      ${["A", "B", "C", "D", "E"].map((l, i) => `<text x="${120 + i * 96 + 7}" y="52" font-family="Source Serif 4, Georgia" font-size="16" fill="#1d1d1d">${l}</text>`).join("")}
      ${[0, 1, 2, 3, 4].map((i) => box(120 + i * 96, 72)).join("")}
      <!-- B: a clear cross -->
      <path d="M220 76 C226 83 234 91 241 96" stroke="${pen}" stroke-width="3.2" fill="none" stroke-linecap="round"/>
      <path d="M241 75 C234 82 227 90 219 97" stroke="${pen}" stroke-width="3" fill="none" stroke-linecap="round"/>
      <!-- B was then filled in to cancel it, half-heartedly -->
      <path d="M219 78 L240 80 M218 84 L241 85 M219 90 L238 91" stroke="${pen}" stroke-width="2.4" opacity="0.75" stroke-linecap="round"/>
      <!-- D: a smaller cross, slightly outside the box -->
      <path d="M411 78 C416 84 421 90 428 99" stroke="${pen}" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M426 76 C421 83 417 90 409 101" stroke="${pen}" stroke-width="2.8" fill="none" stroke-linecap="round"/>
      <text x="420" y="140" font-family="Segoe Print, Comic Sans MS, cursive" font-size="15" fill="${pen}" opacity="0.85">→ D</text>
    </g>
  </svg>`;
}

function viewReview(choice = "D") {
  const queue = [
    ["Albers, Jana", "Aufgabe 17", true], ["Albers, Jana", "Aufgabe 24", false], ["Brandt, Tobias", "Aufgabe 3", false],
    ["Çelik, Deniz", "Aufgabe 9", false], ["Engel, Marvin", "Matrikelnummer (Reserveheft)", false], ["Fischer, Sophie", "Aufgabe 31", false],
  ];
  return examFrame("zweifelsfaelle", `
    <div class="review">
      <div class="scan-stage">
        <span class="scan-meta">Heft 001, Seite 1, Aufgabe 17</span>
        <div class="scan-nav"><button class="btn">Ganze Seite</button></div>
        ${scanCrop()}
      </div>
      <aside class="decision panel panel-body">
        <div class="reading">Gelesen: B und D<small>Zwei Kästchen sind markiert. B sieht ausgemalt aus, also korrigiert, und daneben steht „→ D“.</small></div>
        <div>
          <div class="muted small" style="margin-bottom:6px">Was gilt?</div>
          <div class="choices" id="choices">
            ${["A", "B", "C", "D", "E"].map((l, i) => `<button class="choice ${l === choice ? "on" : ""}" data-choice="${l}"><b>${l}</b><kbd>${i + 1}</kbd></button>`).join("")}
          </div>
          <div class="row" style="margin-top:8px"><button class="btn" data-choice="none">Keine Antwort <kbd class="k">0</kbd></button><button class="btn" data-choice="BD">B und D <kbd class="k">M</kbd></button></div>
        </div>
        <div class="second-opinion">
          <h4>${icon("spark").replace("<svg", '<svg width="15" height="15" style="stroke:var(--ink)"')}Zweite Meinung</h4>
          <span class="muted">Das Sprachmodell liest D: Das Kästchen B ist nachträglich ausgemalt, was nach dem Hinweis auf dem Bogen eine Korrektur bedeutet, und der Pfeil bestätigt D.</span>
        </div>
        <button class="btn decide" data-next>${icon("check")}D übernehmen und weiter <kbd class="k" style="background:transparent;color:#fff;border-color:rgba(255,255,255,.5)">Enter</kbd></button>
        <div class="kbd-hint"><kbd class="k">1</kbd>–<kbd class="k">5</kbd> wählen, <kbd class="k">Enter</kbd> übernehmen, <kbd class="k">←</kbd> zurück</div>
        <div>
          <div class="muted small" style="margin:6px 0 4px">Zweifelsfall 1 von 11</div>
          <ul class="queue">${queue.map(([who, what, now]) => `<li class="${now ? "now" : ""}"><span>${what}</span><span class="s">${who}</span></li>`).join("")}</ul>
        </div>
      </aside>
    </div>`);
}

function viewResults() {
  const grades = [["1,0", 2], ["1,3", 3], ["1,7", 4], ["2,0", 6], ["2,3", 7], ["2,7", 6], ["3,0", 5], ["3,3", 4], ["3,7", 3], ["4,0", 2], ["5,0", 4]];
  const max = 7;
  const items = [
    ["aa-014", "Algorithms and Programs", 0.62, 0.41, ""], ["sn-008", "Signal and Noise", 0.18, -0.12, "flag"],
    ["pd-004", "Cutting Problems", 0.81, 0.33, ""], ["ns-011", "Number Systems", 0.47, 0.52, ""], ["si-006", "Symbols and Information", 0.55, 0.09, "low"],
  ];
  return examFrame("ergebnisse", `
    <div class="grid-3" style="margin-bottom:16px">
      <div class="panel stat"><div class="v">48</div><div class="l">bewertet</div></div>
      <div class="panel stat"><div class="v">2,6</div><div class="l">Durchschnittsnote</div></div>
      <div class="panel stat"><div class="v">91,7 %</div><div class="l">bestanden (4 nicht bestanden)</div></div>
    </div>
    <div class="grid-2">
      <section class="panel">
        <div class="panel-head"><h2>Aufgabenanalyse</h2><span class="aside">Schwierigkeit und Trennschärfe je Aufgabe</span></div>
        <div class="panel-body">
          <table class="table">
            <thead><tr><th>Aufgabe</th><th>Konzept</th><th class="num">gelöst</th><th class="num">Trennschärfe</th><th></th></tr></thead>
            <tbody>${items.map(([id, c, p, r, f]) => `
              <tr><td class="mono">${id}</td><td>${c}</td><td class="num">${Math.round(p * 100)} %</td>
              <td class="num ${f === "flag" ? "flag" : ""}">${r.toFixed(2).replace(".", ",")}</td>
              <td>${f === "flag" ? '<button class="btn" data-toast="Aufgabe sn-008 gestrichen, Noten neu berechnet">Streichen</button>' : f === "low" ? '<span class="tag warn">ansehen</span>' : ""}</td></tr>`).join("")}
            </tbody>
          </table>
          <div class="advice" style="margin-top:12px">
            <p><b>sn-008 fällt auf:</b> Die besten 27 % haben öfter C gewählt als die richtige Antwort B.</p>
            <p class="src">Mögliche Ursache laut Sprachmodell: C ist bei kurzer Integrationszeit ebenfalls vertretbar. Prüfe, ob die Frage zwei richtige Antworten hat.</p>
          </div>
        </div>
      </section>
      <div style="display:grid;gap:16px">
        <section class="panel">
          <div class="panel-head"><h2>Notenverteilung</h2></div>
          <div class="panel-body">
            <div class="histo">${grades.map(([g, n]) => `<div class="${g === "5,0" ? "fail" : ""}"><small>${n}</small><span style="height:${(n / max) * 100}%"></span><small>${g}</small></div>`).join("")}</div>
          </div>
        </section>
        <section class="panel">
          <div class="panel-head"><h2>Ausgabe</h2></div>
          <div class="panel-body" style="display:grid;gap:8px">
            <button class="btn" data-toast="Notenliste exportiert">${icon("download")}Notenliste für das Prüfungsamt</button>
            <button class="btn" data-toast="48 Einsichtsbögen erzeugt">${icon("download")}Einsichtsbögen (PDF je Person)</button>
            <button class="btn" data-toast="Bericht erzeugt">${icon("download")}Statistikbericht</button>
            <button class="btn primary" data-toast="Noten freigegeben">Noten freigeben</button>
          </div>
        </section>
      </div>
    </div>`);
}

// --- view: settings -----------------------------------------------------------------
function viewSettings() {
  const features = [
    ["Zweite Meinung zu Zweifelsfällen", "Schickt nur den Bildausschnitt der Kästchen, ohne Namen und QR-Code.", true],
    ["Didaktische Prüfung von Fragen", "Schickt den Text der Frage mit Antworten.", true],
    ["Entwürfe und Übersetzungen", "Schickt den Text der Frage.", true],
    ["Deutung der Aufgabenanalyse", "Schickt Frage und anonyme Antwortverteilung.", false],
    ["Abschrift der Handschrift", "Schickt Bildausschnitte von Freitextantworten. Nur nutzen, wo deine Hochschule das erlaubt, oder mit einem lokalen Modell.", false],
  ];
  return `
  <div class="page">
    <div class="page-head"><div><h1>Einstellungen</h1></div></div>
    <div class="settings">
      <section class="panel">
        <div class="panel-head"><h2>Allgemein</h2></div>
        <div class="panel-body" style="display:grid;gap:14px">
          <div class="row">
            <label class="field"><span>Sprache der Oberfläche</span><div class="seg"><button class="on">Deutsch</button><button>English</button></div></label>
            <label class="field"><span>Dein Name (für Freigaben)</span><input class="input" value="Nicolas Meseth"></label>
          </div>
          <p class="muted small" style="margin:0">Ordner und Prüfungsordnung stellst du je Modul ein, unter <a href="#/module">Module</a>.</p>
        </div>
      </section>
      <section class="panel">
        <div class="panel-head"><h2>Sprachmodell</h2><span class="aside">optional; ohne läuft alles genauso</span></div>
        <div class="panel-body">
          <div class="switch-row"><button class="switch on" aria-pressed="true" aria-label="Sprachmodell nutzen"></button><div class="text"><b>Sprachmodell nutzen</b><span class="muted small">Vorschläge erscheinen nur als Vorschläge; geändert wird nichts ohne deinen Klick.</span></div></div>
          <div class="row" style="padding:12px 0">
            <label class="field"><span>Anbieter</span><select class="select"><option>OpenAI</option><option>Anthropic</option><option>Lokales Modell (Ollama)</option></select></label>
            <label class="field"><span>API-Schlüssel</span><input class="input" type="password" value="••••••••••••••••"></label>
          </div>
          <p class="muted small" style="margin:0 0 6px">Der Schlüssel liegt in der Windows-Anmeldeinformationsverwaltung, nicht in einer Datei.</p>
          ${features.map(([t, d, on]) => `<div class="switch-row"><button class="switch ${on ? "on" : ""}" aria-pressed="${on}" aria-label="${t}"></button><div class="text"><b>${t}</b><span class="muted small">${d}</span></div></div>`).join("")}
        </div>
      </section>
    </div>
  </div>`;
}

// --- router ------------------------------------------------------------------------
function render() {
  const parts = location.hash.replace(/^#\/?/, "").split("/");
  const [area, a, b] = parts;
  let html;
  if (area === "oeffnen" && a) {
    currentModule = MODULES.find((m) => m.id === a) || currentModule;
    location.hash = "#/fragen";
    return;
  }
  if (area === "module" || area === "") {
    const editing = a === "neu" ? "neu" : (a && b === "einstellungen" ? a : null);
    document.getElementById("root").innerHTML = shell("#/module", viewModules(editing));
    return;
  }
  if (area === "klausuren" && a) {
    const views = { zusammenstellen: viewCompose, druck: viewPrint, einlesen: viewScan, zweifelsfaelle: viewReview, ergebnisse: viewResults };
    html = shell("#/klausuren", (views[b] || viewCompose)());
  } else if (area === "klausuren") html = shell("#/klausuren", viewExams());
  else if (area === "einstellungen") html = shell("#/einstellungen", viewSettings());
  else html = shell("#/fragen", viewQuestions(a));
  document.getElementById("root").innerHTML = html;
}

document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-toggle-nav],[data-toast],[data-advice],[data-close-advice],[data-choice],[data-next],.switch,.seg button,.option-card,.filter-list li,.opt .mark");
  if (!t) return;
  if (t.hasAttribute("data-toggle-nav")) toggleNav();
  if (t.dataset.toast) toast(t.dataset.toast);
  if (t.hasAttribute("data-advice")) showAdvice();
  if (t.hasAttribute("data-close-advice")) $("#advice").innerHTML = "";
  if (t.dataset.choice) { document.querySelectorAll(".choice").forEach((c) => c.classList.toggle("on", c.dataset.choice === t.dataset.choice)); }
  if (t.hasAttribute("data-next")) toast("Aufgabe 17: D übernommen. Weiter mit Aufgabe 24");
  if (t.classList.contains("switch")) { t.classList.toggle("on"); t.setAttribute("aria-pressed", t.classList.contains("on")); }
  if (t.matches(".seg button")) { t.parentElement.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === t)); }
  if (t.classList.contains("option-card")) { t.parentElement.querySelectorAll(".option-card").forEach((b) => b.classList.toggle("on", b === t)); }
  if (t.matches(".filter-list li")) { t.parentElement.querySelectorAll("li").forEach((b) => b.classList.toggle("on", b === t)); }
  if (t.matches(".opt .mark")) { const on = !t.classList.contains("correct"); t.classList.toggle("correct", on); t.innerHTML = on ? icon("check") : ""; }
});

document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key.toLowerCase() === "b") { e.preventDefault(); toggleNav(); return; }
  if (!location.hash.includes("zweifelsfaelle") || e.target.matches("input,textarea,select")) return;
  const map = { 1: "A", 2: "B", 3: "C", 4: "D", 5: "E" };
  if (map[e.key]) document.querySelectorAll(".choice").forEach((c) => c.classList.toggle("on", c.dataset.choice === map[e.key]));
  if (e.key === "Enter") toast("Übernommen. Weiter mit dem nächsten Zweifelsfall");
});

window.addEventListener("hashchange", render);
render();
