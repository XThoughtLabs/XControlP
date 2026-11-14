"use strict";
  // ---------------------------------------------------------------- Статистика
  // Неделя (с воскресенья, как в Израиле) и месяц; стрелки — прошлый и следующий период; ▲/▼ — сравнение с прошлым
  // периодом, а пока период идёт — с теми же первыми днями прошлого. Квартал и год считает этот же код: когда
  // накопятся данные, добавить "quarter" и "year" в ST_KINDS — больше ничего менять не нужно.
  // Откуда цифры: план дня — day.db (как во вкладке «Итоги дней»); движение проектов — история Пульта;
  // идеи — общая база идей; уроки и коммиты по дням — сборщик (кнопка «Синхронизировать данные»), только числа.
  const ST_KINDS = ["week", "month", "quarter", "year"];   // квартал и год включены
  const ST_NAME = { week: tl("Неделя"), month: tl("Месяц"), quarter: tl("Квартал"), year: tl("Год") };
  const ST_PREV = { week: tl("к прошлой неделе"), month: tl("к прошлому месяцу"), quarter: tl("к прошлому кварталу"), year: tl("к прошлому году") };
  const ST_PREV_PART = { week: tl("к тем же дням прошлой недели"), month: tl("к тем же дням прошлого месяца"),
    quarter: tl("к тем же дням прошлого квартала"), year: tl("к тем же дням прошлого года") };
  const ST_CHART_NAME = { week: "Коммиты по дням", month: "Коммиты по дням", quarter: "Коммиты по неделям", year: "Коммиты по месяцам" };
  const STUDY = "Учёба";
  state.st = { kind: "week", anchor: null };
  const cap1 = (s) => s ? s[0].toUpperCase() + s.slice(1) : s;
  const num1 = (x) => LANG === "ru" ? x.toFixed(1).replace(".", ",") : x.toFixed(1);
  const ST_PP = LANG === "ru" ? "п.п." : LANG === "he" ? "נק׳ אחוז" : "pp";   // процентные пункты

  function stPeriod(kind, day) {
    const d = startOfDay(day);
    let start, end, label;
    if (kind === "month") {
      start = new Date(d.getFullYear(), d.getMonth(), 1); end = new Date(d.getFullYear(), d.getMonth() + 1, 1);
      label = cap1(MONTHS[start.getMonth()]) + " " + start.getFullYear();
    } else if (kind === "quarter") {
      const q = Math.floor(d.getMonth() / 3);
      start = new Date(d.getFullYear(), q * 3, 1); end = new Date(d.getFullYear(), q * 3 + 3, 1);
      label = tl("Квартал") + " " + (q + 1) + " · " + start.getFullYear();
    } else if (kind === "year") {
      start = new Date(d.getFullYear(), 0, 1); end = new Date(d.getFullYear() + 1, 0, 1); label = String(start.getFullYear());
    } else {
      kind = "week"; start = weekStartOf(d); end = addDays(start, 7); label = fmtShort(start) + " – " + fmt(addDays(end, -1));
    }
    return { kind, start, end, label };
  }
  // Сравнение: прошлый период целиком; если текущий ещё идёт — те же первые дни прошлого периода.
  function stCompare(cur) {
    const prev = stPeriod(cur.kind, addDays(cur.start, -1)), stop = addDays(today(), 1);
    if (stop >= cur.end) return { prev, cutCur: cur.end, cutPrev: prev.end, partial: false };
    const n = Math.max(1, Math.round((stop - cur.start) / DAY)), cut = addDays(prev.start, n);
    return { prev, cutCur: stop, cutPrev: cut < prev.end ? cut : prev.end, partial: true };
  }
  // Части периода для столбцов и строк таблицы: неделя и месяц — дни, квартал — недели, год — месяцы.
  function stBuckets(cur) {
    const out = [];
    if (cur.kind === "week" || cur.kind === "month") {
      for (let d = cur.start; d < cur.end; d = addDays(d, 1))
        out.push({ start: d, end: addDays(d, 1), label: WD[d.getDay()] + ", " + fmt(d), row: WD[d.getDay()] + " " + fmtShort(d), short: cur.kind === "week" ? WD[d.getDay()] + " " + d.getDate() : String(d.getDate()) });
    } else if (cur.kind === "quarter") {
      for (let d = weekStartOf(cur.start); d < cur.end; d = addDays(d, 7)) {
        const s = d < cur.start ? cur.start : d, e = addDays(d, 7) > cur.end ? cur.end : addDays(d, 7);
        out.push({ start: s, end: e, label: fmtShort(s) + " – " + fmtShort(addDays(e, -1)), short: fmtShort(s) });
      }
    } else {
      for (let m = 0; m < 12; m++) {
        const s = new Date(cur.start.getFullYear(), m, 1);
        out.push({ start: s, end: new Date(cur.start.getFullYear(), m + 1, 1), label: cap1(MONTHS[m]) + " " + s.getFullYear(), short: cap1(MONTHS[m]).slice(0, 3) });
      }
    }
    return out;
  }

  // Все цифры за отрезок [a, b): то, что позже сегодняшнего дня, не считается.
  function stMetrics(a, b) {
    const stop = addDays(today(), 1);
    if (b > stop) b = stop;
    const A = dayKey(a), B = dayKey(addDays(b, -1)), inK = (k) => k >= A && k <= B, inD = (d) => !!d && d >= a && d < b;
    const m = { A, B };
    // план дня — как во вкладке «Итоги дней»: задачи кроме убранных; выполнение — сделано и половина частичных
    const P = { days: 0, total: 0, done: 0, partial: 0, not_done: 0, moved: 0, open: 0, score: 0, ratings: [], rows: [] };
    rvDays().forEach((d) => {
      if (!inK(d.day)) return;
      const c = d.counts || {};
      if (d.total > 0) P.days += 1;
      P.total += d.total || 0; P.done += c.done || 0; P.partial += c.partial || 0; P.not_done += c.not_done || 0; P.moved += c.moved || 0;
      P.open += (c.planned || 0) + (c.active || 0); P.score += d.score || 0;
      if (d.rating != null) P.ratings.push(d.rating);
      P.rows.push(d);
    });
    P.percent = P.total ? Math.round(100 * P.score / P.total) : null;
    P.rating = P.ratings.length ? P.ratings.reduce((x, y) => x + y, 0) / P.ratings.length : null;
    m.plan = P;
    // движение проектов — записи истории Пульта (сдвиги этапов, слияния, блоки курсов, записи штаба)
    m.events = board.history.filter((h) => inD(h.date));
    // учёба — урок по первому коммиту с его кодом (или по файлу продвижения); блоки — «Пройден блок / модуль»
    const L = (board.stats && board.stats.lessons) || {};
    m.lessons = {}; m.lessonDays = {}; m.lessonCount = 0;
    Object.keys(L).forEach((pid) => (Array.isArray(L[pid]) ? L[pid] : []).forEach((x) => {
      if (!x || !inK(String(x.date || ""))) return;
      (m.lessons[pid] = m.lessons[pid] || []).push(String(x.code));
      m.lessonDays[x.date] = (m.lessonDays[x.date] || 0) + 1; m.lessonCount += 1;
    }));
    m.blocks = m.events.filter((h) => /^Пройден (блок|модуль)/.test(h.raw));
    // идеи — новые по дате идеи; сделанные — переход в «сделано» по журналу статусов (и записанные сразу сделанными)
    m.ideasNew = board.ideaSets.map((set) => ({ set, items: set.items.filter((it) => inD(it.date)) }));
    m.ideasNewCount = m.ideasNew.reduce((s, x) => s + x.items.length, 0);
    m.ideasDone = board.ideaHistory.transitions.concat(board.ideaHistory.bornDone).filter((t) => t.to === "done" && inD(t.date));
    // коммиты — по дням и по репозиториям
    const C = board.stats && board.stats.commits;
    m.commitsKnown = !!(C && Array.isArray(C.repos));
    m.repos = []; m.commitDays = {}; m.commits = 0;
    if (m.commitsKnown) C.repos.forEach((r) => {
      let n = 0;
      const days = r && r.days && typeof r.days === "object" ? r.days : {};
      Object.keys(days).forEach((k) => { if (inK(k)) { const v = +days[k] || 0; n += v; m.commitDays[k] = (m.commitDays[k] || 0) + v; } });
      m.repos.push({ name: String(r.name || ""), project: r.project || "", n, days });
      m.commits += n;
    });
    // проекты: записи истории, уроки и коммиты своего репозитория; «стояли» — в работе, но ничего за период
    const ev = {}, com = {};
    m.events.forEach((h) => { (ev[h.project] = ev[h.project] || []).push(h); });
    m.repos.forEach((r) => { if (r.project) com[r.project] = (com[r.project] || 0) + r.n; });
    const own = (p) => (ev[p.id] || []).length + (m.lessons[p.id] || []).length + (com[p.id] || 0) > 0;
    m.active = board.projects.filter((p) => own(p) || board.projects.some((c) => p.movesWith.includes(c.id) && own(c)))
      .map((p) => ({ p, events: ev[p.id] || [], lessons: (m.lessons[p.id] || []).length, commits: com[p.id] || 0 }));
    m.stood = board.projects.filter((p) => p.status === "work" && !m.active.some((x) => x.p === p));
    return m;
  }

  function stDelta(cur, prev, unit, decimals) {
    if (cur == null || prev == null) return "";
    const d = decimals ? Math.round((cur - prev) * 10) / 10 : Math.round(cur - prev), a = Math.abs(d);
    const t = (decimals ? num1(a) : String(a)) + (unit ? " " + unit : "");
    return d > 0 ? '<span class="trend up">▲ +' + esc(t) + '</span>' : d < 0 ? '<span class="trend down">▼ −' + esc(t) + '</span>' : '<span class="trend">= 0</span>';
  }

  // Сводки: ежедневные сводки новостей из репозитория сводок (PULT_DIGEST_REPO или digest_repo в projects.json).
  // Отметки «Интересно» и «Полезно» программа Пульта пишет в репозиторий и сразу отправляет на GitHub.
  const DG_TOPIC = { "llm-models": tl("Модели"), "llm-research": tl("Исследования и продукты"), "agents-memory": tl("Агенты и память"),
    "security-storage": tl("Утечки и защита"), "hardware": tl("Железо") };
  const dgData = () => (window.BOARD && window.BOARD.digests) || { ok: false, error: "", digests: [] };
  function dgCount() { return (dgData().digests || []).length; }
  const dgFmt = (d) => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d || ""); return m ? m[3] + "." + m[2] + "." + m[1] : String(d || ""); };
  // Перевод сводки (с 31.10.2026): поля i18n[LANG] пункта; нет перевода — русский оригинал.
  const dgTr = (it, key) => { const t = LANG !== "ru" && it && it.i18n && it.i18n[LANG]; return (t && t[key]) || (it && it[key]) || ""; };
  function renderDigest() {
    const box = $("digest");
    if (!box || state.view !== "digest") return;
    const D = dgData(), list = D.digests || [];
    if (!list.length) {
      box.innerHTML = '<div class="card"><h2>' + esc(tl("Сводок пока нет")) + '</h2><p class="sub">' +
        esc(D.ok ? tl("Нажмите «Синхронизировать данные», чтобы забрать новые сводки с GitHub.") : (D.error || tl("Репозиторий сводок не найден."))) + '</p></div>';
      return;
    }
    if (!state.dgDate || !list.some((d) => d.date === state.dgDate)) state.dgDate = list[0].date;
    const cur = list.find((d) => d.date === state.dgDate), marks = cur.marks || {};
    const dates = list.map((d) => {
      const n = (d.items || []).length, hit = Object.values(d.marks || {}).filter((x) => x.interesting || x.useful).length;
      return '<button type="button" data-dg="date:' + esc(d.date) + '" class="dg-date' + (d.date === cur.date ? " active" : "") + '"><b>' + esc(dgFmt(d.date)) + '</b>' +
        '<span>' + n + tl(" п.") + (hit ? " · ★ " + hit : "") + '</span></button>';
    }).join("");
    const items = (cur.items || []).map((it, i) => {
      const mk = marks[it.id] || {};
      const btn = (kind, label) => '<button type="button" class="dg-mark' + (mk[kind] ? " on" : "") + '" aria-pressed="' + !!mk[kind] + '" data-dg="mark:' +
        esc(cur.date) + ':' + esc(it.id) + ':' + kind + ':' + (mk[kind] ? 0 : 1) + '">' + esc(label) + '</button>';
      return '<article class="dg-item"><div class="dg-head"><span class="dg-n">' + (i + 1) + '</span>' +
        (it.topic ? '<span class="dg-topic">' + esc(DG_TOPIC[it.topic] || it.topic) + '</span>' : "") + '<h3>' + esc(dgTr(it, "title")) + '</h3></div>' +
        (it.summary ? '<p>' + esc(dgTr(it, "summary")) + '</p>' : "") +
        (it.why ? '<p class="dg-why"><b>' + esc(tl("Почему важно тебе:")) + '</b> ' + esc(dgTr(it, "why")) + '</p>' : "") +
        '<div class="dg-foot">' + (it.url ? '<a href="' + esc(it.url) + '" target="_blank" rel="noopener noreferrer">' + esc(it.source || it.url) + '</a>' : esc(it.source || "")) +
        (it.published ? '<span class="dg-pub">' + esc(dgFmt(it.published)) + '</span>' : "") +
        '<span class="dg-btns">' + btn("interesting", tl("Интересно")) + btn("useful", tl("Полезно")) + '</span></div></article>';
    }).join("");
    const unvList = (LANG !== "ru" && cur.unverified_i18n && cur.unverified_i18n[LANG]) || cur.unverified || [];
    const unv = unvList.length ? '<div class="card dg-unv"><h2>' + esc(tl("Не проверено")) + '</h2><ul>' +
      unvList.map((u) => '<li>' + esc(u) + '</li>').join("") + '</ul></div>' : "";
    const p = D.push || {};
    const status = p.ok === false ? '<p class="dg-status bad">' + esc(tl("Отметки не отправлены на GitHub: ")) + esc(p.error || "") + '</p>'
      : D.unpushed ? '<p class="dg-status">' + esc(tl("Отметок ждут отправки на GitHub: ")) + D.unpushed + '</p>' : "";
    box.innerHTML = '<div class="dg-wrap"><div class="card dg-dates"><h2>' + esc(tl("Даты")) + '</h2>' + dates + '</div>' +
      '<div class="dg-main"><div class="card"><h2>' + esc(tl("Сводка на ")) + esc(dgFmt(cur.date)) + '</h2>' +
      (cur.error ? '<p class="sub">' + esc(cur.error) + '</p>' : "") +
      (items || '<p class="empty">' + esc(tl("В этой сводке нет пунктов.")) + '</p>') + status + '</div>' + unv + '</div></div>';
  }
  async function digestAction(a, el) {
    const parts = String(a || "").split(":");
    if (parts[0] === "date") { state.dgDate = parts[1]; renderDigest(); return; }
    if (parts[0] !== "mark" || parts.length !== 5) return;
    if (!token) {
      showSync("warn", tl("Отметки недоступны"), [["note", tl("Кнопка работает, когда Пульт открыт ярлыком «XControlP» на рабочем столе, а не как файл.")]]);
      return;
    }
    const [, date, id, kind, value] = parts;
    if (el) el.disabled = true;
    try {
      const q = "date=" + encodeURIComponent(date) + "&id=" + encodeURIComponent(id) + "&kind=" + encodeURIComponent(kind) + "&value=" + encodeURIComponent(value);
      const r = await fetch("/digest/mark?" + q, { method: "POST", headers: { "X-Pult-Token": token } });
      const res = await r.json();
      if (!r.ok || !res.ok) throw new Error(res.error || (tl("ответ ") + r.status));
      refresh();
    } catch (err) {
      if (el) el.disabled = false;
      showSync("bad", tl("Отметка не сохранилась"), [["err", esc(String(err && err.message || err))]]);
    }
  }

  async function svcPost(path, el, failTitle) {
    if (!token) {
      showSync("warn", tl("Флажок недоступен"), [["note", tl("Кнопка работает, когда Пульт открыт ярлыком «XControlP» на рабочем столе, а не как файл.")]]);
      return;
    }
    if (el) el.disabled = true;
    try {
      const r = await fetch(path, { method: "POST", headers: { "X-Pult-Token": token } });
      const res = await r.json();
      if (!r.ok || !res.ok) throw new Error(res.error || (tl("ответ ") + r.status));
      refresh();
    } catch (err) {
      if (el) el.disabled = false;
      showSync("bad", failTitle, [["err", esc(String(err && err.message || err))]]);
    }
  }
  function flagAction(a, el) {
    const [id, on] = String(a || "").split(":");
    svcDelAsk = "";
    svcPost("/idea/flag?id=" + encodeURIComponent(id) + "&on=" + encodeURIComponent(on), el, tl("Флажок не сохранился"));
  }
  function svcDelAction(a, el) {
    const [what, id] = String(a || "").split(":");
    if (what === "ask") { svcDelAsk = id; renderDrawer(); return; }
    svcDelAsk = "";
    if (what === "yes") { svcPost("/idea/service-remove?id=" + encodeURIComponent(id), el, tl("Услуга не убрана")); return; }
    renderDrawer();
  }

  // «Наши услуги»: все услуги отдела, из всех отделов идей; с флажком — сверху, затем новые.
  function renderServices() {
    const box = $("ideas");
    const sv = (x) => serviceOf(x.it.id) || {};
    const list = servicesList().sort((a, b) => (sv(b).flag ? 1 : 0) - (sv(a).flag ? 1 : 0) ||
      String(sv(b).added || "").localeCompare(String(sv(a).added || "")) || a.it.id.localeCompare(b.it.id, undefined, { numeric: true }));
    const rows = list.map((x) => '<tr data-open="idea:' + esc(x.set.id) + ':' + esc(x.it.id) + '" tabindex="0" aria-label="' + esc(tl("Открыть идею ") + x.it.id) + '">' +
      '<td><span class="iid">' + esc(x.it.id) + '</span></td><td><span class="idate">' + (sv(x).added ? fmt(parseDate(sv(x).added)) : "") + '</span></td>' +
      '<td><div class="pname ititle">' + flagMark(x.it.id) + esc(x.it.title) + '</div><div class="pgroup">' + esc(x.set.title) + '</div></td><td>' + ideaChip(x.it) + '</td></tr>').join("");
    box.innerHTML = '<div class="card"><h2>' + esc(tl("Наши услуги")) + '</h2><p class="sub">' +
      esc(tl("То, что мы предоставляем клиентам как платную услугу · зелёный ⚑ — флажок стоит, серый ⚐ — флажок снят, услуга остаётся в списке")) + '</p>' +
      (list.length ? '<table><colgroup><col class="c-id"><col class="c-date"><col><col class="c-istatus"></colgroup><thead><tr><th>' + esc(tl("№")) + '</th><th>' +
        esc(tl("Добавлено")) + '</th><th>' + esc(tl("Идея")) + '</th><th>' + esc(tl("Статус")) + '</th></tr></thead><tbody>' + rows + '</tbody></table>'
        : '<div class="empty">' + esc(tl("В отделе услуг пока пусто — услугу добавляет кнопка «⚑ Добавить в услуги» в карточке идеи")) + '</div>') + '</div>';
  }

