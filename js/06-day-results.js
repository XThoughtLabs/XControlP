"use strict";
  // ---------------------------------------------------------------- Итоги дней (08.10.2026)
  // Закрыть день: оценка 1–10 и итог словами; итоги недель и месяцев из плана дня. Хранит программа Пульта (day.db).
  state.rev = { key: "", data: null, text: "", rating: null, note: null, busy: false, err: "", loading: false };
  function rvKey() { if (!state.rev.key) state.rev.key = dayKey(today()); return state.rev.key; }
  function rvDays() { return state.rev.data && Array.isArray(state.rev.data.days) ? state.rev.data.days : []; }
  function rvDay(key) { return rvDays().find((d) => d.day === key) || null; }
  function rvWeekPercent() {
    const start = dayKey(weekStartOf(today())), end = dayKey(addDays(weekStartOf(today()), 7));
    let planned = 0, score = 0;
    rvDays().forEach((d) => { if (d.day >= start && d.day < end) { planned += d.total; score += d.score; } });
    return planned ? Math.round(100 * score / planned) + "%" : "—";
  }
  async function revLoad(silent) {
    const S = state.rev;
    if (!dpServer()) return;
    if (S.loading) { S.again = S.again || !silent ? true : S.again; return; }   // идёт чтение — перечитать сразу после
    S.loading = true;
    try {
      const r = await fetch("/day-review.json?v=" + Date.now(), { cache: "no-store" });
      const res = await r.json();
      if (!res.ok) S.err = res.error || tl("Итоги дней не прочитались");
      else {
        const text = JSON.stringify(res);
        if (text === S.text && silent) return;
        S.text = text; S.data = res;
        if (!silent) S.err = "";
      }
    } catch (err) {
      S.err = tl("Программа Пульта не отвечает") + ": " + (err && err.message || err);
    } finally {
      S.loading = false;
    }
    renderNav();
    if (state.view === "review") renderReview();
    if (state.view === "stats") renderStats();
    if (S.again) { S.again = false; return revLoad(false); }
  }
  async function revPost(ops) {
    const S = state.rev;
    if (!dpServer()) { S.err = tl("Изменения работают, когда Пульт открыт ярлыком «XControlP» на рабочем столе."); renderReview(); return false; }
    if (S.busy) return false;
    S.busy = true;
    try {
      const r = await fetch("/day/op", { method: "POST", headers: { "X-Pult-Token": token, "Content-Type": "application/json" },
        body: JSON.stringify({ day: rvKey(), ops }) });
      let res = {};
      try { res = await r.json(); } catch (err) { res = { ok: false, error: tl("ответ") + " " + r.status }; }
      if (!r.ok || !res.ok) { S.err = res.error || (tl("ответ") + " " + r.status); return false; }
      S.err = ""; S.rating = null; S.note = null;
      state.day.text = "";
      return true;
    } catch (err) {
      S.err = tl("Не сохранилось") + ": " + (err && err.message || err);
      return false;
    } finally {
      S.busy = false;
      await revLoad(false);
      dayLoad(true);
    }
  }

  function rvAggregate(keyOf, labelOf) {
    const groups = new Map();
    rvDays().forEach((d) => {
      const k = keyOf(d.day);
      const g = groups.get(k) || { key: k, label: labelOf(d.day), days: 0, planned: 0, done: 0, partial: 0, moved: 0, score: 0, ratings: [] };
      if (d.total > 0) g.days += 1;
      g.planned += d.total; g.done += d.counts.done; g.partial += d.counts.partial; g.moved += d.counts.moved; g.score += d.score;
      if (d.rating != null) g.ratings.push(d.rating);
      groups.set(k, g);
    });
    return [...groups.values()].sort((a, b) => (a.key < b.key ? 1 : -1));
  }
  function rvTable(rows, first) {
    if (!rows.length) return '<div class="empty">' + tl("Пока нет дней с планом") + '</div>';
    const avg = (a) => a.length ? (a.reduce((x, y) => x + y, 0) / a.length).toFixed(1) : "—";
    return '<table class="numtab rv-tab"><thead><tr><th>' + first + '</th><th>' + tl("Дней с планом") + '</th><th>' + tl("Задач") + '</th><th>' + tl("Сделано") +
      '</th><th>' + tl("Перенесено") + '</th><th>' + tl("Выполнение") + '</th><th>' + tl("Оценка") + '</th></tr></thead><tbody>' +
      rows.map((g) => '<tr><td>' + esc(g.label) + '</td><td>' + g.days + '</td><td>' + g.planned + '</td><td>' + g.done + (g.partial ? " +" + g.partial + "½" : "") +
        '</td><td>' + g.moved + '</td><td><b>' + (g.planned ? Math.round(100 * g.score / g.planned) + "%" : "—") + '</b></td><td>' + avg(g.ratings) + '</td></tr>').join("") +
      '</tbody></table>';
  }
  function rvChart() {
    const end = today(), start = addDays(end, -29), days = [];
    for (let i = 0; i < 30; i++) { const k = dayKey(addDays(start, i)); days.push(rvDay(k) || { day: k, total: 0, percent: 0, rating: null, counts: {} }); }
    const W = 760, H = 200, L = 40, R = 30, T = 12, B = 26, pw = W - L - R, ph = H - T - B, bw = pw / days.length;
    let svg = '<svg class="rv-chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(tl("Выполнение и оценка по дням")) + '">';
    [0, 50, 100].forEach((v) => { const y = T + ph - ph * v / 100;
      svg += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y + '" y2="' + y + '" stroke="var(--grid)"/><text x="' + (L - 6) + '" y="' + (y + 4) + '" text-anchor="end" fill="var(--muted)" font-size="10">' + v + '%</text>' +
        '<text x="' + (W - R + 6) + '" y="' + (y + 4) + '" fill="var(--k-future)" font-size="10">' + (v / 10) + '</text>'; });
    const pts = [];
    days.forEach((d, i) => {
      const x = L + i * bw, h = ph * (d.total ? d.percent : 0) / 100, dd = parseDate(d.day);
      const tip = esc(fmt(dd)) + (d.total ? "<br>" + esc(tl("Выполнение")) + ": " + d.percent + "% · " + d.counts.done + " / " + d.total : "<br>" + esc(tl("Плана не было"))) +
        (d.rating != null ? "<br>" + esc(tl("Оценка")) + ": " + d.rating + "/10" : "");
      svg += '<rect x="' + (x + 2) + '" y="' + (T + ph - h) + '" width="' + Math.max(2, bw - 4) + '" height="' + Math.max(h, d.total ? 1 : 0) + '" rx="2" fill="' +
        (d.percent >= 80 ? "var(--good)" : d.percent >= 50 ? "var(--series-1)" : "var(--warning)") + '" data-tip="' + esc(tip) + '"/>';
      if (d.rating != null) pts.push([x + bw / 2, T + ph - ph * d.rating / 10]);
      if (i % 5 === 0 || i === days.length - 1) svg += '<text x="' + (x + bw / 2) + '" y="' + (H - 8) + '" text-anchor="middle" fill="var(--muted)" font-size="10">' + dpShort(d.day) + '</text>';
    });
    if (pts.length > 1) svg += '<polyline fill="none" stroke="var(--k-future)" stroke-width="2" points="' + pts.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ") + '"/>';
    pts.forEach((p) => { svg += '<circle cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="3.5" fill="var(--k-future)"/>'; });
    return svg + '</svg><div class="rv-legend"><span><i class="bar"></i>' + tl("Выполнение плана, %") + '</span><span><i class="dot"></i>' + tl("Оценка дня, 1–10") + '</span></div>';
  }

  function renderReview() {
    const S = state.rev, box = $("review");
    if (!box || state.view !== "review") return;
    const key = rvKey(), d = rvDay(key), c = d ? d.counts : {}, total = d ? d.total : 0;
    const focus = document.activeElement && box.contains(document.activeElement) ? document.activeElement.id : "";
    const open = d ? (c.planned || 0) + (c.active || 0) + (c.partial || 0) + (c.not_done || 0) : 0;
    const closed = d && d.closed, rating = S.rating != null ? S.rating : d && d.rating != null ? d.rating : null;
    const bar = '<div class="cal-bar">' +
      '<button type="button" class="cal-btn" data-rv="prev" aria-label="' + esc(tl("Предыдущий день")) + '">‹</button>' +
      '<button type="button" class="cal-btn" data-rv="today">' + tl("Сегодня") + '</button>' +
      '<button type="button" class="cal-btn" data-rv="next" aria-label="' + esc(tl("Следующий день")) + '">›</button>' +
      '<span class="cal-label">' + esc(dpDayTitle(key)) + '</span>' +
      '<input type="date" class="rv-date" value="' + esc(key) + '" aria-label="' + esc(tl("Перейти к дню")) + '">' +
      '<button type="button" class="cal-btn" data-rv="plan">' + tl("План этого дня") + '</button></div>';
    let card;
    if (!dpServer()) card = '<div class="card"><div class="empty">' + tl("Итоги дней работают, когда Пульт открыт ярлыком «XControlP» на рабочем столе.") + '</div></div>';
    else {
      const chip = (label, n, cls) => '<span class="rv-n ' + (cls || "") + '"><b>' + n + '</b>' + label + '</span>';
      card = '<div class="card rv-close"><h2>' + (closed ? tl("День закрыт") : tl("Закрыть день")) + '</h2><p class="sub">' +
        (closed ? tl("Закрыт") + " " + esc(stamp(d.closed_at)) + " · " + tl("оценку и итог можно поменять") : tl("Оцените день и напишите итог — он попадёт в итоги недель и месяцев")) + '</p>' +
        '<div class="rv-stats">' + chip(tl("в плане"), total) + chip(tl("сделано"), c.done || 0, "good") + chip(tl("частично"), c.partial || 0, "part") +
        chip(tl("не сделано"), c.not_done || 0, "bad") + chip(tl("перенесено"), c.moved || 0) + chip(tl("выполнение"), (d && total ? d.percent : 0) + "%", "big") + '</div>' +
        (open ? '<div class="cal-hint">' + tl("Незаконченных задач") + ': <b>' + open + '</b><button type="button" class="cal-btn" data-rv="carry">' + tl("Все незаконченные — на завтра") + '</button></div>' : "") +
        '<div class="dp-l">' + tl("Оценка дня") + '<div class="rv-rate" role="group" aria-label="' + esc(tl("Оценка дня")) + '">' +
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => '<button type="button" data-rv="rate:' + n + '" class="r' + n + (rating === n ? " on" : "") + '" aria-pressed="' + (rating === n) + '">' + n + '</button>').join("") +
        '</div></div>' +
        '<label class="dp-l">' + tl("Итог дня словами") + '<textarea id="rv-note" rows="3" maxlength="4000" placeholder="' + esc(tl("Например: урок английского сделан, отчёт — завтра")) + '">' +
        esc(S.note != null ? S.note : d ? d.note : (state.day.data && state.day.data.day === key ? state.day.data.note : "")) + '</textarea></label>' +
        '<div class="rv-actions"><button type="button" class="cal-btn primary" data-rv="close"' + (S.busy ? " disabled" : "") + '>' + (closed ? tl("Сохранить оценку") : tl("Закрыть день")) + '</button>' +
        (closed ? '<button type="button" class="cal-btn" data-rv="reopen">' + tl("Открыть день снова") + '</button>' : "") + '</div></div>';
    }
    const weeks = rvAggregate((k) => dayKey(weekStartOf(parseDate(k))), (k) => { const s = weekStartOf(parseDate(k)); return dpShort(dayKey(s)) + " – " + dpShort(dayKey(addDays(s, 6))); }).slice(0, 12);
    const months = rvAggregate((k) => k.slice(0, 7), (k) => { const m = parseDate(k); return MONTHS[m.getMonth()][0].toUpperCase() + MONTHS[m.getMonth()].slice(1) + " " + m.getFullYear(); }).slice(0, 12);
    box.innerHTML = bar + (S.err ? '<div class="cal-hint dp-err">' + esc(S.err) + '<button type="button" class="cal-btn" data-rv="reload">' + tl("Обновить") + '</button></div>' : "") +
      '<div class="rv-cols"><div class="rv-main">' + card + '</div><div class="rv-side"><div class="card"><h2>' + tl("По дням") + '</h2><p class="sub">' +
      tl("Последние 30 дней: сколько из плана сделано и как вы оценили день · наведите на столбец") + '</p>' + rvChart() + '</div></div></div>' +
      '<div class="card"><h2>' + tl("Недели") + '</h2><p class="sub">' + tl("Неделя — с воскресенья · выполнение: сделано и половина частичных из всех задач плана, кроме убранных") + '</p>' + rvTable(weeks, tl("Неделя")) + '</div>' +
      '<div class="card"><h2>' + tl("Месяцы") + '</h2><p class="sub">' + tl("Те же итоги по месяцам") + '</p>' + rvTable(months, tl("Месяц")) + '</div>';
    if (focus) { const el = document.getElementById(focus); if (el) el.focus(); }
  }

  async function revAction(a) {
    const S = state.rev;
    const [cmd, arg] = a.split(":");
    const go = (key) => { S.key = key; S.rating = null; S.note = null; S.err = ""; renderReview(); };
    if (cmd === "prev" || cmd === "next") return go(dayKey(addDays(parseDate(rvKey()), cmd === "prev" ? -1 : 1)));
    if (cmd === "today") return go(dayKey(today()));
    if (cmd === "goto") return parseDate(arg) ? go(arg) : undefined;
    if (cmd === "reload") { S.err = ""; return revLoad(false); }
    if (cmd === "plan") { state.day.key = rvKey(); state.view = "day"; history.replaceState(null, "", "#day"); render(); return dayLoad(false); }
    if (cmd === "rate") { S.rating = +arg; return renderReview(); }
    if (cmd === "carry") return revPost([{ op: "carry_open", day: rvKey() }]);
    if (cmd === "reopen") return revPost([{ op: "reopen_day", day: rvKey() }]);
    if (cmd === "close") {
      const d = rvDay(rvKey()), rating = S.rating != null ? S.rating : d && d.rating != null ? d.rating : null;
      if (rating == null) { S.err = tl("Поставьте оценку дня от 1 до 10."); return renderReview(); }
      const t2 = $("rv-note");
      return revPost([{ op: "close_day", day: rvKey(), rating, note: t2 ? t2.value : "" }]);
    }
  }

