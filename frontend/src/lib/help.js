// Help for every page, behind the "?" in the top bar, and the tour that shows the parts of a page one by one.
// `points` are the short paragraphs of the help, `tour` the steps of the tour. A step points at the element that
// carries `data-tour="<target>"`; a step whose element is not on the page at the moment (no question chosen, no
// exam open) is skipped. tests/test_help.py checks that every target is marked somewhere in the interface, so that
// a step cannot point at something that was renamed or removed.

export const HELP = {
  "/modules": {
    de: {
      title: "Module",
      intro: "Ein Modul ist eine Lehrveranstaltung mit ihren Klausuren. Es zieht seine Fragen aus einem oder mehreren Fragenpools; ein Pool kann mehreren Modulen dienen.",
      points: [
        "„Neues Modul“ legt einen Modulordner an und verbindet ihn mit einem Pool, „Ordner öffnen“ nimmt ein vorhandenes Modul auf, etwa nach dem Kopieren von einem anderen Rechner.",
        "Das aktuelle Modul steht oben in der Leiste; die Seiten Themen, Fragen und Klausuren zeigen immer dessen Pools und Klausuren. Oben in der Leiste wechselst du es auch.",
        "An jedem Pool stehen seine Sprachen und die Zahl seiner Fragen. Beim Zeigen auf einen Pool erscheinen „Sprachen“, „Im Explorer zeigen“ und „Pool lösen“; das Lösen lässt die Fragen unberührt.",
      ],
      tour: [
        { target: "modules-new", title: "Neues Modul", text: "Legt einen Modulordner an und verbindet ihn mit einem vorhandenen oder neuen Fragenpool." },
        { target: "modules-open", title: "Ordner öffnen", text: "Nimmt einen Modulordner auf, der schon eine module.toml hat, zum Beispiel aus einem geteilten Ordner." },
        { target: "module-row", title: "Ein Modul", text: "Name, Kürzel und Ordner des Moduls. Das grüne „aktuell“ zeigt, mit welchem Modul die anderen Seiten arbeiten." },
        { target: "module-pools", title: "Seine Pools", text: "Jeder Pool mit Sprachen und Fragenzahl. Beim Zeigen darauf änderst du die Sprachen oder öffnest den Ordner im Explorer." },
        { target: "module-menu", title: "Weitere Schritte", text: "Hier fügst du einen weiteren Pool hinzu, öffnest den Modulordner oder entfernst das Modul aus der Liste, ohne Dateien zu löschen." },
        { target: "module-switch", title: "Aktuelles Modul", text: "Hier oben wechselst du jederzeit das Modul, mit dem Themen, Fragen und Klausuren arbeiten." },
      ],
    },
    en: {
      title: "Modules",
      intro: "A module is a course with its exams. It draws its questions from one or several question pools; a pool can serve several modules.",
      points: [
        "“New module” creates a module folder and connects it to a pool; “Open folder” adds an existing module, for example one copied from another computer.",
        "The current module is shown in the top bar; the Concepts, Questions and Exams pages always show its pools and exams. You switch it in the top bar too.",
        "Each pool shows its languages and its number of questions. Pointing at a pool shows “Languages”, “Show in Explorer” and “Detach pool”; detaching leaves the questions untouched.",
      ],
      tour: [
        { target: "modules-new", title: "New module", text: "Creates a module folder and connects it to an existing or a new question pool." },
        { target: "modules-open", title: "Open folder", text: "Adds a module folder that already has a module.toml, for example from a shared folder." },
        { target: "module-row", title: "A module", text: "Its name, short name and folder. The green “current” shows which module the other pages work with." },
        { target: "module-pools", title: "Its pools", text: "Every pool with its languages and number of questions. Point at one to change its languages or open its folder." },
        { target: "module-menu", title: "More steps", text: "Add another pool, open the module folder, or take the module off the list without deleting any file." },
        { target: "module-switch", title: "Current module", text: "Up here you switch the module that Concepts, Questions and Exams work with, at any time." },
      ],
    },
  },

  "/concepts": {
    de: {
      title: "Themen",
      intro: "Jede Frage gehört zu einem Thema. Hier pflegst du Namen und Kurzbeschreibungen der Themen und siehst auf einen Blick, wie es um ihre Fragen steht.",
      points: [
        "Links stehen die Themen der Pools des aktuellen Moduls mit der Zahl ihrer Fragen; die Suche und, bei mehreren Pools, der Poolfilter grenzen die Liste ein.",
        "Rechts änderst du Name und Kurzbeschreibung eines Themas und speicherst sie; die Kennung darunter benennt den Ordner der Fragen und bleibt gleich.",
        "Die Übersicht zeigt die Fragen eines Themas nach Niveau, Typ und Status, dazu, wie viele Übungsfragen noch keine Klausurvariante haben. „Fragen zeigen“ öffnet die Fragenliste mit diesem Thema als Filter.",
        "Ein Thema ohne Fragen lässt sich löschen, eines mit Fragen nicht, damit nichts verloren geht.",
      ],
      tour: [
        { target: "concepts-search", title: "Suchen", text: "Grenzt die Liste nach Name und Beschreibung ein." },
        { target: "concepts-list", title: "Die Themen", text: "Jedes Thema mit der Zahl seiner Fragen; ein roter Punkt zählt Fragen mit Fehlern. Ein Klick zeigt es rechts." },
        { target: "concept-form", title: "Name und Beschreibung", text: "Hier änderst du, wie das Thema überall heißt. „Speichern“ übernimmt es; die Kennung bleibt." },
        { target: "concept-questions", title: "Seine Fragen", text: "„Fragen zeigen“ springt zur Fragenliste mit diesem Thema, „Neue Frage“ legt gleich eine darin an." },
        { target: "concepts-new", title: "Neues Thema", text: "Fragt nach Name und Kurzbeschreibung; die Kennung macht Markwise aus dem Namen." },
      ],
    },
    en: {
      title: "Concepts",
      intro: "Every question belongs to a concept. Here you look after the names and short descriptions of the concepts and see at a glance how their questions stand.",
      points: [
        "On the left are the concepts of the current module's pools with their number of questions; the search and, with several pools, the pool filter narrow the list.",
        "On the right you change a concept's name and short description and save them; the identifier below names the folder of its questions and stays the same.",
        "The overview shows the questions of a concept by level, type and status, and how many practice questions still lack an exam variant. “Show questions” opens the question list filtered to the concept.",
        "A concept without questions can be deleted, one with questions cannot, so that nothing is lost.",
      ],
      tour: [
        { target: "concepts-search", title: "Search", text: "Narrows the list by name and description." },
        { target: "concepts-list", title: "The concepts", text: "Each concept with its number of questions; a red dot counts questions with errors. A click shows it on the right." },
        { target: "concept-form", title: "Name and description", text: "Change what the concept is called everywhere. “Save” takes it over; the identifier stays." },
        { target: "concept-questions", title: "Its questions", text: "“Show questions” jumps to the question list for this concept, “New question” starts one in it." },
        { target: "concepts-new", title: "New concept", text: "Asks for a name and a short description; Markwise makes the identifier from the name." },
      ],
    },
  },

  "/questions": {
    de: {
      title: "Fragen",
      intro: "Hier schreibst und pflegst du die Fragen der Pools des aktuellen Moduls. Eine Frage steht rechts so da, wie sie im Heft aussieht, und wird genau dort bearbeitet.",
      points: [
        "Suche und Filter grenzen die Liste ein; mehrere Werte in einem Filter gelten als „oder“, mehrere Filter als „und“. Klausurvarianten stehen eingerückt unter ihrer Übungsfrage und lassen sich einklappen.",
        "Ein Klick auf einen Text der Frage macht ihn zu einem Feld mit seinem Markdown; der Haken, Strg+Enter oder ein Klick daneben speichert, Escape verwirft. Formeln schreibst du als LaTeX zwischen $ und $, abgesetzt zwischen $$ und $$.",
        "Die Labels neben der Kennung sind die Einstellungen der Frage: Thema, Typ, Niveau, Zeit, Status und Verwendung. Ein Klick öffnet die Auswahl; im Status liegen Freigeben, Freigabe zurücknehmen und Ausmustern. Ein neues Thema verschiebt die Frage mit ihren Klausurvarianten dorthin, die Kennung bleibt.",
        "„Details“ zeigt Begründungen, Bewertungshinweise, Abbildungen und Code, die Herkunft, die Prüfung mit KI und alle Befunde.",
        "Mit den Pfeilen über der Frage, Alt+←/→ oder Bild ↑/↓ blätterst du durch die Liste, auch wenn sie ausgeblendet ist.",
      ],
      tour: [
        { target: "q-search", title: "Suchen", text: "Sucht in Fragetext, Antworten, Begründungen und Kennung." },
        { target: "q-filters", title: "Filter", text: "Jeder Filter nennt seinen Namen und zeigt blau, was gewählt ist. Mehrere Werte in einem Filter bedeuten „oder“." },
        { target: "q-count", title: "Anzahl und Ansicht", text: "Wie viele Fragen die Liste zeigt und wie viele Varianten eingeklappt sind. Daneben: Filter zurücksetzen, alle Varianten ein- und ausklappen, Liste und Statistik ein- und ausblenden." },
        { target: "q-list", title: "Die Liste", text: "Ein Klick zeigt eine Frage rechts; die Pfeiltasten wandern durch die Liste. Die Kante rechts lässt sich ziehen, um die Liste breiter oder schmaler zu machen." },
        { target: "q-nav", title: "Blättern", text: "Vor und zurück in der Reihenfolge der Liste, auch mit Alt+←/→ oder Bild ↑/↓." },
        { target: "q-labels", title: "Einstellungen als Labels", text: "Thema, Typ, Niveau, Zeit, Status und Verwendung. Ein Klick auf ein Label öffnet seine Auswahl; jede Wahl ist sofort gespeichert." },
        { target: "q-status", title: "Status und Freigabe", text: "Hier gibst du die Frage als prüfende Person frei, nimmst deine Freigabe zurück oder musterst sie aus. Eine Freigabe bleibt, auch wenn die Frage später geändert wird." },
        { target: "q-stem", title: "In der Frage bearbeiten", text: "Ein Klick auf einen Text öffnet sein Markdown. Der Haken oder Strg+Enter speichert, Escape verwirft. Das Kästchen einer Antwort markiert sie als richtig." },
        { target: "q-details", title: "Details", text: "Blendet unter der Frage alles Weitere ein: Begründungen, Abbildungen und Code, Abdeckung, KI-Prüfung, Befunde und Herkunft." },
        { target: "q-more", title: "Weitere Aktionen", text: "Klausurvariante anlegen, die Datei im Editor öffnen oder einen Entwurf löschen." },
        { target: "q-new", title: "Neue Frage", text: "Fragt nach Pool, Thema und Typ und öffnet die neue Frage gleich zum Schreiben." },
      ],
    },
    en: {
      title: "Questions",
      intro: "Here you write and look after the questions of the current module's pools. A question is shown on the right as it reads in the booklet, and it is edited right there.",
      points: [
        "Search and filters narrow the list; several values in one filter count as “or”, several filters as “and”. Exam variants stand indented below their practice question and can be folded away.",
        "A click on a text of the question turns it into a field with its Markdown; the tick, Ctrl+Enter or a click elsewhere saves, Escape discards. Formulas are LaTeX between $ and $, set apart between $$ and $$.",
        "The labels next to the identifier are the question's settings: concept, type, level, time, status and use. A click opens the choice; the status holds release, withdrawing your release and retiring. Another concept moves the question there with its exam variants; the identifier stays.",
        "“Details” shows rationales, marking notes, figures and code, where the question comes from, the check with AI and all findings.",
        "The arrows above the question, Alt+←/→ or Page Up/Down page through the list, also while it is hidden.",
      ],
      tour: [
        { target: "q-search", title: "Search", text: "Searches question texts, answers, rationales and identifiers." },
        { target: "q-filters", title: "Filters", text: "Each filter names itself and shows in blue what is chosen. Several values in one filter mean “or”." },
        { target: "q-count", title: "Count and view", text: "How many questions the list shows and how many variants are folded away. Next to it: clear filters, fold all variants, show or hide the list and the statistics." },
        { target: "q-list", title: "The list", text: "A click shows a question on the right; the arrow keys move through the list. Drag its right edge to make it wider or narrower." },
        { target: "q-nav", title: "Paging", text: "Back and forth in the order of the list, also with Alt+←/→ or Page Up/Down." },
        { target: "q-labels", title: "Settings as labels", text: "Concept, type, level, time, status and use. A click on a label opens its choice; every choice is saved at once." },
        { target: "q-status", title: "Status and release", text: "Release the question as an examiner, withdraw your release or retire it. A release stays when the question is changed later." },
        { target: "q-stem", title: "Edit in the question", text: "A click on a text opens its Markdown. The tick or Ctrl+Enter saves, Escape discards. An answer's box marks it as correct." },
        { target: "q-details", title: "Details", text: "Shows everything else below the question: rationales, figures and code, coverage, the AI check, findings and origin." },
        { target: "q-more", title: "More actions", text: "Create an exam variant, open the file in an editor, or delete a draft." },
        { target: "q-new", title: "New question", text: "Asks for pool, concept and type and opens the new question for writing." },
      ],
    },
  },

  "/exams": {
    de: {
      title: "Klausuren",
      intro: "Hier stellst du die Klausuren des aktuellen Moduls zusammen und druckst sie: als Klausurheft mit Antwortbogen oder mit Kästchen direkt unter den Fragen, dazu den Lösungsschlüssel.",
      points: [
        "„Neue Klausur“ fragt nach Titel, Datum, Sprache und Antwortform; ein Klick auf eine Klausur öffnet sie.",
        "Links stehen die Fragen der Pools, anfangs nur die für Klausuren. Das Plus hängt eine Frage an, ziehen setzt sie an eine bestimmte Stelle; Fragen in der Klausur sind grün hinterlegt und lassen sich mit „Fragen der Klausur ausblenden“ aus der Liste nehmen.",
        "Rechts steht die Klausur so, wie das Heft sie zeigt. Am Griff ziehst du eine Frage an einen anderen Platz; Niveau und Zeit sind Labels, die Punkte folgen der Zeit, bis du sie selbst setzt.",
        "Ein Klick auf eine Frage, rechts in der Klausur oder links in der Liste, findet sie auf der anderen Seite und rahmt sie auf beiden; links klappt sie ihre Antworten aus, rechts zeigt sie sie auch dann, wenn die Antworten ausgeblendet sind.",
        "„Abschnitt“ teilt die Klausur in Teile, etwa Teil A und Teil B, wahlweise mit einem Thema, das die Liste links filtert. Die Gliederung zeigt die ganze Klausur auf einem Bildschirm.",
        "„Drucken“ setzt die Hefte als PDF in den Klausurordner, mit QR-Code und Eckmarken zum Einlesen der Scans.",
      ],
      tour: [
        { target: "exams-new", title: "Neue Klausur", text: "Fragt nach Titel, Datum, Sprache und ob die Antworten auf einen eigenen Bogen oder unter die Fragen kommen." },
        { target: "exams-list", title: "Die Klausuren", text: "Jede Klausur des Moduls mit Datum, Sprache, Fragen und Punkten. Ein Klick öffnet sie." },
        { target: "exam-settings", title: "Angaben zur Klausur", text: "Titel, Datum, Sprache, Antwortform und Prüfende. Ein neuer Titel oder ein neues Datum benennt den Ordner der Klausur mit um." },
        { target: "exam-totals", title: "Summen und Prüfung", text: "Fragen, Punkte und Bearbeitungszeit, dazu Hinweise, wenn etwas nicht stimmt, etwa zwei Varianten derselben Übungsfrage." },
        { target: "exam-picker", title: "Fragen hinzufügen", text: "Suche und Filter wie auf der Fragenseite. Das Plus hängt eine Frage an, ziehen setzt sie an die gewünschte Stelle, das Auge zeigt sie in Ruhe. Darunter blendest du Fragen aus, die schon in der Klausur stehen." },
        { target: "exam-list", title: "Die Klausur", text: "So sieht das Heft aus. Am Griff links ziehst du eine Frage an einen anderen Platz; Thema, Niveau und Zeit öffnen per Klick ihre Auswahl, die Punkte änderst du direkt." },
        { target: "exam-section", title: "Abschnitte", text: "Teilt die Klausur in Teile mit Titel, Hinweis und optional einem Thema; die Summen stehen an jedem Abschnitt." },
        { target: "exam-view", title: "Fragen oder Gliederung", text: "Die Gliederung zeigt eine Zeile je Frage, gut zum Ordnen der ganzen Klausur. Der Pfeil daneben blendet die Antworten aus." },
        { target: "exam-print", title: "Drucken", text: "Setzt Klausurheft, Antwortbogen und Lösungsschlüssel als PDF in den Klausurordner." },
      ],
    },
    en: {
      title: "Exams",
      intro: "Here you put together the exams of the current module and print them: as a booklet with an answer sheet or with the boxes right below the questions, together with the answer key.",
      points: [
        "“New exam” asks for title, date, language and answer form; a click on an exam opens it.",
        "On the left are the questions of the pools, at first only those meant for exams. The plus adds a question at the end, dragging puts it at a chosen place; questions in the exam have a green background, and “Hide questions in the exam” takes them off the list.",
        "On the right the exam is shown as the booklet shows it. Drag a question by its handle to another place; level and time are labels, and the points follow the time until you set them yourself.",
        "A click on a question, on the right in the exam or on the left in the list, finds it on the other side and frames it on both; on the left it unfolds its answers, on the right it shows them even while the answers are hidden.",
        "“Section” divides the exam into parts such as Part A and Part B, optionally with a concept that filters the list on the left. The outline shows the whole exam on one screen.",
        "“Print” typesets the booklets as PDF files in the exam folder, with QR codes and corner marks for reading the scans.",
      ],
      tour: [
        { target: "exams-new", title: "New exam", text: "Asks for title, date, language and whether the answers go on an answer sheet or below the questions." },
        { target: "exams-list", title: "The exams", text: "Every exam of the module with date, language, questions and points. A click opens it." },
        { target: "exam-settings", title: "About the exam", text: "Title, date, language, answer form and examiners. A new title or date renames the exam's folder too." },
        { target: "exam-totals", title: "Totals and checks", text: "Questions, points and answering time, and notes when something is wrong, such as two variants of the same practice question." },
        { target: "exam-picker", title: "Add questions", text: "Search and filters as on the Questions page. The plus adds a question, dragging puts it where you want it, the eye shows it in peace. Below them you hide questions already in the exam." },
        { target: "exam-list", title: "The exam", text: "This is how the booklet looks. Drag a question by the handle on its left; concept, level and time open their choice on a click, the points are changed right there." },
        { target: "exam-section", title: "Sections", text: "Divides the exam into parts with a title, a note and optionally a concept; each section shows its totals." },
        { target: "exam-view", title: "Questions or outline", text: "The outline shows one line per question, handy for ordering the whole exam. The arrow next to it hides the answers." },
        { target: "exam-print", title: "Print", text: "Typesets booklet, answer sheet and answer key as PDF files in the exam folder." },
      ],
    },
  },

  "/settings": {
    de: {
      title: "Einstellungen",
      intro: "Die Einstellungen gelten für diesen Rechner: die Sprache der Oberfläche, dein Name als prüfende Person und, wenn du möchtest, die Hilfe durch ein Sprachmodell.",
      points: [
        "Die Sprache der Oberfläche ist unabhängig von der Sprache einer Klausur; die Hefte stehen immer in der Sprache der Klausur.",
        "Dein Name steht an jeder Freigabe und an den Fragen, die du anlegst oder änderst. Ohne Namen nimmt Markwise deinen Windows-Benutzernamen.",
        "Das Sprachmodell ist standardmäßig aus. Eingeschaltet prüft es Fragen und schlägt Übersetzungen, Begründungen und falsche Antworten vor; es sieht nur die Frage selbst mit ihren Abbildungen, nie Scans, Namen oder Noten. Der Schlüssel liegt in der Windows-Anmeldeinformationsverwaltung.",
      ],
      tour: [
        { target: "settings-language", title: "Sprache", text: "Deutsch oder Englisch für die Oberfläche." },
        { target: "settings-examiner", title: "Dein Name", text: "Steht an deinen Freigaben und an den Fragen, die du anlegst oder änderst." },
        { target: "settings-llm", title: "Sprachmodell", text: "Schaltet die Hilfe durch ein Sprachmodell ein, mit Schlüssel und Modell. Standardmäßig ist sie aus." },
      ],
    },
    en: {
      title: "Settings",
      intro: "The settings apply to this computer: the language of the interface, your name as examiner and, if you like, help from a language model.",
      points: [
        "The interface language is independent of an exam's language; booklets are always in the exam's language.",
        "Your name stands at every release and at the questions you create or change. Without a name, Markwise uses your Windows user name.",
        "The language model is off by default. Switched on, it checks questions and proposes translations, rationales and wrong answers; it sees only the question itself with its figures, never scans, names or marks. The key is kept in the Windows Credential Manager.",
      ],
      tour: [
        { target: "settings-language", title: "Language", text: "German or English for the interface." },
        { target: "settings-examiner", title: "Your name", text: "Stands at your releases and at the questions you create or change." },
        { target: "settings-llm", title: "Language model", text: "Switches on help from a language model, with key and model. It is off by default." },
      ],
    },
  },
};

export const helpFor = (path, lang) => HELP[path]?.[lang] ?? HELP[path]?.de ?? null;
