"use strict";
  // ---------------------------------------------------------------- Настройки
  // Кнопка ☰ перед языками → панель со стороны меню. Выбор хранит программа в settings.json (POST /settings?icons=…&theme=…).
  // Этап 2: стили значков — найденные программой в icons (style.json) и «Базовый» (символы); «Вернуть базовые настройки».
  const setPanel = $("settings-panel");
  const SET_DEFAULT = { icons: "comic", theme: "dark", scale: "100", accent: "orange" };
  const SET_SCALES = ["90", "100", "110", "125"];
  const SET_ACCENTS = [["orange", "Оранжевый", "#f28a1e"], ["blue", "Синий", "#4c8df6"], ["violet", "Фиолетовый", "#9d80f2"], ["teal", "Бирюзовый", "#19b5a3"]];
  const uiZoom = () => parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
  const SET_PREVIEW = [["obzor", "▦"], ["calendar", "▤"], ["review", "▥"], ["ideas", "✦"]];
  let setMsg = "", setOk = "", setBusy = false, setTab = "interface";
  const setPick = (o) => o && typeof o === "object" ? String(o[LANG] || o.ru || o.en || "") : String(o || "");
  const iconStyles = () => (window.BOARD && Array.isArray(window.BOARD.icon_styles) ? window.BOARD.icon_styles : [])
    .filter((st) => st && typeof st.id === "string" && /^[a-z0-9][a-z0-9-]{0,29}$/.test(st.id) && st.id !== "base");
  function uiSettings() {
    const fromData = window.BOARD && window.BOARD.settings && typeof window.BOARD.settings === "object" ? window.BOARD.settings : {};
    return Object.assign({}, SET_DEFAULT, fromData, setLocal);
  }
  function applySettings() {
    const u = uiSettings();
    document.documentElement.dataset.icons = iconStyle();
    document.documentElement.dataset.theme = u.theme;
    document.documentElement.dataset.scale = SET_SCALES.includes(u.scale) ? u.scale : "100";
    document.documentElement.dataset.accent = SET_ACCENTS.some(([id]) => id === u.accent) ? u.accent : "orange";
  }
  function renderSettings() {
    if (!setPanel) return;
    const u = uiSettings(), cur = iconStyle();
    const opt = (key, value, body, disabled, on) => '<button type="button" class="set-opt' + (on ? " on" : "") + '" data-set="' + key + ':' + esc(value) + '" aria-pressed="' +
      !!on + '"' + (disabled || setBusy ? " disabled" : "") + '>' + body + '</button>';
    const styles = iconStyles().map((st) => opt("icons", st.id, '<span class="set-ics">' + SET_PREVIEW.map(([n]) => iconImg(st.id, n, "")).join("") + '</span><b>' +
      esc(setPick(st.name) || st.id) + '</b>' + (setPick(st.about) ? '<small>' + esc(setPick(st.about)) + '</small>' : ""), false, cur === st.id)).join("") +
      opt("icons", "base", '<span class="set-ics set-sym">' + SET_PREVIEW.map(([, sym]) => sym).join(" ") + '</span><b>' + esc(tl("Базовый")) + '</b><small>' +
        esc(tl("Прежние значки-символы")) + '</small>', false, cur === "base");
    const isBase = cur === "base" && u.theme === "dark" && u.scale === "100" && u.accent === "orange";
    const tabBtn = (id, label) => '<button type="button" role="tab" class="' + (setTab === id ? "on" : "") + '" aria-selected="' + (setTab === id) + '" data-set="tab:' + id + '">' +
      esc(tl(label)) + '</button>';
    const langsBody = '<section class="set-sec"><h3>' + navIcon("lang", "") + esc(tl("Язык окна")) + '</h3><div class="set-opts">' +
      Object.keys(LANGS).map((k) => '<button type="button" class="set-opt' + (k === LANG ? " on" : "") + '" data-lang="' + k + '" lang="' + k + '" dir="' + (k === "he" ? "rtl" : "ltr") +
        '" aria-pressed="' + (k === LANG) + '"><b>' + esc(LANGS[k]) + '</b></button>').join("") + '</div>' +
      '<p class="set-note">' + esc(tl("Сейчас переводится всё окно вместе с содержимым: проекты, идеи и отчёты переводит штаб.")) + '</p>' +
      '<p class="set-note">' + esc(tl("Позже язык будет переводить только систему и настройки, а перевод содержимого вашей моделью станет отдельной настройкой.")) + '</p></section>';
    const chip = (key, value, body, on) => '<button type="button" class="set-chip' + (on ? " on" : "") + '" data-set="' + key + ':' + value + '" aria-pressed="' + !!on + '"' +
      (setBusy ? " disabled" : "") + '>' + body + '</button>';
    const tune = '<h4>' + esc(tl("Размер текста")) + '</h4><div class="set-row">' + SET_SCALES.map((v) => chip("scale", v, v + "%", u.scale === v)).join("") + '</div>' +
      '<h4>' + esc(tl("Цвет акцента")) + '</h4><div class="set-row">' + SET_ACCENTS.map(([id, name, color]) => chip("accent", id, '<i style="background:' + color + '"></i>' + esc(tl(name)), u.accent === id)).join("") + '</div>' +
      '<p class="set-note">' + esc(tl("Другие настройки появятся позже")) + '</p>';
    setPanel.innerHTML = '<div class="dw"><div class="dw-head"><h2 id="set-title">☰ ' + esc(tl("Настройки")) + '</h2>' +
      '<button type="button" class="dw-close" data-set="close" aria-label="' + esc(tl("Закрыть")) + '">✕</button>' +
      '<div class="set-tabs" role="tablist">' + tabBtn("interface", "Интерфейс") + tabBtn("langs", "Языки") + '</div></div>' +
      '<div class="dw-body">' + (setMsg ? '<p class="set-msg" role="alert">' + esc(setMsg) + '</p>' : "") + (setOk ? '<p class="set-ok" role="status">' + esc(setOk) + '</p>' : "") +
      (setTab === "langs" ? langsBody : "") + (setTab === "langs" ? "" : '' +
      '<section class="set-sec"><h3>' + esc(tl("Стили интерфейса")) + '</h3><div class="set-opts">' + styles + '</div>' +
        '<p class="set-note">' + esc(tl("Другие стили появятся позже")) + '</p></section>' +
      '<section class="set-sec"><h3>' + esc(tl("Общий стиль")) + '</h3><div class="set-opts">' +
        opt("theme", "dark", '<b>' + esc(tl("Тёмный")) + '</b>', false, u.theme === "dark") + opt("theme", "light", '<b>' + esc(tl("Светлый")) + '</b>', false, u.theme === "light") + '</div></section>' +
      '<section class="set-sec"><h3>' + esc(tl("Настройка стиля")) + '</h3>' + tune + '</section>' +
      '<section class="set-sec"><button type="button" class="svc-btn" data-set="reset"' + (isBase || setBusy ? " disabled" : "") + '>' + esc(tl("Вернуть базовые настройки")) + '</button>' +
        '<p class="set-note">' + esc(tl("Прежние значки-символы, тёмный стиль, размер 100 % и оранжевый акцент")) + '</p></section>') +
      '</div></div>';
  }
  function openSettings() {
    if (!setPanel) return;
    setMsg = ""; setOk = "";
    renderSettings();
    if (!setPanel.open) setPanel.showModal();
    const close = setPanel.querySelector(".dw-close");
    if (close) close.focus();
  }
  async function saveSettings(changes) {
    const cur = Object.assign(uiSettings(), { icons: iconStyle() }), diff = {};
    Object.keys(changes).forEach((k) => { if (SET_DEFAULT.hasOwnProperty(k) && cur[k] !== changes[k]) diff[k] = changes[k]; });
    setMsg = ""; setOk = "";
    if (!Object.keys(diff).length) { renderSettings(); return true; }
    if (!token) { setMsg = tl("Настройка не сохранилась"); renderSettings(); return false; }
    setBusy = true; renderSettings();
    let ok = false;
    try {
      const q = Object.keys(diff).map((k) => k + "=" + encodeURIComponent(diff[k])).join("&");
      const r = await fetch("/settings?" + q, { method: "POST", headers: { "X-Pult-Token": token } });
      const res = await r.json().catch(() => ({}));
      ok = r.ok && !!res.ok;
    } catch (err) { ok = false; }
    setBusy = false;
    if (ok) { setLocal = Object.assign({}, setLocal, diff); applySettings(); render(); }
    else setMsg = tl("Настройка не сохранилась");
    renderSettings();
    return ok;
  }
  async function settingsAction(v) {
    const [cmd, arg] = String(v || "").split(":");
    if (cmd === "open") { setTab = arg === "langs" ? "langs" : "interface"; openSettings(); }
    else if (cmd === "tab") { setTab = arg === "langs" ? "langs" : "interface"; setMsg = ""; setOk = ""; renderSettings(); }
    else if (cmd === "close") { if (setPanel && setPanel.open) setPanel.close(); }
    else if (cmd === "reset") { if (await saveSettings({ icons: "base", theme: "dark", scale: "100", accent: "orange" })) { setOk = tl("Базовые настройки возвращены"); renderSettings(); } }
    else if (cmd === "icons" || cmd === "theme" || cmd === "scale" || cmd === "accent") saveSettings({ [cmd]: arg });
  }
  if (setPanel) {
    setPanel.addEventListener("click", (e) => { if (e.target === setPanel) setPanel.close(); });
    setPanel.addEventListener("close", () => { const b = document.querySelector(".set-open"); if (b) b.focus(); });
  }
  applySettings();

  function applyStatic() {
    document.documentElement.lang = LANG;
    document.documentElement.dir = LANG === "he" ? "rtl" : "ltr";
    if (LANG === "ru") return;
    document.title = tl(document.title);
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: (n) =>
      /^(SCRIPT|STYLE)$/.test(n.parentNode.nodeName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((n) => { if (CYR_RE.test(n.nodeValue)) n.nodeValue = tx(n.nodeValue); });
    document.querySelectorAll("[title],[aria-label],[placeholder]").forEach((el) => ["title", "aria-label", "placeholder"].forEach((a) => {
      const v = el.getAttribute(a);
      if (v && CYR_RE.test(v)) el.setAttribute(a, tx(v));
    }));
  }

  function render() {
    if (!board) return;
    if (state.view === "idea-stats" && !board.ideaSets.length) state.view = "all";
    if (String(state.view).startsWith("ideas") && !ideaSetOf(state.view)) state.view = "all";
    const insightView = state.view === "perf" || state.view === "idea-stats";
    const calView = state.view === "calendar";
    const dayView = state.view === "day";
    const reviewView = state.view === "review";
    const statsView = state.view === "stats";
    const digestView = state.view === "digest";
    const servicesView = state.view === "services" && board.ideaSets.length > 0;
    const researchView = state.view === "research";
    const reportsView = state.view === "reports";
    const proposalsView = state.view === "proposals";
    if (state.view !== "all" && state.view !== "alerts" && !insightView && !calView && !dayView && !reviewView && !statsView && !digestView && !servicesView && !researchView && !reportsView && !proposalsView && !ideaSetOf(state.view) && !board.groups.includes(state.view)) state.view = "all";
    const ideaSet = ideaSetOf(state.view), ideasView = !!ideaSet;
    document.querySelectorAll(".dash").forEach((el) => { el.hidden = ideasView || insightView || calView || dayView || reviewView || statsView || digestView || servicesView || researchView || reportsView || proposalsView; });
    $("ideas").hidden = !(ideasView || servicesView || researchView || reportsView || proposalsView);
    $("insight").hidden = !insightView;
    $("calendar").hidden = !calView;
    $("dayplan").hidden = !dayView;
    $("review").hidden = !reviewView;
    $("stats").hidden = !statsView;
    $("digest").hidden = !digestView;
    $("period").hidden = ideasView || insightView || calView || dayView || reviewView || statsView || digestView || servicesView || researchView || reportsView || proposalsView;
    const list = ideasView || insightView || calView || dayView || reviewView || statsView || digestView || servicesView || researchView || reportsView || proposalsView ? board.projects : visibleProjects();
    renderNav(); renderFocus(); renderBottom(list);
    if (digestView) {
      $("title").textContent = tl("Сводки");
      $("subtitle").textContent = tl("Ежедневные сводки новостей · отметки «интересно» и «полезно» · сегодня ") + fmt(today());
      renderDigest();
    } else if (statsView) {
      $("title").textContent = tl("Статистика");
      $("subtitle").textContent = tl("План дня, движение проектов, учёба, идеи и коммиты за неделю, месяц, квартал и год · сравнение с прошлым периодом · сегодня ") + fmt(today());
      renderStats();
    } else if (reviewView) {
      $("title").textContent = tl("Итоги дней");
      $("subtitle").textContent = tl("Оценка и итог каждого дня · недели и месяцы · сегодня") + " " + fmt(today());
      renderReview();
    } else if (dayView) {
      $("title").textContent = tl("План дня");
      $("subtitle").textContent = tl("Задачи на день из проектов и этапов · отметки выполнения · сегодня ") + fmt(today());
      renderDay();
    } else if (calView) {
      $("title").textContent = tl("Календарь");
      $("subtitle").textContent = tl("Личный — ваш Google Календарь (только чтение) · рабочий — события проектов из Пульта · сегодня ") + fmt(today());
      renderCalendar();
    } else if (proposalsView) {
      $("title").textContent = tl("Предложения");
      $("subtitle").textContent = tl("Ответы штаба на запросы Пульта · открытых предложений") + ": " + prOpen() + tl(" · сегодня ") + fmt(today());
      renderProposals();
    } else if (reportsView) {
      $("title").textContent = tl("Отчёты");
      $("subtitle").textContent = tl("Отчётов") + ": " + rpAll().length + tl(" · сегодня ") + fmt(today());
      renderReports();
    } else if (researchView) {
      $("title").textContent = tl("Исследования");
      $("subtitle").textContent = tl("Записей") + ": " + rsList().length + tl(" · сегодня ") + fmt(today());
      renderResearch();
    } else if (servicesView) {
      $("title").textContent = tl("Наши услуги");
      $("subtitle").textContent = tl("Услуг") + ": " + servicesList().length + " · " + tl("с флажком") + ": " +
        servicesList().filter((x) => (serviceOf(x.it.id) || {}).flag).length + tl(" · сегодня ") + fmt(today());
      renderServices();
    } else if (ideasView) {
      $("title").textContent = ideaSet.title;
      $("subtitle").textContent = (ideaSet.about || ideaSet.title) + tl(" · идей: ") + ideaSet.items.length + (ideaSet.updated ? (ideaSet.fromDb ? tl(" · последняя запись ") : tl(" · файл изменён ")) + ideaSet.updated : "");
      renderIdeas();
    } else if (state.view === "idea-stats") {
      const n = board.ideaSets.reduce((a, s) => a + s.items.length, 0);
      $("title").textContent = tl("Аналитика идей");
      $("subtitle").textContent = board.ideaSets.map((s) => s.title).join(tl(" и ")) + tl(" · идей: ") + n +
        (board.ideaHistory.started ? tl(" · история статусов с ") + fmt(board.ideaHistory.started) : "");
      renderIdeaStats();
    } else if (state.view === "perf") {
      $("title").textContent = tl("Общий уровень производительности");
      $("subtitle").textContent = tl("Проекты, темп и идеи вместе · без отдела «Развитие» · сегодня ") + fmt(today());
      renderPerf();
    } else {
      const viewName = state.view === "all" ? tl("Все проекты") : state.view === "alerts" ? tl("Тревоги") : td(state.view);
      $("title").textContent = viewName;
      $("subtitle").textContent = tl("Обновлено: ") + fmt(board.updated) + (board.sync && board.sync.synced ? tl(" · синхронизировано ") + stamp(board.sync.synced) : "") +
        tl(" · сегодня ") + fmt(today()) + tl(" · проектов на экране: ") + list.length;
      renderHqDay(); renderTiles(list); renderActivity(list); renderProgress(list); renderShare(list); renderTable(list); renderFeed(list);
    }
    if (drawer.open) renderDrawer();
  }

  function load() {
    if (!window.BOARD) {
      document.body.innerHTML = '<div class="error">' + esc(window.BOARD_ERROR ||
        tl("Нет данных (файл data.js). Откройте программу через «XControlP.pyw» — она соберёт данные из projects.json.")) + '</div>';
      return false;
    }
    const text = JSON.stringify(window.BOARD);
    if (text !== lastText) { lastText = text; board = normalize(window.BOARD); calAfterLoad(); applySettings(); render(); }
    return true;
  }

  // Data changes: data.js is read again every 20 seconds; the screen redraws only if something changed.
  function refresh() {
    const s = document.createElement("script");
    s.src = "data.js?v=" + Date.now();
    s.onload = () => { s.remove(); load(); dayLoad(true); revLoad(true); };
    s.onerror = () => s.remove();
    document.body.appendChild(s);
  }

  // Синхронизация: кнопка просит программу Пульта (локальный сервер на 127.0.0.1) запустить сборщик.
  const stamp = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(s || ""); return m ? m[3] + "." + m[2] + " " + m[4] + ":" + m[5] : String(s || ""); };
  const KIND = { stages: tl("этапы и слияния в репозитории"), lessons: tl("коды уроков в коммитах курса"), progress: tl("файл продвижения в папке проекта") };
  function autoLine(p) {
    const a = p.auto;
    if (!a) return "";
    const act = a.activity;
    return tl('<div class="dw-auto">Источник: <b>') + esc(KIND[a.kind] || a.kind || "—") + '</b>' +
      (act ? tl(' · последняя активность: <b>') + esc(fmt(parseDate(act.date))) + '</b> — ' + esc(td(act.text)) + (act.branch ? ' (' + esc(act.branch) + ')' : "") : "") +
      (a.synced ? tl(' · синхронизировано ') + esc(stamp(a.synced)) : "") + '</div>';
  }
  const token = (document.querySelector('meta[name="pult-token"]') || {}).content || "";
  const syncBtn = $("sync"), syncBox = $("syncbox");
  function showSync(kind, title, items) {
    syncBox.className = "syncbox" + (kind ? " " + kind : "");
    syncBox.innerHTML = tl('<button type="button" class="sclose" aria-label="Закрыть">✕</button><h2>') + esc(title) + '</h2>' +
      (items.length ? '<ul>' + items.map(([cls, html]) => '<li class="' + cls + '">' + html + '</li>').join("") + '</ul>' : "");
    syncBox.hidden = false;
  }
  syncBox.addEventListener("click", (e) => { if (e.target.closest(".sclose")) syncBox.hidden = true; });
  // auto = true: синхронизация при включении Пульта, один раз за запуск программы.
  async function doSync(auto) {
    if (!token) {
      if (!auto) showSync("warn", tl("Синхронизация недоступна"), [["note", tl("Кнопка работает, когда Пульт открыт ярлыком «XControlP» на рабочем столе, а не как файл.")]]);
      return;
    }
    if (syncBtn.classList.contains("busy")) return;
    syncBtn.classList.add("busy"); syncBtn.disabled = true;
    syncBtn.querySelector(".lbl").textContent = tl("Синхронизация…");
    showSync("", auto ? tl("Синхронизация при запуске: беру свежие данные с GitHub и читаю проекты…")
      : tl("Синхронизация: беру свежие данные с GitHub и читаю проекты…"), []);
    try {
      const r = await fetch(auto ? "/sync/startup" : "/sync", { method: "POST", headers: { "X-Pult-Token": token } });
      const res = await r.json();
      if (res.skipped) { syncBox.hidden = true; return; }
      if (res.busy) { showSync("warn", tl("Синхронизация уже идёт"), [["note", tl("Данные обновятся сами, когда она закончится.")]]); return; }
      if (!r.ok || !res.ok) throw new Error(res.error || (tl("ответ ") + r.status));
      const items = (res.projects || []).map((p) => p.ok
        ? (p.moved ? ["moved", esc(p.name) + tl(': этап сдвинулся — <b>') + esc(p.stage) + '</b>' + (p.was ? tl(' (был: ') + esc(p.was) + ')' : "")]
                   : ["", esc(p.name) + tl(': без изменений — ') + esc(p.stage)])
        : ["err", esc(p.name) + tl(': не прочитан — ') + esc(p.error || tl("ошибка"))]);
      (res.notes || []).forEach((n) => items.push(["note", esc(n)]));
      if (res.events) items.push(["", tl("Новых событий в истории: ") + res.events]);
      const cal = res.calendar;
      if (cal) items.push(cal.ok ? ["", tl("Google Календарь: обновлён, событий ") + cal.events]
        : [cal.need_login ? "note" : "err", tl("Google Календарь: ") + esc(cal.need_login ? tl("нужно войти снова — раздел «Календарь», кнопка «Войти в Google»") : cal.error || tl("не обновился"))]);
      const dgs = res.digest;
      if (dgs) items.push(dgs.ok ? ["", tl("Сводки: обновлены, новых ") + (dgs.new || 0)] : ["note", tl("Сводки: ") + esc(dgs.error || tl("не обновились"))]);
      const kind = (res.projects || []).some((p) => !p.ok) ? "bad" : (res.notes || []).length ? "warn" : "";
      showSync(kind, (auto ? tl("Синхронизировано при запуске") + " " : tl("Синхронизировано ")) + stamp(res.synced) + " · " + res.seconds + tl(" с"), items);
      refresh();
    } catch (err) {
      showSync("bad", auto ? tl("Синхронизация при запуске не удалась") : tl("Синхронизация не удалась"), [["err", esc(String(err && err.message || err))],
        ["note", auto ? tl("Пульт показывает прежние данные; повторить можно кнопкой синхронизации.")
          : tl("Если окно Пульта было открыто очень долго, программа могла закрыться. Закройте окно и откройте Пульт ярлыком заново.")]]);
    } finally {
      syncBtn.classList.remove("busy"); syncBtn.disabled = false;
      syncBtn.querySelector(".lbl").textContent = tl("Синхронизировать данные");
    }
  }
  syncBtn.addEventListener("click", () => doSync(false));

  // Кнопки тревог: «Починить» — пометка «в починке», «Убрать» — тревога скрыта, «Вернуть» — отметка снята.
  // Отметки хранит программа Пульта в alerts.json (тот же одноразовый ключ, что у синхронизации).
  async function alertAction(act, key, el) {
    if (act === "toggle") { state.alShowGone = !state.alShowGone; render(); return; }
    if (!token) {
      showSync("warn", tl("Кнопки тревог недоступны"), [["note", tl("Кнопка работает, когда Пульт открыт ярлыком «XControlP» на рабочем столе, а не как файл.")]]);
      return;
    }
    if (el) el.disabled = true;
    try {
      const r = await fetch("/alerts?key=" + encodeURIComponent(key) + "&state=" + encodeURIComponent(act), { method: "POST", headers: { "X-Pult-Token": token } });
      const res = await r.json();
      if (!r.ok || !res.ok) throw new Error(res.error || (tl("ответ ") + r.status));
      refresh();
    } catch (err) {
      if (el) el.disabled = false;
      showSync("bad", tl("Отметка тревоги не сохранилась"), [["err", esc(String(err && err.message || err))],
        ["note", tl("Если окно Пульта было открыто очень долго, программа могла закрыться. Закройте окно и откройте Пульт ярлыком заново.")]]);
    }
  }

  // Адрес с #видом (например #ideas:<id>) меняется снаружи — показать этот вид.
  window.addEventListener("hashchange", () => {
    const v = decodeURIComponent(location.hash.slice(1)) || "all";
    if (v !== state.view) { state.view = v; render(); }
  });
  document.addEventListener("click", (e) => {
    const lg = e.target.closest("[data-lang]");
    if (lg) { setLang(lg.dataset.lang); return; }
    const rv = e.target.closest("[data-rv]");
    if (rv && !rv.disabled) { revAction(rv.dataset.rv); return; }
    const st = e.target.closest("[data-st]");
    if (st && !st.disabled) { stAction(st.dataset.st); return; }
    const dp = e.target.closest("[data-dp]");
    if (dp && !dp.disabled) { dayAction(dp.dataset.dp); return; }
    const ca = e.target.closest("[data-cal]");
    if (ca) { calAction(ca.dataset.cal); return; }
    const al = e.target.closest("[data-al]");
    if (al && !al.disabled) { alertAction(al.dataset.al, al.dataset.key || "", al); return; }
    const ao = e.target.closest("[data-alopen]");
    if (ao) { state.ideaFilter = "decision"; state.view = ao.dataset.alopen; history.replaceState(null, "", "#" + encodeURIComponent(state.view)); render(); return; }
    const pq = e.target.closest("[data-prq]");
    if (pq && !pq.disabled) { if (pq.dataset.prq === "load") refresh(); else prRequest(pq.dataset.prq, pq); return; }
    const pr = e.target.closest("[data-pr]");
    if (pr && !pr.disabled) { const i = pr.dataset.pr.indexOf(":"); prMarkSet(pr.dataset.pr.slice(i + 1), pr.dataset.pr.slice(0, i), pr); return; }
    const gt = e.target.closest("[data-goto]");
    if (gt) { state.view = gt.dataset.goto; history.replaceState(null, "", "#" + encodeURIComponent(state.view)); render(); return; }
    const pl = e.target.closest("[data-plan]");
    if (pl && !pl.disabled) { planAdd(pl.dataset.plan, pl); return; }
    const sd = e.target.closest("[data-svcdel]");
    if (sd && !sd.disabled) { svcDelAction(sd.dataset.svcdel, sd); return; }
    const fl = e.target.closest("[data-flag]");
    if (fl && !fl.disabled) { flagAction(fl.dataset.flag, fl); return; }
    const rs = e.target.closest("[data-rs]");
    if (rs && !rs.disabled) { rsAction(rs.dataset.rs); return; }
    const rp = e.target.closest("[data-rp]");
    if (rp && !rp.disabled) { rpAction(rp.dataset.rp); return; }
    const sx = e.target.closest("[data-set]");
    if (sx && !sx.disabled) { settingsAction(sx.dataset.set); return; }
    const dg = e.target.closest("[data-dg]");
    if (dg && !dg.disabled) { digestAction(dg.dataset.dg, dg); return; }
    const b = e.target.closest("nav button");
    if (b) { state.view = b.dataset.view; history.replaceState(null, "", "#" + encodeURIComponent(state.view)); render(); return; }
    const g = e.target.closest("[data-goto]");
    if (g) { state.view = g.dataset.goto; history.replaceState(null, "", "#" + encodeURIComponent(state.view)); render(); return; }
    const f = e.target.closest("[data-filter]");
    if (f) { state.ideaFilter = f.dataset.filter; renderIdeas(); return; }
    const o = !drawer.contains(e.target) && e.target.closest("[data-open]");
    if (o) openStages(o.dataset.open);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const o = e.target.closest && !drawer.contains(e.target) && e.target.closest("[data-open]");
    if (o && o === e.target) { e.preventDefault(); openStages(o.dataset.open); return; }
    const r = e.target.closest && e.target.closest("tr[data-rs]");
    if (r && r === e.target) { e.preventDefault(); rsAction(r.dataset.rs); }
  });
  let resizeTimer = 0;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 150); });
  $("period").addEventListener("change", (e) => { state.period = +e.target.value; render(); });
  document.addEventListener("input", (e) => {
    if (e.target.id === "rv-note") { state.rev.note = e.target.value; return; }
    if (e.target.dataset && e.target.dataset.dpField && e.target.tagName === "INPUT") dayField(e.target);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.dataset && (e.target.dataset.dpField === "amount" || e.target.dataset.dpField === "title")) { e.preventDefault(); dayAction("add"); }
  });
  document.addEventListener("change", (e) => {
    if (e.target.dataset && e.target.dataset.dpField && e.target.tagName === "SELECT") { dayField(e.target); return; }
    if (e.target.classList && e.target.classList.contains("rv-date")) { if (parseDate(e.target.value)) revAction("goto:" + e.target.value); return; }
    if (e.target.classList && e.target.classList.contains("dp-date")) { if (parseDate(e.target.value)) dayAction("goto:" + e.target.value); return; }
    if (!e.target.classList || !e.target.classList.contains("cal-month")) return;
    const m = /^(\d{4})-(\d{2})$/.exec(e.target.value || "");
    if (m) { state.cal.anchor = new Date(+m[1], +m[2] - 1, 1); renderCalendar(); }
  });
  $("print").addEventListener("click", () => window.print());

  // Tooltips: on hover and on keyboard focus.
  const tip = $("tip");
  function showTip(el, x, y) {
    tip.innerHTML = el.getAttribute("data-tip"); tip.hidden = false;
    const z = uiZoom(), w = tip.offsetWidth, h = tip.offsetHeight, vw = innerWidth / z, vh = innerHeight / z;
    tip.style.left = Math.min(x / z + 14, vw - w - 8) + "px";
    tip.style.top = Math.max(8, Math.min(y / z + 14, vh - h - 8)) + "px";
  }
  document.addEventListener("mousemove", (e) => {
    const el = e.target.closest && e.target.closest("[data-tip]");
    if (el) showTip(el, e.clientX, e.clientY); else tip.hidden = true;
  });
  document.addEventListener("focusin", (e) => {
    const el = e.target.closest && e.target.closest("[data-tip]");
    if (el) { const r = el.getBoundingClientRect(); showTip(el, r.left + r.width / 2, r.top + r.height / 2); }
  });
  document.addEventListener("focusout", () => { tip.hidden = true; });

  applyStatic();
  renderLangs();
  if (load()) {
    dayLoad(true);
    revLoad(true);
    setInterval(refresh, 20000);
    setInterval(render, 10 * 60 * 1000);
    doSync(true);
  }
