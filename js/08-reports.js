"use strict";
  // ---------------------------------------------------------------- Раздел «Отчёты»
  // Недельные отчёты штаба из папки reports/weekly (или reports_dir из projects.json): оригинал (.md) и файл данных (.json рядом, с тем же именем).
  // Неделя открывается на главном экране: категории с пояснениями, таблицами и графиками; «Оригинал» — полный текст.
  // Месячные отчёты — из reports/monthly; в списке переключатель «Недели / Месяцы».
  const rpList = () => (board && board.reports && board.reports.entries) || [];
  const rpMonths = () => (board && board.reports && board.reports.months) || [];
  const rpAll = () => rpList().concat(rpMonths());
  const rpIsMonth = (r) => /^Monthly report /.test(String((r && r.file) || ""));
  const rpKindList = (kind) => (kind === "months" ? rpMonths() : rpList());
  const rpCap = (s) => String(s || "").charAt(0).toUpperCase() + String(s || "").slice(1);
  const rpShort = (d) => String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0");
  const RP_LOC = LANG === "ru" ? "ru-RU" : LANG === "he" ? "he-IL" : "en-US";
  const rpT = (o) => (o && typeof o === "object" && !Array.isArray(o)) ? String(o[LANG] || o.ru || o.en || "") : (o == null ? "" : String(o));
  // Язык оригинала: поле original файла данных; без него — русский для старых имён «Недельный отчёт …», иначе английский.
  const rpOrig = (r) => { const o = r && r.data && r.data.original; return o === "ru" || o === "en" || o === "he" ? o : (/^Недельный отчёт /.test(String((r && r.file) || "")) ? "ru" : "en"); };
  const RP_ORIG_NOTE = { ru: "Оригинал отчёта — на русском", en: "Оригинал отчёта — на английском", he: "Оригинал отчёта — на иврите" };
  const rpNum = (n, dec) => typeof n === "number" ? n.toLocaleString(RP_LOC, { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 }) : String(n == null ? "" : n);
  const RP_ICON = Object.assign(Object.create(null), { summary: "obzor", tech: "tech", study: "study", services: "services", day: "dayplan", code: "stats",
    ideas: "ideas", resources: "perf", decisions: "digest", risks: "alerts", proposals: "growth", rating: "review" });   // без прототипа, как GROUP_ICON
  const RP_KPI = { commits: "Коммиты", repos: "Репозиториев с коммитами", tasks: "Задач в плане дня", done_pct: "Сделано задач", day_rating: "Оценка дней",
    lessons: "Уроков", ideas_new: "Новых идей", hq_rating: "Оценка штаба" };
  const RP_TONE = { good: "var(--good)", warn: "var(--warning)", bad: "var(--critical)" };
  state.rp = (function () {
    try { const v = JSON.parse(sessionStorage.getItem("pult-rp") || "null"); if (v && typeof v === "object") return v; } catch (err) { /* без хранилища */ }
    return { open: "", cat: "all", doc: false, kind: "weeks" };
  })();
  let rpNote = "";
  function rpSave() { try { sessionStorage.setItem("pult-rp", JSON.stringify(state.rp)); } catch (err) { /* без хранилища */ } }
  function rpWeek(r) {
    if (rpIsMonth(r)) {
      const m = parseDate(r.start);
      return m ? rpCap(MONTHS[m.getMonth()]) + " " + m.getFullYear() : String(r.file || "");
    }
    const a = parseDate(r.start), b = parseDate(r.end);
    return a && b ? rpShort(a) + "–" + rpShort(b) + "." + b.getFullYear() : String(r.file || "");
  }
  function rpAction(v) {
    const [cmd, ...rest] = String(v || "").split(":"), arg = rest.join(":");
    if (cmd === "reveal") { rpReveal(arg); return; }
    const kind = state.rp.kind === "months" ? "months" : "weeks";
    if (cmd === "open") state.rp = { open: arg, cat: "all", doc: false, kind };
    else if (cmd === "list") state.rp = { open: "", cat: "all", doc: false, kind };
    else if (cmd === "kind") state.rp = { open: "", cat: "all", doc: false, kind: arg === "months" ? "months" : "weeks" };
    else if (cmd === "cat") state.rp = Object.assign({}, state.rp, { cat: arg, doc: false });
    else if (cmd === "doc") state.rp = Object.assign({}, state.rp, { doc: !state.rp.doc });
    rpNote = "";
    rpSave();
    renderReports();
    const top = $("ideas");
    if (top && top.scrollIntoView) top.scrollIntoView({ block: "start" });
  }
  async function rpReveal(file) {
    let ok = false;
    if (token) {
      try {
        const r = await fetch("/report/reveal?file=" + encodeURIComponent(file), { method: "POST", headers: { "X-Pult-Token": token } });
        const res = await r.json().catch(() => ({}));
        ok = r.ok && !!res.ok;
      } catch (err) { ok = false; }
    }
    rpNote = ok ? "" : tl("Папка не открылась");
    if (!ok) renderReports();
  }

  // ---- кирпичики отчёта: пункты, таблица, графики (столбики, стопки по дням, линия), цитаты, нумерованный список
  const rpH = (b) => b && b.title ? '<h4 class="rp-h">' + esc(rpT(b.title)) + '</h4>' : "";
  const rpCell = (c) => typeof c === "number" ? esc(rpNum(c)) : mdInline(rpT(c));
  function rpFig(b, inner) {
    return '<figure class="rp-fig"><figcaption>' + esc(rpT(b.title)) + (b.unit ? ' · ' + esc(rpT(b.unit)) : "") + '</figcaption>' + inner +
      (b.note ? '<p class="rp-fnote">' + mdInline(rpT(b.note)) + '</p>' : "") + '</figure>';
  }
  function rpBar(b) {
    const items = (b.items || []).filter((x) => x && typeof x.value === "number" && x.value >= 0);
    const max = Math.max(1, ...items.map((x) => x.value));
    return rpFig(b, '<div class="rp-bars">' + items.map((x) => {
      const label = rpT(x.label), w = x.value > 0 ? Math.max(1, x.value / max * 100) : 0;
      return '<span class="rp-bl">' + esc(label) + '</span><span class="rp-bt" title="' + esc(label + ": " + rpNum(x.value)) + '">' +
        (w ? '<span style="width:' + w.toFixed(1) + '%;background:var(--series-1)"></span>' : "") + '</span><span class="rp-bv">' + esc(rpNum(x.value)) + '</span>';
    }).join("") + '</div>');
  }
  function rpStack(b) {
    const keys = b.keys || [], items = (b.items || []).filter((x) => x && Array.isArray(x.values));
    const sum = (x) => x.values.reduce((a, v) => a + (typeof v === "number" && v > 0 ? v : 0), 0);
    const max = Math.max(1, ...items.map(sum));
    const legend = '<div class="rp-legend">' + keys.map((k) => '<span><i style="background:' + (RP_TONE[k.tone] || "var(--other)") + '"></i>' + esc(rpT(k.label)) + '</span>').join("") +
      (b.extra ? '<span><b>★</b>' + esc(rpT(b.extra)) + '</span>' : "") + '</div>';
    return rpFig(b, legend + '<div class="rp-stk">' + items.map((x) => {
      const label = rpT(x.label);
      const segs = x.values.map((v, k) => typeof v === "number" && v > 0 ? '<span style="width:' + (v / max * 100).toFixed(1) + '%;background:' + (RP_TONE[(keys[k] || {}).tone] || "var(--other)") + '" title="' +
        esc(label + " · " + rpT((keys[k] || {}).label) + ": " + rpNum(v)) + '"></span>' : "").join("");
      return '<span class="rp-bl">' + esc(label) + '</span><span class="rp-bt">' + segs + '</span><span class="rp-bv">' + esc(rpNum(sum(x))) +
        (typeof x.extra === "number" ? '<b>★ ' + esc(rpNum(x.extra)) + '</b>' : "") + '</span>';
    }).join("") + '</div>');
  }
  function rpLine(b) {
    const items = (b.items || []).filter((x) => x && typeof x.value === "number");
    if (!items.length) return "";
    const W = 600, H = 200, padX = 60, top = 30, bottom = 40, pre = String(b.prefix || "");
    const max = Math.max(...items.map((x) => x.value), 1);
    const xs = (i) => items.length === 1 ? W / 2 : padX + i * (W - 2 * padX) / (items.length - 1);
    const ys = (v) => top + (H - top - bottom) * (1 - v / max);
    const short = (x) => rpT(x.label).split(",")[0];
    const pts = items.map((x, i) => xs(i).toFixed(1) + "," + ys(x.value).toFixed(1)).join(" ");
    let svg = '<svg class="rp-line" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(rpT(b.title)) + '" direction="ltr">' +
      '<line x1="' + (padX - 30) + '" y1="' + ys(0) + '" x2="' + (W - padX + 30) + '" y2="' + ys(0) + '" stroke="var(--axis)" stroke-width="1"/>' +
      '<polyline points="' + pts + '" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round"/>';
    items.forEach((x, i) => {
      const cx = xs(i), cy = ys(x.value), val = pre + rpNum(x.value);
      svg += '<g><title>' + esc(rpT(x.label) + ": " + val) + '</title><circle cx="' + cx + '" cy="' + cy + '" r="12" fill="transparent"/>' +
        '<circle cx="' + cx + '" cy="' + cy + '" r="5" fill="var(--series-1)" stroke="var(--card)" stroke-width="2"/>' +
        '<text x="' + cx + '" y="' + (cy - 12) + '" text-anchor="middle" fill="var(--text)" font-size="13" font-weight="700">' + esc(val) + '</text>' +
        '<text x="' + cx + '" y="' + (H - 14) + '" text-anchor="middle" fill="var(--text-2)" font-size="12">' + esc(short(x)) + '</text></g>';
    });
    svg += '</svg>';
    const notes = items.filter((x) => rpT(x.label).includes(",")).map((x) => '<li>' + esc(rpT(x.label)) + ' — ' + esc(pre + rpNum(x.value)) + '</li>').join("");
    return rpFig(b, svg + (notes ? '<ul class="rp-pts rp-fnote">' + notes + '</ul>' : ""));
  }
  function rpTable(b) {
    const cols = b.columns || [], rows = (b.rows || []).filter(Array.isArray);
    return rpH(b) + '<div class="rp-table"><table><thead><tr>' + cols.map((c) => '<th>' + esc(rpT(c)) + '</th>').join("") + '</tr></thead><tbody>' +
      rows.map((r) => '<tr>' + r.map((c) => '<td>' + rpCell(c) + '</td>').join("") + '</tr>').join("") +
      (Array.isArray(b.total) ? '<tr class="rp-total">' + b.total.map((c) => '<td>' + rpCell(c) + '</td>').join("") + '</tr>' : "") + '</tbody></table></div>';
  }
  function rpQuotes(b) {
    return rpH(b) + '<div class="rp-quotes">' + (b.items || []).map((q) => {
      const tr = q.verbatim && LANG !== "ru" && q.text && q.text.ru;
      return '<blockquote class="rp-q"' + (tr ? ' title="' + esc(q.text.ru) + '"' : "") + '><div class="rp-qm"><span class="rp-qd">' + esc(q.date || "") + '</span> · ' + esc(rpT(q.topic)) +
        (tr ? '<span class="rp-tr">' + esc(tl("перевод")) + '</span>' : "") + '</div>' + mdInline(rpT(q.text)) + '</blockquote>';
    }).join("") + '</div>';
  }
  // ctx — только у разделов «Риски» и «Предложения»: тогда у каждого пункта кнопка «В план дня».
  const rpPlan = (ctx, i, title) => ctx ? " " + planBtn(ctx.src + "." + i, title, "", ctx.from) : "";
  const rpPoints = (b, ctx) => rpH(b) + '<ul class="rp-pts">' + (b.items || []).map((x, i) => '<li>' + mdInline(rpT(x)) + rpPlan(ctx, i, rpT(x)) + '</li>').join("") + '</ul>';
  const rpOl = (b, ctx) => rpH(b) + '<ol class="rp-ol">' + (b.items || []).map((x, i) => '<li><b>' + esc(rpT(x.title)) + '.</b> ' + mdInline(rpT(x.text)) +
    rpPlan(ctx, i, rpT(x.title) + ": " + rpT(x.text)) + '</li>').join("") + '</ol>';
  const RP_PLAN_CATS = ["risks", "proposals"];
  function rpBlock(b, ctx) {
    if (!b || typeof b !== "object") return "";
    try {
      if (b.type === "points") return rpPoints(b, ctx);
      if (b.type === "table") return rpTable(b);
      if (b.type === "bar") return rpBar(b);
      if (b.type === "stack") return rpStack(b);
      if (b.type === "line") return rpLine(b);
      if (b.type === "quotes") return rpQuotes(b);
      if (b.type === "list") return rpOl(b, ctx);
      if (b.type === "text") return '<p class="rp-lead">' + mdInline(rpT(b.text)) + '</p>';
    } catch (err) { return '<p class="rs-note">' + esc(tl("Блок отчёта не читается")) + '</p>'; }
    return "";
  }
  function rpKpis(D, prev) {
    const P = prev && prev.data && Array.isArray(prev.data.kpis) ? prev.data.kpis : null;
    const tiles = (Array.isArray(D.kpis) ? D.kpis : []).filter((k) => k && RP_KPI[k.id] && typeof k.value === "number").map((k) => {
      const dec = k.id === "day_rating" ? 1 : 0, unit = k.id === "done_pct" ? "%" : "", p = P && P.find((x) => x && x.id === k.id);
      let delta = "";
      if (p && typeof p.value === "number") {
        const d = Math.round((k.value - p.value) * 10) / 10;
        delta = '<span class="rp-delta">' + (d > 0 ? "▲ +" + rpNum(d, dec) + unit : d < 0 ? "▼ −" + rpNum(-d, dec) + unit : "= 0") + '</span>';
      }
      return '<div class="rp-kpi"><div class="rp-kv">' + esc(rpNum(k.value, dec) + unit) + (/rating$/.test(k.id) ? '<small> / 10</small>' : "") + '</div><div class="rp-kl">' +
        esc(tl(RP_KPI[k.id])) + '</div>' + delta + '</div>';
    }).join("");
    return tiles ? '<div class="rp-kpis">' + tiles + '</div>' + (P ? '<p class="rs-note">' + esc(tl(rpIsMonth(prev) ? "Стрелки — сравнение с прошлым месяцем" : "Стрелки — сравнение с прошлой неделей")) + ' · ' + esc(rpWeek(prev)) + '</p>' : "") : "";
  }
  function rpReport(r, all) {
    const prev = all.slice(all.indexOf(r) + 1).find((x) => x.data), D = r.data;
    const pending = r.pushed === false ? '<span class="rp-pending" title="' + esc(tl("Отчёт ещё не отправлен на GitHub")) + '">' + esc(tl("не отправлен")) + '</span>' : "";
    const head = '<div class="rp-head"><button type="button" class="svc-btn" data-rp="list">← ' + esc(tl("Все отчёты")) + '</button><h2 class="rp-title">' + esc(tl(rpIsMonth(r) ? "Месяц" : "Неделя")) +
      ' <span class="rp-week">' + esc(rpWeek(r)) + '</span></h2>' + pending + '<span class="rp-tools">' +
      (D ? '<button type="button" class="svc-btn' + (state.rp.doc ? " on" : "") + '" data-rp="doc">' + esc(tl(state.rp.doc ? "Категории" : "Оригинал")) + '</button>' : "") +
      '<button type="button" class="svc-btn" data-rp="reveal:' + esc(r.file) + '" title="' + esc(r.file) + '">' + esc(tl("Показать в папке")) + '</button></span></div>' +
      (rpNote ? '<p class="rs-note">' + esc(rpNote) + '</p>' : "");
    if (!D || state.rp.doc) {
      const why = D ? "" : r.data_error ? tl("Файл данных отчёта не читается — показан оригинал") : tl("Для этого отчёта нет файла данных — показан оригинал");
      return '<div class="card">' + head + (why ? '<p class="rs-note">' + esc(why) + '</p>' : "") + (LANG !== rpOrig(r) ? '<p class="rs-note">' + esc(tl(RP_ORIG_NOTE[rpOrig(r)])) + '</p>' : "") +
        '<div class="rs-doc" lang="' + rpOrig(r) + '" dir="' + (rpOrig(r) === "he" ? "rtl" : "ltr") + '">' + (r.text ? mdHtml(r.text) : '<div class="empty">' + esc(tl("Текст отчёта не читается")) + '</div>') + '</div></div>';
    }
    const cats = (Array.isArray(D.categories) ? D.categories : []).filter((c) => c && c.id && Array.isArray(c.blocks));
    const sel = cats.some((c) => c.id === state.rp.cat) ? state.rp.cat : "all";
    const chip = (id, label, icon) => '<button type="button" class="rp-cat' + (sel === id ? " on" : "") + '" data-rp="cat:' + esc(id) + '" aria-pressed="' + (sel === id) + '">' +
      (icon ? navIcon(icon, "") : "") + '<span>' + esc(label) + '</span></button>';
    const chips = '<div class="rp-cats" role="group" aria-label="' + esc(tl("Категории")) + '">' + chip("all", tl("Все"), "") +
      cats.map((c) => chip(c.id, rpT(c.title), RP_ICON[c.id])).join("") + '</div>';
    const shown = sel === "all" ? cats : cats.filter((c) => c.id === sel);
    return '<div class="card">' + head + '<p class="rp-lead">' + (typeof D.rating === "number" ? '<span class="rp-score">' + esc(tl("Оценка штаба")) + ': ' + esc(rpNum(D.rating)) + ' / 10</span> · ' : "") +
      mdInline(rpT(D.summary)) + '</p>' + rpKpis(D, prev) + chips + '</div>' +
      shown.map((c) => '<section class="rp-sec"><h3>' + navIcon(RP_ICON[c.id], "") + '<span>' + esc(rpT(c.title)) + '</span></h3>' +
        c.blocks.map((b, bi) => rpBlock(b, RP_PLAN_CATS.includes(c.id) ? { src: "rp:" + (D.start || r.file) + ":" + c.id + ":" + bi,
          from: tl(rpIsMonth(r) ? "Из месячного отчёта" : "Из отчёта") + " " + rpWeek(r) + " · " + rpT(c.title) } : null)).join("") + '</section>').join("");
  }
  // Запросы штабу и предложения. Кнопка кладёт запрос со снимком Пульта в папку
  // requests; пользователь просит штаб в чате разобрать его; штаб кладёт ответ (pult-answer, три языка) в папку answers.
  // Вкладка «Предложения» показывает ответы; у предложения «В план дня» и «Отклонить». Сводка дня — карточкой на обзоре.
  const prAnswers = () => (board && board.answers) || [];
  const prWaiting = () => ((board && board.requests) || []).filter((r) => !r.answered);
  const prMark = (key) => (board && board.proposalMarks && board.proposalMarks[key]) || null;
  const prKey = (a, p) => a.id + "|" + p.id;
  const prKindName = (k) => k === "summary" ? tl("Сводка дня") : tl("Предложения");
  const prOpen = () => prAnswers().reduce((n, a) => n + (a.data && Array.isArray(a.data.proposals) ? a.data.proposals.filter((p) => !prMark(prKey(a, p))).length : 0), 0);
  function prSnapshot() {
    const key = dayKey(today()), D = state.day.data && state.day.data.day === key ? state.day.data : null;
    const alerts = sysAlerts().concat(...board.projects.map((p) => alertsOf(p)));
    const wk = stPeriod("week", today()), W = stMetrics(wk.start, wk.end);
    return { today: key, lang: LANG,
      day_plan: D ? dpVisible(D.items).map((i) => ({ title: i.title, project: i.project_id || "", kind: i.kind, status: i.status, priority: i.priority })) : null,
      alerts: alerts.map((a) => ({ level: a.level, title: a.title, text: a.text, project: a.project || "", mark: markOf(a) })),
      projects: board.projects.map((p) => ({ id: p.id, name: p.name, group: p.group, status: p.status, stage: p.stages[p.current] || "",
        current: p.current, stages: p.stages.length, days_since_move: p.days })),
      week: { from: dayKey(wk.start), plan: { total: W.plan.total, done: W.plan.done, partial: W.plan.partial, not_done: W.plan.not_done, open: W.plan.open },
        ideas_new: W.ideasNewCount, ideas_done: W.ideasDone.length },
      waiting_requests: prWaiting().length, open_proposals: prOpen() };
  }
  async function prRequest(kind, el) {
    if (!dpServer()) { showSync("warn", tl("Запрос не создан"), [["note", tl("Кнопка работает, когда Пульт открыт ярлыком «XControlP» на рабочем столе.")]]); return; }
    if (el) el.disabled = true;
    try {
      const r = await fetch("/request?kind=" + encodeURIComponent(kind), { method: "POST", headers: { "X-Pult-Token": token, "Content-Type": "application/json" },
        body: JSON.stringify(prSnapshot()) });
      let res = {};
      try { res = await r.json(); } catch (err) { res = { ok: false, error: tl("ответ ") + r.status }; }
      if (!r.ok || !res.ok) throw new Error(res.error || (tl("ответ ") + r.status));
      showSync("", tl("Запрос создан"), [["note", tl("Напишите в чате штаба: «разбери запрос». Ответ появится во вкладке «Предложения».")]]);
      refresh();
    } catch (err) {
      showSync("bad", tl("Запрос не создан"), [["err", esc(String(err && err.message || err))]]);
    } finally {
      if (el) el.disabled = false;
    }
  }
  async function prMarkSet(key, st, el) {
    if (el) el.disabled = true;
    try {
      const r = await fetch("/proposal?key=" + encodeURIComponent(key) + "&state=" + encodeURIComponent(st), { method: "POST", headers: { "X-Pult-Token": token } });
      const res = await r.json();
      if (!r.ok || !res.ok) throw new Error(res.error || (tl("ответ ") + r.status));
      refresh();
    } catch (err) {
      if (el) el.disabled = false;
      showSync("bad", tl("Отметка предложения не сохранилась"), [["err", esc(String(err && err.message || err))]]);
    }
  }
  function prAnswerHtml(a) {
    const D = a.data;
    if (!D) return '<div class="card"><p class="rs-note">' + esc(tl("Ответ штаба не читается")) + ': ' + esc(a.file) + (a.error ? " · " + esc(a.error) : "") + '</p></div>';
    const props = (Array.isArray(D.proposals) ? D.proposals : []).map((p) => {
      const key = prKey(a, p), st = (prMark(key) || {}).state || "", proj = p.project ? board.projects.find((x) => x.id === p.project) : null;
      const btns = st === "declined" ? '<span class="pr-st">' + esc(tl("отклонено")) + '</span><button type="button" class="albtn" data-pr="active:' + esc(key) + '">' + esc(tl("Вернуть")) + '</button>'
        : st === "accepted" ? '<span class="plan-in">✓ ' + esc(tl("уже в плане")) + '</span>'
        : planBtn("pr:" + key, rpT(p.text), proj ? proj.id : "", tl("Из предложений штаба")) +
          (dpServer() ? '<button type="button" class="albtn" data-pr="declined:' + esc(key) + '">' + esc(tl("Отклонить")) + '</button>' : "");
      return '<li class="pr-item' + (st ? " pr-" + st : "") + '"><div>' + mdInline(rpT(p.text)) + (proj ? ' <span class="pr-proj">· ' + esc(proj.name) + '</span>' : "") + '</div>' +
        (p.why ? '<div class="pr-why">' + mdInline(rpT(p.why)) + '</div>' : "") + '<div class="albtns">' + btns + '</div></li>';
    }).join("");
    return '<div class="card pr-card"><div class="rp-head"><h2 class="rp-title">' + esc(rpT(D.title)) + ' <span class="rp-week">' + esc(stamp(D.written)) + '</span></h2>' +
      '<span class="pr-kind">' + esc(prKindName(D.kind)) + '</span></div>' + (D.summary ? '<p class="rp-lead">' + mdInline(rpT(D.summary)) + '</p>' : "") +
      (Array.isArray(D.blocks) ? D.blocks.map((b) => rpBlock(b)).join("") : "") +
      (props ? '<h3 class="mini-h">' + esc(tl("Предложения штаба")) + '</h3><ul class="pr-list">' + props + '</ul>' : "") + '</div>';
  }
  const prButtons = () => (dpServer() ? '<button type="button" class="svc-btn" data-prq="summary">' + esc(tl("Запросить сводку дня")) + '</button>' +
    '<button type="button" class="svc-btn" data-prq="proposals">' + esc(tl("Запросить предложения")) + '</button>' : "");
  function renderProposals() {
    const waiting = prWaiting(), answers = prAnswers();
    $("ideas").innerHTML = '<div class="card"><div class="rp-head"><h2>' + esc(tl("Запросы штабу")) + '</h2><span class="rp-tools">' + prButtons() +
      '<button type="button" class="svc-btn" data-prq="load">' + esc(tl("Загрузить предложения")) + '</button></span></div>' +
      '<p class="sub">' + esc(tl("Кнопка запроса кладёт снимок Пульта в папку «requests». Напишите в чате штаба «разбери запрос» — ответ штаба появится здесь.")) + '</p>' +
      (waiting.length ? '<ul class="pr-wait">' + waiting.map((r) => '<li>⏳ ' + esc(stamp(r.created)) + ' · ' + esc(prKindName(r.kind)) + ' — ' + esc(tl("ждёт разбора в чате штаба")) + '</li>').join("") + '</ul>' : "") + '</div>' +
      (answers.length ? answers.map(prAnswerHtml).join("") : '<div class="card"><div class="empty">' + esc(tl("Ответов штаба пока нет")) + '</div></div>');
  }
  function renderHqDay() {
    const el = $("hqday");
    if (!el) return;
    el.hidden = state.view !== "all";
    if (el.hidden) return;
    const key = dayKey(today()), open = prOpen();
    const sum = prAnswers().find((a) => a.data && a.data.kind === "summary" && String(a.data.written).slice(0, 10) === key);
    const waitSum = prWaiting().some((r) => r.kind === "summary");
    el.innerHTML = '<div class="card hq-card"><div class="rp-head"><h2>' + esc(tl("Сводка дня")) + (sum ? ' <span class="rp-week">' + esc(stamp(sum.data.written)) + '</span>' : "") + '</h2>' +
      '<span class="rp-tools">' + prButtons() + '<button type="button" class="svc-btn" data-goto="proposals">' + esc(tl("Предложения")) + (open ? " · " + open : "") + '</button></span></div>' +
      (sum ? (sum.data.summary ? '<p class="rp-lead">' + mdInline(rpT(sum.data.summary)) + '</p>' : "") + (Array.isArray(sum.data.blocks) ? sum.data.blocks.slice(0, 2).map((b) => rpBlock(b)).join("") : "")
        : '<p class="sub">' + esc(waitSum ? tl("Запрос сводки ждёт разбора в чате штаба") : tl("Сводки на сегодня ещё нет — нажмите «Запросить сводку дня»")) + '</p>') + '</div>';
  }

  function renderReports() {
    const box = $("ideas"), R = board.reports || {}, kind = state.rp.kind === "months" ? "months" : "weeks", all = rpKindList(kind);
    const cur = state.rp.open ? rpAll().find((r) => r.file === state.rp.open) : null;
    if (cur) { box.innerHTML = rpReport(cur, rpIsMonth(cur) ? rpMonths() : rpList()); return; }
    if (state.rp.open) { state.rp = { open: "", cat: "all", doc: false, kind }; rpSave(); }
    let html = "", month = "";
    all.forEach((r) => {
      const a = parseDate(r.start), b = parseDate(r.end);
      if (!a || !b) return;
      const m = kind === "months" ? String(b.getFullYear()) : MONTHS[b.getMonth()] + " " + b.getFullYear();
      if (m !== month) { month = m; html += '<div class="rp-month">' + esc(m) + '</div>'; }
      const pending = r.pushed === false ? '<span class="rp-pending" title="' + esc(tl("Отчёт ещё не отправлен на GitHub")) + '">' + esc(tl("не отправлен")) + '</span>' : "";
      const D = r.data;
      html += '<button type="button" class="rp-row" data-rp="open:' + esc(r.file) + '"><span class="rp-week">' + esc(rpWeek(r)) + '</span>' +
        (D && typeof D.rating === "number" ? '<span class="rp-score">' + esc(rpNum(D.rating)) + ' / 10</span>' : "") + pending +
        '<span class="rp-go">' + esc(tl("Открыть")) + ' →</span>' + (D && D.summary ? '<span class="rp-sum">' + mdInline(rpT(D.summary)) + '</span>' : "") + '</button>';
    });
    const note = R.error === "no_dir" ? '<div class="empty">' + esc(tl("Папка отчётов не найдена")) + ': ' + esc(R.dir) + '</div>'
      : R.error === "no_git" ? '<p class="rs-note">' + esc(tl("Не удалось проверить GitHub — пометки «не отправлен» сейчас нет")) + '</p>' : "";
    const tabs = '<div class="rp-cats" role="group" aria-label="' + esc(tl("Отчёты")) + '">' + ["weeks", "months"].map((k) =>
      '<button type="button" class="rp-cat' + (kind === k ? " on" : "") + '" data-rp="kind:' + k + '" aria-pressed="' + (kind === k) + '"><span>' +
      esc(tl(k === "weeks" ? "Недели" : "Месяцы")) + ' · ' + rpKindList(k).length + '</span></button>').join("") + '</div>';
    const empty = kind === "months"
      ? '<div class="empty">' + esc(tl("Месячных отчётов пока нет — штаб кладёт их в папку reports/monthly")) + '</div>'
      : (R.error === "no_dir" ? "" : '<div class="empty">' + esc(tl("Отчётов пока нет — штаб кладёт их в папку reports/weekly")) + '</div>');
    box.innerHTML = '<div class="card"><h2>' + esc(tl("Отчёты")) + '</h2><p class="sub">' +
      esc(tl(kind === "months" ? "Месячные отчёты штаба · нажмите на месяц, чтобы открыть отчёт" : "Недельные отчёты штаба · нажмите на неделю, чтобы открыть отчёт")) + '</p>' +
      tabs + (kind === "weeks" ? note : "") + (all.length ? html : empty) + '</div>';
  }

