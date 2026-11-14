"use strict";
  // ---------------------------------------------------------------- Языки (этап Пульта «Меню языков»)
  // Ключ перевода — сама русская надпись (как в gettext). Словари — i18n.js (надписи окна) и translations.json
  // (данные: проекты, группы, этапы, описания, события). Нет перевода — показывается по-русски.
  const LANGS = { ru: "Русский", en: "English", he: "עברית" };
  const LANG = (function () {
    const fromBoard = window.BOARD && window.BOARD.settings && window.BOARD.settings.lang;
    let saved = "";
    try { saved = localStorage.getItem("pult-lang") || ""; } catch (err) { saved = ""; }
    const v = fromBoard || saved || "ru";
    return LANGS[v] ? v : "ru";
  })();
  const I18N = window.PULT_I18N || {};
  const UI = (I18N[LANG] || {});
  const CYR_RE = /[А-Яа-яЁё]/;
  const EDGE = "\\s·—–:;,.!?()«»\"'+＋✓✗○◐▶↑↓⚑✎✕‹›…/|•◆◇✦⚠▦▤☑";
  const CORE_RE = new RegExp("^([" + EDGE + "]*)([\\s\\S]*?)([" + EDGE + "]*)$");
  function tx(s, dict) {
    const m = CORE_RE.exec(s), core = m[2];
    if (!core || !CYR_RE.test(core)) return s;
    const tr = (dict || UI)[core];
    return tr == null ? s : m[1] + tr + m[3];
  }
  // Надпись может быть куском разметки, даже разрезанным посередине тега: внутри тега переводятся только
  // значения атрибутов (куски между кавычками), снаружи — текст.
  function tparts(s, fn) {
    const lt = s.indexOf("<"), gt = s.indexOf(">");
    let inTag = gt >= 0 && (lt < 0 || gt < lt) || (lt < 0 && gt < 0), out = "", i = 0;
    while (i < s.length) {
      const j = s.indexOf(inTag ? ">" : "<", i);
      const end = j < 0 ? s.length : j;
      const chunk = s.slice(i, end);
      out += inTag ? chunk.split('"').map(fn).join('"') : fn(chunk);
      if (j < 0) break;
      out += s[j]; i = j + 1; inTag = !inTag;
    }
    return out;
  }
  function tl(s) {
    if (LANG === "ru" || typeof s !== "string" || !CYR_RE.test(s)) return s;
    return /[<>]|="/.test(s) ? tparts(s, (x) => tx(x)) : tx(s);
  }

  const STATUS = {
    "в работе": "work", "работа": "work", "work": "work",
    "на паузе": "pause", "пауза": "pause", "pause": "pause",
    "остановлен": "stop", "стоп": "stop", "stop": "stop",
    "план": "plan", "plan": "plan"
  };
  const STATUS_LABEL = { work: tl("В работе"), pause: tl("На паузе"), stop: tl("Остановлен"), plan: tl("План") };
  const SHARE_COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)"];
  // Словари, в которых ищут по именам из данных, — без прототипа: группа «constructor» или «toString» — обычный ключ.
  const GROUP_ICON = Object.assign(Object.create(null), { "Технологии": "⚙", "Учёба": "◎", "Книги": "✎", "Философия": "◈", "Игры": "⚑", "Развитие": "↗" });
  // Значки меню — картинки из папки icons (их отдаёт программа). Нет картинки — остаётся символ.
  const NAV_ICON = Object.assign(Object.create(null), { all: "obzor", calendar: "calendar", day: "dayplan", review: "review", stats: "stats", digest: "digest", reports: "reports",
    "Технологии": "tech", "Учёба": "study", "Книги": "books", "Философия": "philosophy", "Игры": "games", "Развитие": "growth",
    services: "services", research: "research", "idea-stats": "idea-stats", perf: "perf", alerts: "alerts" });
  const SET_ICON = Object.assign(Object.create(null), { hq: "ideas", main: "ideas" });
  // Значки из данных: ключ icons в projects.json дополняет встроенные — groups: {"Группа": {"symbol": "◆", "image": "имя"}},
  // idea_sets: {"id набора идей": "имя"}, reports: {"id раздела отчёта": "имя"}. Имя картинки — латиница, цифры, дефис,
  // до 40 знаков, как у сервера (ICON_PATH в pult/settings.py). При каждой нормализации словари собираются заново:
  // встроенные значки, потом значки из данных, так что удалённая настройка перестаёт действовать сразу.
  // Группа с именем встроенного раздела (all, calendar, …) картинку этого раздела не заменяет.
  const ICON_NAME_RE = /^[a-z0-9][a-z0-9-]{0,39}$/;
  let ICON_BASE = null;   // [словарь, его встроенная копия]; снимается при первом вызове, когда все файлы окна загружены
  let VIEW_KEYS = null;
  function applyDataIcons(data) {
    if (!ICON_BASE) {
      ICON_BASE = [GROUP_ICON, NAV_ICON, SET_ICON, RP_ICON].map((map) => [map, Object.freeze(Object.assign({}, map))]);
      VIEW_KEYS = new Set(Object.keys(NAV_ICON).filter((key) => !Object.prototype.hasOwnProperty.call(GROUP_ICON, key)));
    }
    ICON_BASE.forEach(([map, base]) => { Object.keys(map).forEach((key) => { delete map[key]; }); Object.assign(map, base); });
    const icons = data && data.icons && typeof data.icons === "object" && !Array.isArray(data.icons) ? data.icons : {};
    const each = (part, fn) => {
      const map = icons[part];
      if (map && typeof map === "object" && !Array.isArray(map)) Object.keys(map).forEach((key) => fn(key, map[key]));
    };
    each("groups", (name, v) => {
      if (!v || typeof v !== "object") return;
      if (typeof v.symbol === "string" && v.symbol.length > 0 && v.symbol.length <= 4) GROUP_ICON[name] = v.symbol;
      if (typeof v.image === "string" && ICON_NAME_RE.test(v.image) && !VIEW_KEYS.has(name)) NAV_ICON[name] = v.image;
    });
    each("idea_sets", (id, v) => { if (typeof v === "string" && ICON_NAME_RE.test(v)) SET_ICON[id] = v; });
    each("reports", (id, v) => { if (typeof v === "string" && ICON_NAME_RE.test(v)) RP_ICON[id] = v; });
  }
  // Стиль значков: «base» — прежние символы, иначе картинки стиля из icons\<папка стиля>.
  const ICON_MISSING = new Set();
  let setLocal = {};
  function iconStyle() {
    const s = Object.assign({}, window.BOARD && window.BOARD.settings, setLocal).icons;
    return typeof s === "string" && /^[a-z0-9][a-z0-9-]{0,29}$/.test(s) ? s : "base";
  }
  function iconImg(style, name, sym) {
    const key = style + "/" + name;
    if (!name || style === "base" || location.protocol !== "http:" || ICON_MISSING.has(key)) return esc(sym);
    return '<img src="/icons/' + style + '/' + name + '.png" alt="" draggable="false" data-ic="' + key + '" data-sym="' + esc(sym) + '">';
  }
  function navIcon(name, sym) { return iconImg(iconStyle(), name, sym); }
  document.addEventListener("error", (e) => {
    const img = e.target;
    if (!img || img.tagName !== "IMG" || !img.dataset || !img.dataset.ic) return;
    ICON_MISSING.add(img.dataset.ic);
    img.replaceWith(document.createTextNode(img.dataset.sym || ""));
  }, true);
  // Отдел «Развитие» — личные планы (карьера, оборудование, заработок): свой раздел, в «Обзор» не входит, тревог не даёт.
  const DEV = "Развитие";
  const DAY = 86400000;
  const state = { view: decodeURIComponent(location.hash.slice(1)) || "all", period: 30, open: null, ideaFilter: "all" };
  const IDEA_KIND = { road: tl("В дорожной карте"), done: tl("Сделано"), explore: tl("Исследовать"), idea: tl("Идеи и наброски"), decision: tl("Решения CEO"), future: tl("На будущее"), wait: tl("Ждут и отложены"), dropped: tl("Отказались") };
  function ideaKind(status) {
    const s = String(status || "").toLowerCase();
    if (s.startsWith("сделано")) return "done";
    if (s.startsWith("в дорожной карте")) return "road";
    if (s.startsWith("решение")) return "decision";   // решение, ещё не выполнено — не идея
    if (s.includes("исследовать")) return "explore";
    if (s.startsWith("отказ")) return "dropped";
    if (s.startsWith("ждёт") || s.startsWith("ждет") || s.startsWith("отлож")) return "wait";
    if (s.startsWith("идея") && s.includes("на будущее")) return "future";   // отложена сознательно, не забыта
    return "idea";
  }
  // Итоги идей для аналитики: порядок в полосах и цвета (палитра проверена; на полке — нарочно серый).
  const OUTCOMES = [
    { k: "done", name: tl("Воплощены"), color: "var(--k-done)" },
    { k: "road", name: tl("В проекте"), color: "var(--k-road)" },
    { k: "explore", name: tl("Проверяются"), color: "var(--k-explore)" },
    { k: "decision", name: tl("Решения CEO"), color: "var(--k-decision)" },
    { k: "wait", name: tl("На паузе"), color: "var(--k-wait)" },
    { k: "future", name: tl("На будущее"), color: "var(--k-future)" },
    { k: "idea", name: tl("На полке"), color: "var(--k-shelf)" },
    { k: "dropped", name: tl("Отказались"), color: "var(--k-dropped)" }
  ];
  const OUT = Object.fromEntries(OUTCOMES.map((o) => [o.k, o]));
  // Общий уровень производительности: веса частей (в сумме 1). Поменять формулу — здесь.
  const PERF_WEIGHTS = { move: 0.5, real: 0.25, sorted: 0.25 };
  // Подотделы раздела «Идеи»: view "ideas" — первый набор идей, "ideas:<id>" — остальные (идеи проекта…).
  const ideaView = (set, i) => i === 0 ? "ideas" : "ideas:" + set.id;
  function ideaSetOf(view) {
    if (!board || !board.ideaSets.length || !String(view || "").startsWith("ideas")) return null;
    return view === "ideas" ? board.ideaSets[0] : board.ideaSets.find((x, i) => i > 0 && view === "ideas:" + x.id) || null;
  }
  let board = null;
  let lastText = "";

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const parseDate = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ""); return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null; };
  const today = () => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), d.getDate()); };
  const fmt = (d) => d ? String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0") + "." + d.getFullYear() : "—";
  const fmtShort = (d) => String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0");
  const daysAgo = (d) => d ? Math.round((today() - d) / DAY) : null;
  const pluralRu = (n, one, few, many) => { const a = Math.abs(n) % 100, b = a % 10; if (a > 10 && a < 20) return many; if (b > 1 && b < 5) return few; if (b === 1) return one; return many; };
  // Другие языки: формы из i18n.js по русским формам, правило числа — Intl.PluralRules (CLDR).
  const PLURAL_RULES = LANG === "ru" ? null : new Intl.PluralRules(LANG);
  const plural = (n, one, few, many) => {
    const forms = LANG === "ru" ? null : ((I18N.plural || {})[LANG] || {})[one + "|" + few + "|" + many];
    if (!forms) return pluralRu(n, one, few, many);
    return forms[PLURAL_RULES.select(n)] || forms.other;
  };
  const daysText = (n) => n === 0 ? tl("сегодня") : n === 1 ? tl("вчера") :
    LANG === "he" ? "לפני " + n + " " + plural(n, "день", "дня", "дней") : n + " " + plural(n, "день", "дня", "дней") + tl(" назад");

  // Данные (названия проектов, групп, этапов, описания, события) — из translations.json через data.js.
  // Словарь без прототипа: название «constructor» или «toString» переводится как обычная строка.
  let DATA_TR = Object.create(null);
  const EVENT_PREFIX = ["Пройден блок", "Начат блок", "Слит", "Начат"];
  // Идеи: перевод только целой строкой из translations.json; оригинал в базе идей не меняется; нет перевода — по-русски.
  const trIdea = (s) => (LANG === "ru" || typeof s !== "string" || !s || DATA_TR[s] == null) ? s : DATA_TR[s];
  const trNote = (n) => (LANG === "ru" || !n || typeof n !== "object") ? n :
    Object.assign({}, n, { text: trIdea(n.text), sub: Array.isArray(n.sub) ? n.sub.map(trIdea) : n.sub, labelShown: trIdea(n.label) });
  function td(s) {
    if (LANG === "ru" || typeof s !== "string" || !s) return s;
    if (DATA_TR[s] != null) return DATA_TR[s];
    for (const p of EVENT_PREFIX) {
      if (s.startsWith(p + " ") && DATA_TR[p] != null) { const rest = s.slice(p.length + 1); return DATA_TR[p] + " " + (DATA_TR[rest] != null ? DATA_TR[rest] : rest); }
    }
    return s;
  }

  // Текст, который ввёл человек (задача дня): сначала данные, потом обычные надписи («1 урок»).
  function tdt(s) { const d = td(s); return d !== s ? d : tl(s); }

  function normalize(data) {
    const tr = data.translations && data.translations[LANG];
    DATA_TR = Object.assign(Object.create(null), tr && typeof tr === "object" ? tr : {});
    applyDataIcons(data);
    const projects = (data.projects || []).map((p) => {
      const stages = (Array.isArray(p.stages) ? p.stages : []).map(td);
      const current = Math.max(0, Math.min(Number.isInteger(p.current) ? p.current : 0, Math.max(stages.length - 1, 0)));
      const status = STATUS[String(p.status || "").trim().toLowerCase()] || "pause";
      // Движение — последнее из двух: смена этапа или работа по данным проекта (кнопка «Синхронизировать данные»).
      const act = p.auto && p.auto.activity ? parseDate(p.auto.activity.date) : null;
      const moved = parseDate(p.last_move);
      const last = act && (!moved || act > moved) ? act : moved;
      return {
        id: p.id || p.name, name: td(p.name) || tl("Без названия"), group: p.group || tl("Другое"), status, stages, current,
        movesWith: Array.isArray(p.moves_with) ? p.moves_with.map(String) : [],
        about: td(p.about) || "", link: /^https:\/\//.test(p.link || "") ? p.link : "", auto: p.auto || null,
        last, ownLast: last, days: daysAgo(last),
        done: current, total: stages.length,
        percent: stages.length ? Math.round(current / stages.length * 100) : 0
      };
    });
    // Общий план движется вместе со своими проектами (поле moves_with в projects.json): движение — последнее из всех.
    projects.forEach((p) => {
      if (!p.movesWith.length) return;
      projects.forEach((c) => { if (c !== p && p.movesWith.includes(c.id) && c.ownLast && (!p.last || c.ownLast > p.last)) p.last = c.ownLast; });
      p.days = daysAgo(p.last);
    });
    const history = (data.history || []).map((h) => ({ date: parseDate(h.date), project: h.project, text: td(h.text) || "", raw: String(h.text || ""), auto: !!h.auto }))
      .filter((h) => h.date).sort((a, b) => b.date - a.date);
    const groups = Array.isArray(data.groups) && data.groups.length ? data.groups : [...new Set(projects.map((p) => p.group))];
    // Каждый файл идей — свой подотдел. Старый data.js знает только data.ideas (один файл).
    const rawSets = Array.isArray(data.idea_sets) && data.idea_sets.length ? data.idea_sets :
      data.ideas ? [Object.assign({ id: "hq", title: tl("Идеи") }, data.ideas)] : [];
    const ideaSets = rawSets.map((set, i) => {
      const items = (set.items || []).map((it) => ({
        id: String(it.id || ""), date: parseDate(it.date), title: trIdea(it.title || it.id || ""), fullTitle: trIdea(it.full_title || ""),
        status: trIdea(it.status || ""), kind: it.kind && it.kind !== "idea" ? it.kind : ideaKind(it.status), notes: Array.isArray(it.notes) ? it.notes.map(trNote) : [],
        project: it.project || "", links: Array.isArray(it.links) ? it.links.map(String) : []
      }));
      const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(set.updated || "");
      return { id: String(set.id || "set" + (i + 1)), title: !set.title || set.title === "Идеи" ? tl("Идеи") : td(set.title) || tl("Идеи"), about: td(set.about) || "", error: set.error || "", source: set.source || "", items, fromDb: !!set.from_db,
        updated: m ? m[3] + "." + m[2] + "." + m[1] + " " + m[4] + ":" + m[5] : "" };
    });
    const ideas = ideaSets[0] || null;
    const ih = data.idea_history || {};
    const ideaHistory = { started: parseDate(ih.started), error: ih.error || "", fromDb: !!ih.from_db,
      transitions: (Array.isArray(ih.transitions) ? ih.transitions : []).map((t) => ({ date: parseDate(t.date), set: t.set, id: t.id, from: t.from, to: t.to })).filter((t) => t.date),
      bornDone: (Array.isArray(ih.born_done) ? ih.born_done : []).map((t) => ({ date: parseDate(t.date), set: t.set, id: t.id, from: "", to: "done" })).filter((t) => t.date) };
    return { updated: parseDate(data.updated), focus: data.focus, groups, projects, history, ideas, ideaSets, ideaHistory, sync: data.sync || null,
      stats: data.stats && typeof data.stats === "object" ? data.stats : null,
      ideaSource: data.idea_source || null, calendar: normCalendar(data.calendar),
      alerts: data.alerts && typeof data.alerts === "object" ? data.alerts : {},
      services: data.services && typeof data.services === "object" ? data.services : {},
      research: data.research && Array.isArray(data.research.entries) ? data.research : { entries: [], error: "" },
      reports: data.reports && Array.isArray(data.reports.entries) ? data.reports : { entries: [], dir: "", error: "" },
      dayCarried: Array.isArray(data.day_carried) ? data.day_carried.filter((c) => c && typeof c.carries === "number") : [],
      answers: Array.isArray(data.answers) ? data.answers.filter((a) => a && a.file) : [],
      requests: Array.isArray(data.requests) ? data.requests.filter((r) => r && r.id) : [],
      proposalMarks: data.proposal_marks && typeof data.proposal_marks === "object" ? data.proposal_marks : {} };
  }

  // Ключ тревоги: проект, вид и то, от чего она зависит (этап или дата последнего движения). Причина сменилась —
  // ключ новый, и прежняя отметка («в починке», «убрана») к новой тревоге не относится.
  const alertKey = (p, kind) => p.id + "|" + kind + "|" + (kind === "stop" ? p.current : p.last ? dayKey(p.last) : "");
  function allAlertsOf(p) {
    if (p.status === "plan") return [];
    if (p.status === "stop") return [{ key: alertKey(p, "stop"), project: p.id, level: "critical", title: tl("Проект остановлен"), text: p.name + ": " + (p.stages[p.current] || "") }];
    if (p.status === "work" && p.days != null && p.days > 14) return [{ key: alertKey(p, "idle"), project: p.id, level: "warning", title: tl("Без движения ") + p.days + " " + plural(p.days, "день", "дня", "дней"), text: p.name + tl(" в работе, но этап давно не менялся") }];
    if (p.status === "pause" && p.days != null && p.days > 30) return [{ key: alertKey(p, "pause"), project: p.id, level: "info", title: tl("Давно на паузе"), text: p.name + ": " + p.days + " " + plural(p.days, "день", "дня", "дней") + tl(" без движения") }];
    return [];
  }
  const alertMark = (a) => (board && board.alerts && board.alerts[a.key]) || null;
  // Отдел услуг: реестр услуг Пульта (flags.json). Услуга закреплена: флажок снимается и ставится, услуга остаётся;
  // убрать услугу совсем — отдельная кнопка с подтверждением. База идей не меняется.
  const serviceOf = (id) => (board && board.services && board.services[id]) || null;
  const flagMark = (id) => {
    const sv = serviceOf(id);
    if (!sv) return "";
    return sv.flag ? '<span class="svc-flag" title="' + esc(tl("Наша услуга")) + '" aria-label="' + esc(tl("Наша услуга")) + '">⚑</span>'
      : '<span class="svc-flag off" title="' + esc(tl("Флажок снят")) + '" aria-label="' + esc(tl("Флажок снят")) + '">⚐</span>';
  };
  const servicesList = () => board.ideaSets.flatMap((set) => set.items.filter((it) => serviceOf(it.id)).map((it) => ({ it, set })));
  let svcDelAsk = "";  // номер услуги, для которой открыт вопрос «Убрать из услуг?»
  const markOf = (a) => (alertMark(a) || {}).state || "";
  // Тревоги на экране — все, кроме убранных; «в починке» видны, но в счёт тревог не входят.
  const alertsOf = (p) => allAlertsOf(p).filter((a) => markOf(a) !== "dismissed");
  const dismissedOf = (p) => allAlertsOf(p).filter((a) => markOf(a) === "dismissed");
  // Тревоги без проекта: задача переносится «на завтра», отчёт недели не отправлен,
  // решения давно ждут. Пороги: 3 переноса, 2 дня после конца недели, 30 дней. Видны в «Обзоре» и «Тревогах».
  const SYS_CARRY = 3, SYS_REPORT_DAYS = 2, SYS_DECISION_DAYS = 30;
  function sysAlertsAll() {
    if (!board) return [];
    const out = [], now = today();
    (board.dayCarried || []).forEach((c) => {
      if (c.carries < SYS_CARRY) return;
      const p = c.project_id ? board.projects.find((x) => x.id === c.project_id) : null, first = parseDate(c.first_day);
      out.push({ key: "sys|carry|" + c.root + "|" + c.carries, project: p ? p.id : "", level: "warning",
        title: tl("Переносов на завтра") + ": " + c.carries,
        text: "«" + tdt(c.title) + "»" + (p ? " · " + p.name : "") + (first ? " · " + tl("впервые в плане") + " " + fmtShort(first) : "") });
    });
    ((board.reports || {}).entries || []).forEach((r) => {
      const end = parseDate(r.end);
      if (r.pushed !== false || !end || Math.floor((now - end) / DAY) < SYS_REPORT_DAYS) return;
      out.push({ key: "sys|report|" + r.file, project: "", level: "warning", title: tl("Отчёт недели не отправлен на GitHub"),
        text: rpWeek(r) + ": " + tl("отчёт лежит в папке, но на GitHub его нет") });
    });
    const since = {};
    ((board.ideaHistory || {}).transitions || []).forEach((t) => { if (t.to === "decision" && (!since[t.id] || t.date > since[t.id])) since[t.id] = t.date; });
    const by = {};
    let old = 0;
    (board.ideaSets || []).forEach((set) => set.items.forEach((it) => {
      if (it.kind !== "decision") return;
      const d = since[it.id] || (it.date instanceof Date ? it.date : parseDate(it.date));
      if (d && Math.floor((now - d) / DAY) > SYS_DECISION_DAYS) { old++; by[set.id] = (by[set.id] || 0) + 1; }
    }));
    if (old) {
      const sets = board.ideaSets.filter((x) => by[x.id]).sort((a, b) => by[b.id] - by[a.id]);
      out.push({ key: "sys|decisions|" + old, project: "", level: "info", open: ideaView(sets[0], board.ideaSets.indexOf(sets[0])),
        title: tl("Решения CEO ждут дольше 30 дней") + ": " + old,
        text: sets.map((x) => (board.ideaSets.indexOf(x) ? x.title : tl("Идеи")) + " — " + by[x.id]).join(" · ") });
    }
    return out;
  }
  const sysShown = () => state.view === "all" || state.view === "alerts";
  const sysAlerts = () => sysAlertsAll().filter((a) => markOf(a) !== "dismissed");
  const sysDismissed = () => sysAlertsAll().filter((a) => markOf(a) === "dismissed");
  const isAlarm = (a) => (a.level === "critical" || a.level === "warning") && !markOf(a);
  const isRepair = (a) => markOf(a) === "repair";

  function visibleProjects() {
    if (state.view === "all") return board.projects.filter((p) => p.group !== DEV);
    if (state.view === "alerts") return board.projects.filter((p) => alertsOf(p).length);
    return board.projects.filter((p) => p.group === state.view);
  }

  function ring(percent, color, label) {
    const r = 24, c = 2 * Math.PI * r, v = Math.max(0, Math.min(100, percent));
    return '<svg class="ring" width="62" height="62" viewBox="0 0 62 62" role="img" aria-label="' + esc(label) + '">' +
      '<circle cx="31" cy="31" r="' + r + '" fill="none" stroke="' + color + '" stroke-opacity=".18" stroke-width="7"/>' +
      (v > 0 ? '<circle cx="31" cy="31" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="7" stroke-linecap="round" ' +
      'stroke-dasharray="' + (c * v / 100).toFixed(1) + ' ' + c.toFixed(1) + '" transform="rotate(-90 31 31)"/>' : '') +
      '<text x="31" y="35" text-anchor="middle" fill="var(--text)" font-size="12" font-weight="700">' + Math.round(v) + '%</text></svg>';
  }

  function renderNav() {
    const all = board.projects;
    const alarms = all.filter((p) => alertsOf(p).some(isAlarm)).length + sysAlerts().filter(isAlarm).length;
    const items = [["all", "▦", tl("Обзор"), all.filter((p) => p.group !== DEV).length]].concat(board.groups.map((g) => [g, GROUP_ICON[g] || "•", td(g), all.filter((p) => p.group === g).length]));
    const navBtn = ([key, icon, label, count]) =>
      '<button type="button" data-view="' + esc(key) + '" class="' + (state.view === key ? "active" : "") + '"><span class="icon">' + navIcon(NAV_ICON[key], icon) + '</span>' + esc(label) +
      '<span class="count">' + count + '</span></button>';
    let html = navBtn(items[0]) + navBtn(["calendar", "▤", tl("Календарь"), calTodayCount()]) + navBtn(["day", "☑", tl("План дня"), dayLeftCount()]) + navBtn(["review", "▥", tl("Итоги дней"), rvWeekPercent()]) +
      navBtn(["stats", "▧", tl("Статистика"), ""]) + navBtn(["digest", "✉", tl("Сводки"), dgCount()]) +
      navBtn(["reports", "▨", tl("Отчёты"), rpAll().length]) + navBtn(["proposals", "✧", tl("Предложения"), prOpen()]) + items.slice(1).map(navBtn).join("");
    board.ideaSets.forEach((set, i) => {
      const key = ideaView(set, i);
      html += '<button type="button" data-view="' + esc(key) + '" class="' + (i ? "subnav " : "") + (state.view === key ? "active" : "") + '"><span class="icon">' + navIcon(SET_ICON[set.id], i ? "◇" : "✦") + '</span>' +
        esc(i ? set.title : tl("Идеи")) + '<span class="count">' + set.items.length + '</span></button>';
    });
    if (board.ideaSets.length) {
      html += '<button type="button" data-view="services" class="subnav ' + (state.view === "services" ? "active" : "") + '"><span class="icon svc-icon">' + navIcon(NAV_ICON.services, "⚑") + '</span>' + esc(tl("Наши услуги")) +
        '<span class="count">' + servicesList().length + '</span></button>';
    }
    html += '<button type="button" data-view="research" class="' + (state.view === "research" ? "active" : "") + '"><span class="icon">' + navIcon(NAV_ICON.research, "▣") + '</span>' + esc(tl("Исследования")) +
      '<span class="count">' + rsList().length + '</span></button>';
    if (board.ideaSets.length) {
      const total = board.ideaSets.reduce((a, s) => a + s.items.length, 0);
      html += '<button type="button" data-view="idea-stats" class="subnav ' + (state.view === "idea-stats" ? "active" : "") + '"><span class="icon">' + navIcon(NAV_ICON["idea-stats"], "◇") + '</span>' + esc(tl("Аналитика идей")) +
        '<span class="count">' + total + '</span></button>';
    }
    html += '<button type="button" data-view="perf" class="' + (state.view === "perf" ? "active" : "") + '"><span class="icon">' + navIcon(NAV_ICON.perf, "◉") + '</span>' + esc(tl("Общий уровень")) +
      '<span class="count">' + perfScore().total + '%</span></button>';
    html += '<button type="button" data-view="alerts" class="' + (state.view === "alerts" ? "active" : "") + '"><span class="icon">' + navIcon(NAV_ICON.alerts, "⚠") + '</span>' + esc(tl("Тревоги")) +
      (alarms ? '<span class="badge">' + alarms + '</span>' : '<span class="count">0</span>') + '</button>';
    $("nav").innerHTML = html;
  }

  function renderFocus() {
    const p = board.projects.find((x) => x.id === board.focus) || board.projects.find((x) => x.status === "work");
    const box = $("focus");
    if (!p) { box.innerHTML = ""; box.removeAttribute("data-open"); box.removeAttribute("tabindex"); return; }
    box.dataset.open = p.id; box.tabIndex = 0; box.setAttribute("aria-label", tl("Все этапы: ") + p.name);
    const next = p.stages[p.current + 1];
    $("focus").innerHTML = tl('<div class="label">ФОКУС</div><div class="name">') + esc(p.name) + '</div>' +
      tl('<div class="now">Сейчас: ') + esc(p.stages[p.current] || "—") + '</div>' +
      '<div class="big">' + p.percent + '%</div><div class="meter"><span style="width:' + p.percent + '%"></span></div>' +
      tl('<div class="small">Пройдено ') + p.done + tl(' из ') + p.total + ' ' + plural(p.total, "этапа", "этапов", "этапов") + '</div>' +
      (next ? tl('<div class="small">Следующий: ') + esc(next) + '</div>' : "");
  }

  function eventsInPeriod(list) {
    const from = new Date(today() - (state.period - 1) * DAY);
    const ids = new Set(list.map((p) => p.id));
    return board.history.filter((h) => h.date >= from && ids.has(h.project));
  }

  function renderTiles(list) {
    const n = list.length || 1;
    const count = (s) => list.filter((p) => p.status === s).length;
    const ev = eventsInPeriod(list);
    const avg = list.length ? Math.round(list.reduce((a, p) => a + p.percent, 0) / list.length) : 0;
    const groups = new Set(list.map((p) => p.group)).size;
    const tiles = [
      '<div class="card tile"><div class="text"><div class="tlabel">' + (state.view === DEV ? tl("Направлений") : tl("Всего проектов")) + '</div><div class="value">' + list.length + tl('</div><div class="note">в ') + groups + ' ' + plural(groups, "группе", "группах", "группах") + '</div></div></div>',
      '<div class="card tile">' + ring(count("work") / n * 100, "var(--good)", tl("Доля в работе")) + tl('<div class="text"><div class="tlabel">В работе</div><div class="value">') + count("work") + tl('</div><div class="note">горит зелёным</div></div></div>'),
      '<div class="card tile">' + ring(count("pause") / n * 100, "var(--serious)", tl("Доля на паузе")) + tl('<div class="text"><div class="tlabel">На паузе</div><div class="value">') + count("pause") + tl('</div><div class="note">горит оранжевым</div></div></div>'),
      '<div class="card tile">' + ring(count("stop") / n * 100, "var(--critical)", tl("Доля остановленных")) + tl('<div class="text"><div class="tlabel">Остановлено</div><div class="value">') + count("stop") + tl('</div><div class="note">горит красным</div></div></div>'),
      tl('<div class="card tile"><div class="text"><div class="tlabel">Сдвигов этапов</div><div class="value">') + ev.length + tl('</div><div class="note">за ') + state.period + ' ' + plural(state.period, "день", "дня", "дней") + (ev[0] ? tl(' · последний ') + fmtShort(ev[0].date) : "") + '</div></div></div>',
      '<div class="card tile">' + ring(avg, "var(--series-1)", tl("Средний прогресс")) + tl('<div class="text"><div class="tlabel">Средний прогресс</div><div class="value">') + avg + tl('%</div><div class="note">этапов пройдено</div></div></div>')
    ];
    $("tiles").innerHTML = tiles.join("");
  }

  function renderActivity(list) {
    const days = state.period, end = today(), start = new Date(end - (days - 1) * DAY);
    const buckets = Array.from({ length: days }, (_, i) => ({ date: new Date(start.getTime() + i * DAY), items: [] }));
    for (const h of eventsInPeriod(list)) {
      const i = Math.round((h.date - start) / DAY);
      if (buckets[i]) buckets[i].items.push(h);
    }
    const max = Math.max(1, ...buckets.map((b) => b.items.length));
    const top = max <= 4 ? max : Math.ceil(max / 2) * 2;
    const W = Math.max(320, Math.round($("activity").clientWidth || 640)), H = 220, L = 30, R = 8, T = 10, B = 26, pw = W - L - R, ph = H - T - B;
    const slot = pw / days, bw = Math.min(24, Math.max(3, slot * 0.6));
    const y = (v) => T + ph - v / top * ph;
    let svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + tl('" role="img" aria-label="Активность по дням">');
    const step = top <= 4 ? 1 : top / 2;
    for (let v = 0; v <= top; v += step) {
      svg += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="' + (v === 0 ? "var(--axis)" : "var(--grid)") + '" stroke-width="1"/>' +
        '<text class="axis-text" x="' + (L - 6) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + v + '</text>';
    }
    const labelEvery = days <= 30 ? 5 : 15;
    buckets.forEach((b, i) => {
      const x = L + i * slot + (slot - bw) / 2, n = b.items.length;
      if (n) {
        const h = Math.max(2, n / top * ph), r = Math.min(4, bw / 2, h);
        const x0 = x, x1 = x + bw, y1 = y(0), y0 = y1 - h;
        svg += '<path fill="var(--series-1)" d="M' + x0 + ' ' + y1 + 'V' + (y0 + r) + 'Q' + x0 + ' ' + y0 + ' ' + (x0 + r) + ' ' + y0 +
          'H' + (x1 - r) + 'Q' + x1 + ' ' + y0 + ' ' + x1 + ' ' + (y0 + r) + 'V' + y1 + 'Z"/>';
      }
      if ((days - 1 - i) % labelEvery === 0) {
        svg += '<text class="axis-text" x="' + (L + i * slot + slot / 2) + '" y="' + (H - 8) + '" text-anchor="middle">' + fmtShort(b.date) + '</text>';
      }
      const lines = b.items.map((h) => '<div class="l">' + esc(nameOf(h.project)) + ': ' + esc(h.text) + '</div>').join("") || tl('<div class="l">Сдвигов не было</div>');
      svg += '<rect x="' + (L + i * slot) + '" y="' + T + '" width="' + slot + '" height="' + ph + '" fill="transparent" tabindex="0" data-tip="' +
        esc('<div class="t">' + fmt(b.date) + ' · ' + n + ' ' + plural(n, "сдвиг", "сдвига", "сдвигов") + '</div>' + lines) + '"/>';
    });
    svg += "</svg>";
    $("activity").innerHTML = svg;
    $("activity-sub").textContent = tl("Сколько раз сдвигались этапы, по дням (") + fmtShort(start) + " — " + fmtShort(end) + ")";
  }

  function nameOf(id) { const p = board.projects.find((x) => x.id === id); return p ? p.name : id; }

  function renderProgress(list) {
    if (!list.length) { $("progress").innerHTML = tl('<div class="empty">Здесь нет проектов</div>'); return; }
    $("progress").innerHTML = '<div class="bars">' + list.map((p) =>
      '<div class="bar-row" tabindex="0" data-open="' + esc(p.id) + '" data-tip="' + esc('<div class="t">' + esc(p.name) + tl('</div><div class="l">Пройдено ') + p.done + tl(' из ') + p.total +
        ' ' + plural(p.total, "этапа", "этапов", "этапов") + tl('</div><div class="l">Сейчас: ') + esc(p.stages[p.current] || "—") + tl('</div><div class="l">Нажмите — откроются все этапы</div>')) + '">' +
      '<div class="bname">' + esc(p.name) + '</div>' +
      '<div class="track"><div class="fill" style="width:' + p.percent + '%"></div></div>' +
      '<div class="bval">' + p.percent + '% · ' + p.done + '/' + p.total + '</div></div>').join("") + '</div>';
  }

  function renderShare(list) {
    const ev = eventsInPeriod(list);
    $("share-sub").textContent = tl("Доля сдвигов этапов за ") + state.period + " " + plural(state.period, "день", "дня", "дней");
    if (!ev.length) { $("share").innerHTML = tl('<div class="empty">За этот период сдвигов не было</div>'); return; }
    const counts = new Map();
    ev.forEach((h) => counts.set(h.project, (counts.get(h.project) || 0) + 1));
    // Colour follows the project, not its rank: slots go by the project's place in the list.
    const order = board.projects.map((p) => p.id).filter((id) => counts.has(id));
    const ranked = order.slice().sort((a, b) => counts.get(b) - counts.get(a) || order.indexOf(a) - order.indexOf(b));
    const shown = ranked.slice(0, ranked.length > 4 ? 3 : 4);
    const rest = ranked.filter((id) => !shown.includes(id));
    const shownInListOrder = order.filter((id) => shown.includes(id));
    const items = shownInListOrder.map((id, i) => ({ name: nameOf(id), n: counts.get(id), color: SHARE_COLORS[i] }));
    if (rest.length) items.push({ name: tl("Другие (") + rest.length + ")", n: rest.reduce((a, id) => a + counts.get(id), 0), color: "var(--other)" });
    const total = ev.length;
    $("share").innerHTML = '<div class="stack">' + items.map((it) =>
      '<span tabindex="0" style="flex:' + it.n + ';background:' + it.color + '" data-tip="' + esc('<div class="t">' + esc(it.name) + '</div><div class="l">' + it.n + ' ' +
        plural(it.n, "сдвиг", "сдвига", "сдвигов") + ' · ' + Math.round(it.n / total * 100) + '%</div>') + '"></span>').join("") + '</div>' +
      '<div class="legend">' + items.map((it) => '<div class="item"><span class="dot" style="background:' + it.color + '"></span><span class="lname">' + esc(it.name) +
        '</span><span class="num">' + it.n + '</span><span class="pct">' + Math.round(it.n / total * 100) + '%</span></div>').join("") + '</div>';
  }

  function renderTable(list) {
    if (!list.length) { $("table").innerHTML = tl('<tr><td class="empty">Здесь нет проектов</td></tr>'); return; }
    const chip = (kind, label, text) => '<div class="chip ' + kind + '"><small>' + label + '</small><span>' + esc(text || "—") + '</span></div>';
    $("table").innerHTML = tl('<colgroup><col class="c-name"><col class="c-status"><col><col class="c-progress"><col class="c-days"></colgroup><thead><tr><th>Проект</th><th>Статус</th><th>Этапы</th><th>Прогресс</th><th>Движение</th></tr></thead><tbody>') +
      list.map((p) => '<tr data-open="' + esc(p.id) + '" tabindex="0" aria-label="' + esc(tl("Все этапы: ") + p.name) + '"><td><div class="pname">' + esc(p.name) + '</div><div class="pgroup">' + esc(td(p.group)) +
        ' · <span class="more">' + p.total + ' ' + plural(p.total, "этап", "этапа", "этапов") + ' ›</span></div></td>' +
        '<td><span class="lamp ' + p.status + '"><i></i><span>' + STATUS_LABEL[p.status] + '</span></span></td>' +
        '<td><div class="chainbox"><div class="chain">' + chip("past", tl("БЫЛ"), p.stages[p.current - 1]) + '<span class="arrow">→</span>' + chip("now", tl("СЕЙЧАС"), p.stages[p.current]) +
        '<span class="arrow">→</span>' + chip("", tl("ДАЛЬШЕ"), p.stages[p.current + 1]) + '<span class="arrow">→</span>' + chip("", tl("ПОТОМ"), p.stages[p.current + 2]) + '</div></div></td>' +
        '<td><div class="mini"><div class="meter"><span style="width:' + p.percent + '%"></span></div><div class="pct">' + p.percent + '% · ' + p.done + '/' + p.total + '</div></div></td>' +
        '<td><span class="days' + (p.days > 30 ? " old" : "") + '">' + (p.days == null ? "—" : daysText(p.days)) + '</span></td></tr>').join("") + '</tbody>';
  }

  function renderFeed(list) {
    const alerts = sysShown() ? sysAlerts() : [];
    list.forEach((p) => alertsOf(p).forEach((a) => alerts.push(a)));
    const rank = { critical: 0, warning: 1, info: 2 };
    alerts.sort((a, b) => rank[a.level] - rank[b.level]);
    const ico = { critical: "⛔", warning: "⚠", info: "ℹ", done: "✓" };
    const events = eventsInPeriod(list).slice(0, 6);
    const dismissed = sysShown() ? sysDismissed() : [];
    list.forEach((p) => dismissedOf(p).forEach((a) => dismissed.push(a)));
    const btn = (act, a, label) => '<button type="button" class="albtn" data-al="' + act + '" data-key="' + esc(a.key) + '">' + esc(tl(label)) + '</button>';
    const alertHtml = (a, gone) => {
      const m = alertMark(a), repair = !gone && m && m.state === "repair", since = m && parseDate(m.at);
      return '<div class="ev ' + a.level + (repair ? " repair" : "") + (gone ? " dismissed" : "") + '"><div class="head"><span class="ico">' + ico[a.level] + '</span>' + esc(a.title.toUpperCase()) +
        (repair ? '<span class="altag">' + esc(tl("В ПОЧИНКЕ")) + (since ? " · " + fmtShort(since) : "") + '</span>' : "") +
        '</div><div class="body">' + esc(a.text) + '</div><div class="albtns">' +
        (gone ? btn("active", a, "Вернуть") : repair ? btn("dismissed", a, "Убрать") + btn("active", a, "Вернуть") : btn("repair", a, "Починить") + btn("dismissed", a, "Убрать")) +
        (a.open && !gone ? '<button type="button" class="albtn" data-alopen="' + esc(a.open) + '">' + esc(tl("Открыть")) + '</button>' : "") +
        (gone ? "" : planBtn("al:" + a.key, a.title + ": " + a.text, a.project, tl("Из тревоги"))) + '</div></div>';
    };
    const html = alerts.map((a) => alertHtml(a, false))
      .concat(dismissed.length ? ['<button type="button" class="allink" data-al="toggle">' + esc(state.alShowGone ? tl("Скрыть убранные") : tl("Убранные: ") + dismissed.length) + '</button>'] : [])
      .concat(dismissed.length && state.alShowGone ? dismissed.map((a) => alertHtml(a, true)) : [])
      .concat(events.map((h) => '<div class="ev done"><div class="head"><span class="ico">✓</span>' +
      esc(nameOf(h.project).toUpperCase()) + '</div><div class="body">' + esc(h.text) + '</div><div class="when">' + fmt(h.date) + '</div></div>'));
    $("feed").innerHTML = html.join("") || tl('<div class="empty">Ни тревог, ни событий за этот период</div>');
  }

  function renderBottom(list) {
    const all = board.projects;
    const count = (s) => list.filter((p) => p.status === s).length;
    const sys = sysShown() ? sysAlerts() : [];
    const alarms = list.filter((p) => alertsOf(p).some(isAlarm)).length + sys.filter(isAlarm).length;
    const repairing = list.reduce((n, p) => n + alertsOf(p).filter(isRepair).length, 0) + sys.filter(isRepair).length;
    const last = board.history.find((h) => list.some((p) => p.id === h.project));
    $("bottom").innerHTML = tl('<span class="title">✓ ИТОГ НА ') + fmt(today()) + '</span>' +
      tl('<span>В работе: <b>') + count("work") + tl('</b></span><span>На паузе: <b>') + count("pause") + tl('</b></span><span>Остановлено: <b>') + count("stop") + '</b></span>' +
      (last ? tl('<span class="lastmove">Последний сдвиг: <b>') + esc(nameOf(last.project)) + '</b> — ' + esc(last.text) + ' (' + fmt(last.date) + ')</span>' : "") +
      '<span class="pill ' + (alarms ? "alarm" : "calm") + '">' + (alarms ? tl("ТРЕВОГ: ") + alarms : tl("ВСЁ СПОКОЙНО")) + '</span>' +
      (repairing ? '<span class="pill repair">' + tl("В ПОЧИНКЕ: ") + repairing + '</span>' : "");
    void all;
  }

  // Ideas: the registry IDEAS.md, read by the launcher at start (the file itself is never changed).
  const ideaChip = (it) => '<span class="ichip ' + it.kind + '"><i></i><span>' + esc(it.status || "—") + '</span></span>';
  function renderIdeas() {
    const box = $("ideas"), I = ideaSetOf(state.view);
    if (!I || I.error) {
      box.innerHTML = '<div class="card"><div class="empty">' + esc(I ? I.error : tl("Файл с идеями не указан (ideas_files в projects.json).")) + '</div></div>';
      return;
    }
    const all = I.items, n = all.length || 1;
    const count = (k) => all.filter((it) => it.kind === k || (k === "wait" && it.kind === "dropped")).length;
    const newest = all.slice().sort((a, b) => (b.date || 0) - (a.date || 0) || b.id.localeCompare(a.id, undefined, { numeric: true }))[0];
    const done = count("done");
    const tiles = [
      tl('<div class="card tile"><div class="text"><div class="tlabel">Всего идей</div><div class="value">') + all.length + tl('</div><div class="note">в реестре</div></div></div>'),
      '<div class="card tile">' + ring(count("road") / n * 100, "var(--k-road)", tl("Доля в дорожной карте")) + tl('<div class="text"><div class="tlabel">В дорожной карте</div><div class="value">') + count("road") + tl('</div><div class="note">утверждено</div></div></div>'),
      ...(done ? ['<div class="card tile">' + ring(done / n * 100, "var(--k-done)", tl("Доля сделанных")) + tl('<div class="text"><div class="tlabel">Сделано</div><div class="value">') + done + tl('</div><div class="note">уже воплощено</div></div></div>')] : []),
      tl('<div class="card tile"><div class="text"><div class="tlabel">Исследовать</div><div class="value">') + count("explore") + tl('</div><div class="note">надо разобраться</div></div></div>'),
      ...(count("decision") ? [tl('<div class="card tile"><div class="text"><div class="tlabel">') + tl("Решения CEO") + tl('</div><div class="value">') + count("decision") + tl('</div><div class="note">ещё не выполнены</div></div></div>')] : []),
      tl('<div class="card tile"><div class="text"><div class="tlabel">Идеи и наброски</div><div class="value">') + count("idea") + '</div><div class="note">' +
        (count("future") ? tl("не проверялись · ещё ") + count("future") + tl(" на будущее") : tl("не проверялись")) + '</div></div></div>',
      tl('<div class="card tile"><div class="text"><div class="tlabel">Ждут и отложены</div><div class="value">') + count("wait") + tl('</div><div class="note">есть условие</div></div></div>'),
      tl('<div class="card tile"><div class="text"><div class="tlabel">Последняя идея</div><div class="value">') + (newest ? esc(newest.id) : "—") + '</div><div class="note">' +
        (newest ? fmt(newest.date) : "") + '</div></div></div>'
    ];
    const kinds = ["all", "road"].concat(done ? ["done"] : [], count("decision") ? ["decision"] : [], ["explore", "idea"], count("future") ? ["future"] : [], ["wait"]);
    const label = { all: tl("Все"), road: IDEA_KIND.road, done: IDEA_KIND.done, decision: IDEA_KIND.decision, explore: IDEA_KIND.explore, idea: IDEA_KIND.idea, future: IDEA_KIND.future, wait: IDEA_KIND.wait };
    if (!kinds.includes(state.ideaFilter)) state.ideaFilter = "all";
    const list = all.filter((it) => state.ideaFilter === "all" || it.kind === state.ideaFilter || (state.ideaFilter === "wait" && it.kind === "dropped"))
      .slice().sort((a, b) => b.id.localeCompare(a.id, undefined, { numeric: true }));
    const filters = kinds.map((k) => '<button type="button" data-filter="' + k + '" class="' + (state.ideaFilter === k ? "active" : "") + '">' + label[k] +
      '<span class="n">' + (k === "all" ? all.length : count(k)) + '</span></button>').join("");
    const rows = list.map((it) => '<tr data-open="idea:' + esc(I.id) + ':' + esc(it.id) + '" tabindex="0" aria-label="' + esc(tl("Открыть идею ") + it.id) + '">' +
      '<td><span class="iid">' + esc(it.id) + '</span></td><td><span class="idate">' + fmt(it.date) + '</span></td>' +
      '<td><div class="pname ititle">' + flagMark(it.id) + esc(it.title) + '</div></td><td>' + ideaChip(it) + '</td></tr>').join("");
    box.innerHTML = '<div class="tiles' + (tiles.length > 6 ? " t" + tiles.length : "") + '">' + tiles.join("") + '</div>' +
      tl('<div class="card"><h2>Все идеи</h2><p class="sub">Новые сверху · нажмите на идею, чтобы прочитать её целиком</p><div class="filters">') + filters + '</div>' +
      (list.length ? tl('<table><colgroup><col class="c-id"><col class="c-date"><col><col class="c-istatus"></colgroup><thead><tr><th>№</th><th>Дата</th><th>Идея</th><th>Статус</th></tr></thead><tbody>') +
        rows + '</tbody></table>' : (all.length ? tl('<div class="empty">Таких идей пока нет</div>') : '<div class="empty">' + esc(tl("Идей пока нет. Добавьте строку в таблицу файла идей (он указан ниже) или попросите ассистента добавить идею")) + '</div>')) + '</div>' +
      sourceLine(I);
  }

  // Откуда идеи: общая база (пишут исполнители скриптом ideas.py) или, если её нет, файлы.
  function sourceLine(I) {
    const S = board.ideaSource || {};
    if (I.fromDb) return tl('<p class="source">Источник: общая база идей ') + esc(I.source) + (I.updated ? tl(' · последняя запись ') + esc(I.updated) : "") +
      tl(' · исполнители пишут в неё командой ideas.py, Пульт только читает</p>');
    return (S.error ? '<p class="source warn">' + esc(S.error) + '</p>' : "") +
      tl('<p class="source">Источник: ') + esc(I.source) + (I.updated ? tl(' · файл изменён ') + esc(I.updated) : "") + tl(' · обновляется, когда файл меняется</p>');
  }

