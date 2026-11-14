"use strict";
  // ---------------------------------------------------------------- Календарь
  // Личный — календари Google владельца (только чтение, calendar.json от программы Пульта);
  // рабочий — события самого Пульта (история проектов). В Google Пульт ничего не пишет.
  const WEEK_START = 0;                      // неделя с воскресенья, как в Израиле
  const WD = [tl("Вс"), tl("Пн"), tl("Вт"), tl("Ср"), tl("Чт"), tl("Пт"), tl("Сб")];
  const WD_FULL = [tl("воскресенье"), tl("понедельник"), tl("вторник"), tl("среда"), tl("четверг"), tl("пятница"), tl("суббота")];
  const MONTHS = [tl("январь"), tl("февраль"), tl("март"), tl("апрель"), tl("май"), tl("июнь"), tl("июль"), tl("август"), tl("сентябрь"), tl("октябрь"), tl("ноябрь"), tl("декабрь")];
  const MONTHS_GEN = [tl("января"), tl("февраля"), tl("марта"), tl("апреля"), tl("мая"), tl("июня"), tl("июля"), tl("августа"), tl("сентября"), tl("октября"), tl("ноября"), tl("декабря")];
  const CAL_COLOR = { main: "var(--series-1)", holidays: "var(--series-4)", other: "var(--series-2)", work: "var(--series-3)" };
  state.cal = { mode: "month", anchor: null, off: {}, waiting: false, waitMark: "", busy: false, msg: "" };

  const dayKey = (d) => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  const addDays = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
  const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const hm = (d) => String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  const weekStartOf = (d) => addDays(startOfDay(d), -((d.getDay() - WEEK_START + 7) % 7));

  function calEvent(e) {
    if (!e || typeof e !== "object") return null;
    if (e.all_day) {
      const s = parseDate(e.start), x = parseDate(e.end);
      if (!s) return null;
      return { cal: "g:" + e.cal, title: String(e.title || ""), location: String(e.location || ""), allDay: true, start: s, end: x && x > s ? x : addDays(s, 1) };
    }
    const s = new Date(e.start), x = new Date(e.end);
    if (isNaN(s)) return null;
    return { cal: "g:" + e.cal, title: String(e.title || ""), location: String(e.location || ""), allDay: false, start: s, end: isNaN(x) || x <= s ? new Date(s.getTime() + 3600000) : x };
  }
  function normCalendar(c) {
    c = c && typeof c === "object" ? c : {};
    return { available: !!c.available, setup: c.setup || {}, synced: c.synced || "", checked: c.checked || "", needLogin: !!c.need_login,
      rev: String(c.rev || ""), error: c.error || "", loginError: c.login_error || "", calendars: Array.isArray(c.calendars) ? c.calendars : [],
      accounts: Array.isArray(c.accounts) ? c.accounts.filter((a) => a && typeof a === "object") : [],
      events: (Array.isArray(c.events) ? c.events : []).map(calEvent).filter(Boolean) };
  }
  function calSources() {
    const C = board.calendar;
    const extra = ["var(--series-2)", "var(--k-decision)"];   // другие календари (второй аккаунт, общие) — по очереди
    let n = 0;
    const list = C.calendars.map((x) => ({ key: "g:" + x.id, role: x.role, label: tl("Личный · ") + (x.name || tl("календарь")),
      color: x.role === "main" || x.role === "holidays" ? CAL_COLOR[x.role] : extra[n++ % extra.length] }));
    list.push({ key: "work", label: tl("Рабочий · Пульт"), color: CAL_COLOR.work });
    return list;
  }
  function calAllEvents() {
    const work = board.history.map((h) => ({ cal: "work", title: nameOf(h.project) + " — " + h.text, location: "", allDay: true,
      start: h.date, end: addDays(h.date, 1), project: h.project, auto: h.auto }));
    return board.calendar.events.concat(work).filter((e) => !state.cal.off[e.cal]);
  }
  // Все события без учёта выключенных кнопок — для счёта и подсказок.
  function calEveryEvent() {
    const off = state.cal.off; state.cal.off = {};
    try { return calAllEvents(); } finally { state.cal.off = off; }
  }
  function calOverlaps(e, from, to) { return e.start < to && e.end > from; }
  // Сколько событий каждого календаря видно на экране (событие считается один раз).
  function calCounts(from, to) {
    const n = {};
    calEveryEvent().forEach((e) => { if (calOverlaps(e, from, to)) n[e.cal] = (n[e.cal] || 0) + 1; });
    return n;
  }
  // Для личного календаря без событий на экране: ближайшее событие раньше и позже.
  function calNearest(key, from, to) {
    let before = null, after = null;
    calEveryEvent().forEach((e) => {
      if (e.cal !== key || calOverlaps(e, from, to)) return;
      if (e.end <= from) { if (!before || e.start > before.start) before = e; }
      else if (e.start >= to) { if (!after || e.start < after.start) after = e; }
    });
    return { before, after };
  }
  function monthTitle(d) { return MONTHS[d.getMonth()] + " " + d.getFullYear(); }
  // День → события. Событие на несколько дней показывается в каждом своём дне (не больше 62 дней).
  function calByDay(from, to) {
    const map = new Map();
    calAllEvents().forEach((e) => {
      let d = startOfDay(e.start);
      const last = e.allDay ? addDays(startOfDay(e.end), -1) : startOfDay(new Date(e.end.getTime() - 1));
      if (d < from) d = from;
      for (let i = 0; d <= last && d < to && i < 62; i++, d = addDays(d, 1)) {
        const k = dayKey(d);
        if (!map.has(k)) map.set(k, []);
        map.get(k).push(e);
      }
    });
    const order = (e) => (e.cal === "work" ? 2 : e.allDay ? 0 : 1);
    map.forEach((list) => list.sort((a, b) => order(a) - order(b) || a.start - b.start || a.title.localeCompare(b.title)));
    return map;
  }
  function calColor(key) { const s = calSources().find((x) => x.key === key); return s ? s.color : CAL_COLOR.other; }
  function calName(key) { const s = calSources().find((x) => x.key === key); return s ? s.label : ""; }
  // Событие со временем, которое переходит через полночь: «смена с четверга на пятницу».
  // Конец ровно в 00:00 следующего дня — не переход (смена 15:45–00:00 остаётся в своём дне).
  const WD_FROM = [tl("воскресенья"), tl("понедельника"), tl("вторника"), tl("среды"), tl("четверга"), tl("пятницы"), tl("субботы")];
  const WD_TO = [tl("воскресенье"), tl("понедельник"), tl("вторник"), tl("среду"), tl("четверг"), tl("пятницу"), tl("субботу")];
  function overnightLabel(e) {
    if (e.allDay) return "";
    let a = startOfDay(e.start);
    const b = startOfDay(new Date(e.end.getTime() - 1));
    // ночная смена с 00:00 (в таблице — «ночь со среды на четверг») относится к ночи с прошлого дня
    if (b <= a && e.start.getTime() === a.getTime() && /ночн|night|לילה/i.test(e.title)) a = addDays(a, -1);
    if (b <= a) return "";
    const nights = Math.round((b - a) / 86400000);
    const shift = /смен|shift|משמרת/i.test(e.title);
    if (LANG === "en") return (shift ? "shift " : "") + (nights === 1 ? "from " + WD_FULL[a.getDay()] + " to " + WD_FULL[b.getDay()]
      : "from " + a.getDate() + " " + MONTHS_GEN[a.getMonth()] + " to " + b.getDate() + " " + MONTHS_GEN[b.getMonth()]);
    if (LANG === "he") return (shift ? "משמרת " : "") + (nights === 1 ? "מ" + WD_FULL[a.getDay()] + " ל" + WD_FULL[b.getDay()]
      : "מ־" + a.getDate() + " " + MONTHS_GEN[a.getMonth()] + " עד " + b.getDate() + " " + MONTHS_GEN[b.getMonth()]);
    const what = shift ? tl("смена ") : "";
    const prep = a.getDay() === 2 || a.getDay() === 3 ? tl("со ") : tl("с ");   // со вторника, со среды
    return nights === 1 ? what + prep + WD_FROM[a.getDay()] + tl(" на ") + WD_TO[b.getDay()]
      : what + tl("с ") + a.getDate() + " " + MONTHS_GEN[a.getMonth()] + tl(" по ") + b.getDate() + " " + MONTHS_GEN[b.getMonth()];
  }
  function evTip(e) {
    const when = e.allDay ? tl("весь день") : hm(e.start) + "–" + hm(e.end);
    const night = overnightLabel(e);
    return esc(e.title) + "<br>" + esc(calName(e.cal)) + " · " + esc(when) + (night ? "<br>" + esc(night) : "") + (e.location ? "<br>" + esc(e.location) : "");
  }
  // Время на плашке дня. Ночная смена 23:45–08:00 во второй день показывается как «до 08:00», а не «23:45».
  function evTime(e, day) {
    if (e.allDay) return "";
    if (!day || startOfDay(e.start) >= day) return hm(e.start);
    return startOfDay(new Date(e.end.getTime() - 1)) > day ? tl("весь день") : tl("до ") + hm(e.end);
  }
  function evChip(e, day) {
    const t = evTime(e, day);
    return '<div class="cal-ev" style="border-inline-start-color:' + calColor(e.cal) + '" data-tip="' + esc(evTip(e)) + '">' +
      (t ? '<span class="t">' + t + '</span>' : "") + esc(e.title) + '</div>';
  }
  function calTodayCount() {
    if (!board || !board.calendar) return 0;
    const t = today(), list = calByDay(t, addDays(t, 1)).get(dayKey(t));
    return list ? list.length : 0;
  }

  function calState() {
    const C = board.calendar, S = state.cal;
    const box = (cls, title, text, button) => '<div class="cal-state ' + cls + '"><div class="txt"><h2>' + esc(title) + '</h2>' + text + '</div>' + (button || "") + '</div>';
    if (!C.available) return box("warn", tl("Календарь не подключён"), tl("Нет файла calendar_google.py рядом с Пультом — обновите Пульт."));
    if (!C.setup.client) return box("warn", tl("Нужен ключ приложения Google"),
      tl("Положите файл <b>google-client.json</b> в папку «XControlP» (Google Cloud → Google Auth Platform → Clients → Desktop app → Download JSON)."));
    if (S.waiting) return box("", tl("Жду разрешения в окне Google…"),
      tl("В браузере открылось окно Google: выберите ") + (S.waitFor ? tl("аккаунт <b>") + esc(S.waitFor) + "</b>" : tl("нужный аккаунт")) +
      tl(" и нажмите «Разрешить» (доступ только на чтение). Пульт обновит календарь сам.") +
      tl("<br><span class=\"cal-note\">Если Google пишет «Доступ заблокирован» — этот аккаунт не добавлен в тестовые пользователи (Google Cloud → Google Auth Platform → Audience → Test users).</span>") +
      (S.msg ? '<br><span class="cal-note">' + esc(S.msg) + '</span>' : ""));
    const login = tl('<button type="button" class="cal-btn primary" data-cal="login">Войти в Google</button>');
    const okAccounts = C.accounts.filter((a) => a.ok), lost = C.accounts.filter((a) => a.need_login);
    const addBtn = tl('<button type="button" class="cal-btn" data-cal="add" title="Подключить ещё один аккаунт Google (только чтение)">+ Аккаунт</button>');
    const refreshBtn = '<button type="button" class="cal-btn" data-cal="refresh"' + (S.busy ? " disabled" : "") + '>' + (S.busy ? tl("Обновляю…") : tl("Обновить")) + '</button>';
    // Несколько аккаунтов: один истёк, остальные работают — календарь показываем, просим войти снова только в этот.
    if (C.setup.token && C.needLogin && okAccounts.length && lost.length) {
      return box("warn", tl("Нужно войти в Google снова: ") + lost.map((a) => a.account || tl("аккаунт")).join(", "),
        tl("Разрешение истекло (в режиме «Testing» — раз в 7 дней). Записи этого аккаунта показаны на последнее обновление.") +
        (C.loginError ? tl('<br><span class="cal-note">Прошлая попытка: ') + esc(C.loginError) + '</span>' : "") +
        (S.msg ? '<br><span class="cal-note">' + esc(S.msg) + '</span>' : ""),
        lost.map((a) => '<button type="button" class="cal-btn primary" data-cal="relogin:' + esc(a.account || "") + tl('">Войти: ') + esc((a.account || tl("аккаунт")).split("@")[0]) + '</button>').join("") + refreshBtn);
    }
    if (!C.setup.token || C.needLogin) {
      const why = C.needLogin && C.setup.token ? esc(C.error || tl("Разрешение Google истекло — нужно войти снова."))
        : tl("Пульт ещё не подключён к вашему Google Календарю. Разрешение — <b>только на чтение</b>: Пульт ничего не запишет в календарь.");
      return box(C.needLogin && C.setup.token ? "warn" : "", C.needLogin && C.setup.token ? tl("Нужно войти в Google снова") : tl("Подключить Google Календарь"),
        why + (C.loginError ? tl('<br><span class="cal-note">Прошлая попытка: ') + esc(C.loginError) + '</span>' : "") +
        (S.msg ? '<br><span class="cal-note">' + esc(S.msg) + '</span>' : ""), login);
    }
    if (C.error) return box("bad", tl("Календарь не обновился"), esc(C.error) + (C.synced ? tl(" · показаны события на ") + esc(stamp(C.synced)) : ""), refreshBtn);
    const accs = okAccounts.map((a) => a.account).filter(Boolean);
    return box("ok", "", tl('Google Календарь · <b>только чтение</b> · обновлено ') + esc(stamp(C.synced) || "—") +
      (accs.length ? ' · ' + (accs.length > 1 ? tl("аккаунты") : tl("аккаунт")) + ': ' + esc(accs.join(", ")) : "") +
      tl(' · календари: ') + esc(C.calendars.map((x) => x.name).join(", ") || "—") +
      (C.loginError ? tl(' · <span class="cal-note">прошлая попытка входа: ') + esc(C.loginError) + '</span>' : "") +
      (S.msg ? ' · <span class="cal-note">' + esc(S.msg) + '</span>' : ""), addBtn + refreshBtn);
  }

  function renderCalendar() {
    const S = state.cal;
    if (!S.anchor) S.anchor = today();
    const week = S.mode === "week";
    const start = week ? weekStartOf(S.anchor) : weekStartOf(new Date(S.anchor.getFullYear(), S.anchor.getMonth(), 1));
    const days = week ? 7 : 42;
    const end = addDays(start, days);
    const map = calByDay(start, end);
    const t = dayKey(today()), month = S.anchor.getMonth();
    let label;
    if (week) {
      const last = addDays(start, 6);
      label = start.getMonth() === last.getMonth() ? start.getDate() + "–" + last.getDate() + " " + MONTHS_GEN[last.getMonth()] + " " + last.getFullYear()
        : start.getDate() + " " + MONTHS_GEN[start.getMonth()] + " – " + last.getDate() + " " + MONTHS_GEN[last.getMonth()] + " " + last.getFullYear();
    } else {
      label = MONTHS[month][0].toUpperCase() + MONTHS[month].slice(1) + " " + S.anchor.getFullYear();
    }
    // Счёт и подсказки — за сам месяц (или неделю), без соседних дней сетки.
    const cFrom = week ? start : new Date(S.anchor.getFullYear(), month, 1), cTo = week ? end : new Date(S.anchor.getFullYear(), month + 1, 1);
    const counts = calCounts(cFrom, cTo), period = week ? tl("на этой неделе") : tl("в этом месяце");
    const legend = calSources().map((s) => {
      const off = !!S.off[s.key], n = counts[s.key] || 0;
      return '<button type="button" class="cal-chip' + (off ? " off" : "") + '" data-cal="toggle:' + esc(s.key) + '" aria-pressed="' + !off + '" title="' +
        esc((off ? tl("Скрыт. Нажмите, чтобы показать") : tl("Нажмите, чтобы скрыть")) + tl(" · событий ") + period + ": " + n) + '">' +
        '<i style="background:' + s.color + '"></i>' + esc(s.label) + ' <b>' + (off ? tl("скрыт") : n) + '</b></button>';
    }).join("");
    // Подсказки: скрытые календари и личные календари без событий на экране.
    const hints = [];
    const hidden = calSources().filter((s) => S.off[s.key]);
    if (hidden.length) hints.push(tl('<div class="cal-hint">Скрыто: ') + hidden.map((s) => "«" + esc(s.label) + "»").join(", ") +
      tl('<button type="button" class="cal-btn" data-cal="showall">Показать все</button></div>'));
    calSources().forEach((s) => {
      if (s.key === "work" || s.role === "holidays" || S.off[s.key] || counts[s.key]) return;
      const near = calNearest(s.key, cFrom, cTo);
      if (!near.before && !near.after) return;
      hints.push('<div class="cal-hint"><i style="background:' + s.color + '"></i>«' + esc(s.label) + '»: ' + period + tl(' записей нет.') +
        (near.before ? '<button type="button" class="cal-btn" data-cal="goto:' + dayKey(near.before.start) + tl('">‹ раньше: ') + esc(monthTitle(near.before.start)) + '</button>' : "") +
        (near.after ? '<button type="button" class="cal-btn" data-cal="goto:' + dayKey(near.after.start) + tl('">позже: ') + esc(monthTitle(near.after.start)) + ' ›</button>' : "") + '</div>');
    });
    const monthValue = S.anchor.getFullYear() + "-" + String(S.anchor.getMonth() + 1).padStart(2, "0");
    const bar = '<div class="cal-bar">' +
      tl('<button type="button" class="cal-btn" data-cal="prev" aria-label="Назад">‹</button>') +
      tl('<button type="button" class="cal-btn" data-cal="today">Сегодня</button>') +
      tl('<button type="button" class="cal-btn" data-cal="next" aria-label="Вперёд">›</button>') +
      '<span class="cal-label">' + esc(label) + '</span>' +
      '<input type="month" class="cal-month" value="' + monthValue + tl('" aria-label="Перейти к месяцу" title="Перейти к месяцу">') +
      '<span class="cal-seg"><button type="button" data-cal="mode:month" class="' + (week ? "" : "active") + tl('">Месяц</button>') +
      '<button type="button" data-cal="mode:week" class="' + (week ? "active" : "") + tl('">Неделя</button></span>') +
      '<span class="cal-legend">' + legend + '</span></div>';
    let grid = '<div class="cal-grid' + (week ? " week" : "") + '">';
    for (let i = 0; i < 7; i++) grid += '<div class="cal-head">' + WD[(WEEK_START + i) % 7] + '</div>';
    const limit = week ? 99 : 3;
    for (let i = 0; i < days; i++) {
      const d = addDays(start, i), k = dayKey(d), list = map.get(k) || [];
      const cls = "cal-day" + (k === t ? " today" : "") + (!week && d.getMonth() !== month ? " other" : "");
      grid += '<div class="' + cls + '" data-open="day:' + k + '" tabindex="0" aria-label="' + esc(d.getDate() + " " + MONTHS_GEN[d.getMonth()] + tl(": событий ") + list.length) + '">' +
        '<span class="dn">' + d.getDate() + (week ? '<span class="wdn">' + MONTHS_GEN[d.getMonth()] + '</span>' : "") + '</span>' +
        list.slice(0, limit).map((e) => evChip(e, d)).join("") +
        (list.length > limit ? tl('<span class="cal-more">ещё ') + (list.length - limit) + '</span>' : "") + '</div>';
    }
    grid += '</div>';
    $("calendar").innerHTML = calState() + bar + (hints.length ? '<div class="cal-hints">' + hints.join("") + '</div>' : "") + grid +
      tl('<div class="cal-note">Нажмите на день, чтобы увидеть все его события. Рабочий календарь — события проектов из Пульта; в Google они не записываются.</div>');
  }

  function renderDayDrawer(key) {
    const d = parseDate(key);
    if (!d) { if (drawer.open) drawer.close(); return; }
    const list = calByDay(d, addDays(d, 1)).get(key) || [];
    const items = list.map((e) => '<div class="cal-item"><i style="background:' + calColor(e.cal) + '"></i>' +
      '<span class="when">' + (e.allDay ? tl("весь день") : hm(e.start) + "–" + hm(e.end)) + '</span>' +
      '<span class="what">' + (e.project ? '<span class="ilink" data-open="' + esc(e.project) + '">' + esc(nameOf(e.project)) + '</span> — ' + esc(e.title.slice(nameOf(e.project).length + 3)) : esc(e.title)) + '</span>' +
      (overnightLabel(e) ? '<span class="night">' + esc(overnightLabel(e)[0].toUpperCase() + overnightLabel(e).slice(1)) + '</span>' : "") +
      '<span class="src">' + esc(calName(e.cal)) + (e.location ? " · " + esc(e.location) : "") + (e.auto ? tl(" · авто") : "") + '</span></div>').join("");
    drawer.innerHTML = '<div class="dw"><div class="dw-head">' +
      tl('<button type="button" class="dw-close" data-close aria-label="Закрыть">✕</button>') +
      tl('<div class="dw-meta"><span>Календарь</span></div>') +
      '<h2 id="dw-title">' + esc(WD_FULL[d.getDay()][0].toUpperCase() + WD_FULL[d.getDay()].slice(1) + ", " + d.getDate() + " " + MONTHS_GEN[d.getMonth()] + " " + d.getFullYear()) + '</h2>' +
      '<p class="dw-about">' + (list.length ? tl("Событий: ") + list.length : tl("В этот день событий нет")) + '</p></div>' +
      '<div class="dw-body">' + (list.length ? '<div class="cal-list">' + items + '</div>' : tl('<div class="empty">Пусто</div>')) + '</div></div>';
  }

  async function calPost(path, lenient) {
    const r = await fetch(path, { method: "POST", headers: { "X-Pult-Token": token } });
    let res = {};
    try { res = await r.json(); } catch (err) { res = {}; }
    // lenient: обновление, где один аккаунт не прошёл, — не сбой; что именно не так, показывает рамка сверху
    if (!r.ok || (!res.ok && !(lenient && res.accounts))) throw new Error(res.error || (tl("ответ ") + r.status));
    return res;
  }
  let calPoll = 0;
  async function calAction(a) {
    const S = state.cal;
    if (!S.anchor) S.anchor = today();
    if (a === "prev" || a === "next") {
      const k = a === "prev" ? -1 : 1;
      S.anchor = S.mode === "week" ? addDays(S.anchor, 7 * k) : new Date(S.anchor.getFullYear(), S.anchor.getMonth() + k, 1);
    } else if (a === "today") S.anchor = today();
    else if (a.startsWith("mode:")) S.mode = a.slice(5);
    else if (a.startsWith("toggle:")) { const key = a.slice(7); S.off[key] = !S.off[key]; }
    else if (a === "showall") S.off = {};
    else if (a.startsWith("goto:")) { const d = parseDate(a.slice(5)); if (d) S.anchor = d; }
    else if (a === "login" || a === "refresh" || a === "add" || a.startsWith("relogin:")) {
      if (!token) { S.msg = tl("Кнопка работает, когда Пульт открыт ярлыком «XControlP» на рабочем столе."); renderCalendar(); return; }
      S.msg = "";
      if (a !== "refresh") {
        const who = a.startsWith("relogin:") ? a.slice(8) : "";
        const path = a === "add" ? "/calendar/add" : "/calendar/login" + (who ? "?account=" + encodeURIComponent(who) : "");
        try {
          await calPost(path);
          S.waitFor = who;
          S.waiting = true; S.waitMark = board.calendar.rev + "|" + board.calendar.checked + "|" + board.calendar.synced;
          clearInterval(calPoll);
          calPoll = setInterval(() => { refresh(); }, 3000);
          setTimeout(() => { if (S.waiting) { S.waiting = false; S.msg = tl("Разрешение не пришло за 5 минут — попробуйте войти ещё раз."); clearInterval(calPoll); renderCalendar(); } }, 310000);
        } catch (err) { S.msg = tl("Не удалось начать вход: ") + (err && err.message || err); }
      } else {
        S.busy = true; renderCalendar();
        try { const res = await calPost("/calendar/sync", true); S.msg = res.ok ? tl("событий: ") + res.events : ""; }
        catch (err) { S.msg = tl("Не обновилось: ") + (err && err.message || err); }
        S.busy = false; refresh();
      }
    }
    renderCalendar();
  }
  // Данные перечитаны: если ждали входа и в calendar.json что-то изменилось — вход закончился.
  function calAfterLoad() {
    const S = state.cal;
    if (S.waiting && board && board.calendar && board.calendar.rev + "|" + board.calendar.checked + "|" + board.calendar.synced !== S.waitMark) {
      S.waiting = false; clearInterval(calPoll);
      S.msg = board.calendar.loginError || (board.calendar.synced ? "" : "");
    }
  }


