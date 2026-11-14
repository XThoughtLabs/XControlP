"use strict";
  // ---------------------------------------------------------------- Отдел «Исследования»
  // Записи — research.json в папке research рядом с Пультом; программа кладёт их вместе с текстами в data.js.
  // Текст показывается на языке Пульта (нет перевода — оригинал); исходные документы — на языке оригинала.
  const RS_LANG = { ru: "Русский", en: "English", he: "עברית" };
  const rsList = () => (board && board.research && board.research.entries) || [];
  const rsPick = (o, lang) => (o && typeof o === "object") ? (o[lang || LANG] || o[LANG] || o.en || o.ru || Object.values(o)[0] || "") : "";
  const rsFor = (id) => rsList().filter((r) => (r.services || []).includes(id));
  const rsKind = (r) => tl(r.kind === "market" ? "Исследование рынка" : "Исследование");
  state.rs = (function () {
    try { const v = JSON.parse(sessionStorage.getItem("pult-rs") || "null"); if (v && typeof v === "object") return v; } catch (err) { /* без хранилища */ }
    return { open: "", doc: "", lang: "" };
  })();
  function rsSave() { try { sessionStorage.setItem("pult-rs", JSON.stringify(state.rs)); } catch (err) { /* без хранилища */ } }
  function rsAction(v) {
    const [cmd, ...rest] = String(v || "").split(":"), arg = rest.join(":");
    if (cmd === "open") state.rs = { open: arg, doc: "", lang: "" };
    else if (cmd === "list") state.rs = { open: "", doc: "", lang: "" };
    else if (cmd === "lang") state.rs = Object.assign({}, state.rs, { doc: "", lang: arg });
    else if (cmd === "src") state.rs = Object.assign({}, state.rs, { doc: arg });
    else return;
    rsSave();
    if (drawer.open) drawer.close();
    if (state.view !== "research") { state.view = "research"; history.replaceState(null, "", "#research"); }
    render();
    window.scrollTo(0, 0);
  }
  // Подраздел в карточке идеи-услуги: «Исследование рынка · дата», название и короткий ответ.
  function rsBox(it) {
    const list = rsFor(it.id);
    if (!list.length) return "";
    return '<div class="inote"><div class="nlabel">' + esc(rsKind(list[0])) + '</div>' + list.map((r) =>
      '<button type="button" class="rs-item" data-rs="open:' + esc(r.id) + '"><b>' + esc(fmt(parseDate(r.date))) + '</b> — ' + esc(rsPick(r.title)) +
      '<div class="rs-ans">' + esc(rsPick(r.answer)) + '</div></button>').join("") + '</div>';
  }
  // Ссылки на услуги записи: открывают карточку идеи.
  function rsServices(r) {
    return (r.services || []).map((id) => {
      const set = board.ideaSets.find((s) => s.items.some((x) => x.id === id));
      return set ? '<button type="button" class="ilink" data-open="idea:' + esc(set.id) + ':' + esc(id) + '">' + esc(id) + '</button>' : esc(id);
    }).join(", ");
  }
  function renderResearch() {
    const box = $("ideas"), all = rsList(), err = board.research && board.research.error;
    const r = state.rs.open ? all.find((x) => x.id === state.rs.open) : null;
    if (!r) {
      const rows = all.map((x) => '<tr class="rs-row" data-rs="open:' + esc(x.id) + '" tabindex="0"><td><span class="idate">' + esc(fmt(parseDate(x.date))) + '</span></td>' +
        '<td><div class="pname">' + esc(rsPick(x.title)) + '</div><div class="pgroup">' + esc(rsKind(x)) + '</div><div class="rs-ans">' + esc(rsPick(x.answer)) + '</div></td>' +
        '<td>' + rsServices(x) + '</td></tr>').join("");
      box.innerHTML = '<div class="card"><h2>' + esc(tl("Исследования")) + '</h2><p class="sub">' +
        esc(tl("Исследования рынка наших услуг и другие исследования штаба · у каждой записи своя дата · новые сверху")) + '</p>' +
        (err ? '<div class="empty">' + esc(err) + '</div>' : "") +
        (all.length ? '<table><colgroup><col class="c-date"><col><col class="c-istatus"></colgroup><thead><tr><th>' + esc(tl("Дата")) + '</th><th>' + esc(tl("Исследование")) +
          '</th><th>' + esc(tl("Услуги")) + '</th></tr></thead><tbody>' + rows + '</tbody></table>'
          : '<div class="empty">' + esc(tl("Исследований пока нет — записи добавляет штаб в папку «research» рядом с Пультом")) + '</div>') + '</div>';
      return;
    }
    const langs = Object.keys(r.text || {});
    const src = /^\d+$/.test(state.rs.doc) ? (r.sources || [])[+state.rs.doc] : null;
    const lang = src ? (src.lang || r.original) : (langs.includes(state.rs.lang) ? state.rs.lang : langs.includes(LANG) ? LANG : (langs.includes(r.original) ? r.original : langs[0]));
    const text = src ? src.text : (r.text || {})[lang];
    const langBtns = langs.map((l) => '<button type="button" class="svc-btn' + (!src && l === lang ? " on" : "") + '" lang="' + l + '" data-rs="lang:' + l + '">' + esc(RS_LANG[l] || l) +
      ' · ' + esc(tl(l === r.original ? "оригинал" : "перевод")) + '</button>').join("");
    const srcBtns = (r.sources || []).map((x, i) => '<button type="button" class="svc-btn' + (src === x ? " on" : "") + '" data-rs="src:' + i + '">' + esc(rsPick(x.name)) +
      ' · ' + esc(RS_LANG[x.lang] || x.lang) + '</button>').join("");
    box.innerHTML = '<div class="card"><div class="rs-bar"><button type="button" class="svc-btn" data-rs="list">‹ ' + esc(tl("Все исследования")) + '</button>' +
      (src ? '<button type="button" class="svc-btn" data-rs="lang:' + esc(state.rs.lang) + '">‹ ' + esc(tl("К общему исследованию")) + '</button>' : "") + '</div>' +
      '<h2>' + esc(rsPick(r.title)) + '</h2><div class="rs-meta">' + esc(rsKind(r)) + ' · ' + esc(fmt(parseDate(r.date))) + (r.version ? ' · ' + esc(tl("Версия")) + ' ' + esc(r.version) : "") +
      ((r.services || []).length ? ' · ' + esc(tl("Услуги")) + ': ' + rsServices(r) : "") + '</div>' +
      '<div class="rs-ans">' + esc(rsPick(r.answer)) + '</div>' +
      (langs.length ? '<div class="rs-bar"><span class="svc-note">' + esc(tl("Языки")) + ':</span>' + langBtns + '</div>' : "") +
      (srcBtns ? '<div class="rs-bar"><span class="svc-note">' + esc(tl("Исходные документы")) + ':</span>' + srcBtns + '</div>' : "") +
      (src ? '<p class="rs-note">' + esc(tl("Исходный документ на языке оригинала")) + '</p>' : "") +
      (text ? '<article class="rs-doc" lang="' + esc(lang) + '" dir="' + (lang === "he" ? "rtl" : "ltr") + '">' + mdHtml(text) + '</article>'
        : '<div class="empty">' + esc(tl("Текст не найден в папке research")) + '</div>') + '</div>';
  }
  // Простой показ Markdown: заголовки, абзацы, списки с вложением, таблицы, цитаты, код, **жирный**, *курсив*, `код`, ссылки, <br> в таблицах.
  function mdInline(raw) {
    return String(raw).split("`").map((part, k) => {
      const e = esc(part);
      if (k % 2) return "<code>" + e + "</code>";
      return e.replace(/&lt;br\s*\/?&gt;/g, "<br>")
        .replace(/\*\*([^*]+?)\*\*/g, "<b>$1</b>")
        .replace(/(^|[\s(«"])\*([^*\s][^*]*?)\*(?=[\s).,;:!?»"]|$)/g, "$1<i>$2</i>")
        .replace(/https?:\/\/[^\s<>"]+/g, (u) => {
          const t = /[.,;:)]+$/.exec(u), url = t ? u.slice(0, -t[0].length) : u;
          return '<a href="' + url + '" target="_blank" rel="noopener">' + url + '</a>' + (t ? t[0] : "");
        });
    }).join("");
  }
  function mdTable(rows) {
    const cells = (x) => x.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
    const sep = rows.length > 1 && /^[\s|:-]+$/.test(rows[1]);
    const head = sep ? cells(rows[0]) : null, body = (sep ? rows.slice(2) : rows).map(cells);
    return '<div class="rs-table"><table>' + (head ? "<thead><tr>" + head.map((c) => "<th>" + mdInline(c) + "</th>").join("") + "</tr></thead>" : "") +
      "<tbody>" + body.map((x) => "<tr>" + x.map((c) => "<td>" + mdInline(c) + "</td>").join("") + "</tr>").join("") + "</tbody></table></div>";
  }
  const MD_ITEM = /^(\s*)([-*•]|\d+[.)])\s+(.*)$/;
  function mdList(block) {
    const items = [];
    block.forEach((l) => {
      const m = MD_ITEM.exec(l);
      if (m) items.push({ ind: m[1].length, ol: /\d/.test(m[2]), text: m[3] });
      else if (items.length) items[items.length - 1].text += " " + l.trim();
    });
    let out = "";
    const stack = [];
    items.forEach((it) => {
      while (stack.length && it.ind < stack[stack.length - 1].ind) out += "</li></" + stack.pop().tag + ">";
      const top = stack[stack.length - 1];
      if (!top || it.ind > top.ind) { const tag = it.ol ? "ol" : "ul"; stack.push({ ind: it.ind, tag }); out += "<" + tag + ">"; }
      else out += "</li>";
      out += "<li>" + mdInline(it.text);
    });
    while (stack.length) out += "</li></" + stack.pop().tag + ">";
    return out;
  }
  function mdHtml(src) {
    const lines = String(src || "").replace(/\r/g, "").split("\n");
    let out = "", i = 0, para = [];
    const flush = () => { if (para.length) { out += "<p>" + mdInline(para.join(" ")) + "</p>"; para = []; } };
    while (i < lines.length) {
      const line = lines[i];
      let m;
      if (!line.trim()) { flush(); i++; continue; }
      if (/^\s*```/.test(line)) {
        flush(); const code = []; i++;
        while (i < lines.length && !/^\s*```/.test(lines[i])) code.push(lines[i++]);
        i++; out += "<pre><code>" + esc(code.join("\n")) + "</code></pre>"; continue;
      }
      if ((m = /^(#{1,6})\s+(.*)$/.exec(line))) { flush(); const n = Math.min(m[1].length + 1, 6); out += "<h" + n + ">" + mdInline(m[2]) + "</h" + n + ">"; i++; continue; }
      if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { flush(); out += "<hr>"; i++; continue; }
      if (/^\s*\|/.test(line)) { flush(); const rows = []; while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++]); out += mdTable(rows); continue; }
      if (/^\s*>/.test(line)) { flush(); const q = []; while (i < lines.length && /^\s*>/.test(lines[i])) q.push(lines[i++].replace(/^\s*>\s?/, "")); out += "<blockquote>" + mdHtml(q.join("\n")) + "</blockquote>"; continue; }
      if (MD_ITEM.test(line)) {
        flush(); const block = [];
        while (i < lines.length && (MD_ITEM.test(lines[i]) || (block.length && /^\s{2,}\S/.test(lines[i])))) block.push(lines[i++]);
        out += mdList(block); continue;
      }
      para.push(line.trim()); i++;
    }
    flush();
    return out;
  }

  function renderStats() {
    const box = $("stats");
    if (!box || state.view !== "stats") return;
    const S = state.st, now = stPeriod(S.kind, today()), cur = stPeriod(S.kind, S.anchor || today());
    const K = stCompare(cur), M = stMetrics(cur.start, K.cutCur), Mp = stMetrics(K.prev.start, K.cutPrev);
    const isNow = cur.start.getTime() === now.start.getTime();
    const cmp = K.partial ? ST_PREV_PART[cur.kind] : ST_PREV[cur.kind];
    const prevName = tl("Прошлый период") + " (" + K.prev.label + ")";
    const server = dpServer();
    const bar = '<div class="cal-bar st-bar"><div class="cal-seg" role="group" aria-label="' + esc(tl("Период")) + '">' +
      ST_KINDS.map((k) => '<button type="button" data-st="kind:' + k + '" class="' + (k === cur.kind ? "active" : "") + '" aria-pressed="' + (k === cur.kind) + '">' + ST_NAME[k] + '</button>').join("") + '</div>' +
      '<button type="button" class="cal-btn" data-st="prev" aria-label="' + esc(tl("Предыдущий период")) + '">‹</button>' +
      '<button type="button" class="cal-btn" data-st="now"' + (isNow ? " disabled" : "") + '>' + esc(tl("Сейчас")) + '</button>' +
      '<button type="button" class="cal-btn" data-st="next" aria-label="' + esc(tl("Следующий период")) + '"' + (isNow ? " disabled" : "") + '>›</button>' +
      '<span class="cal-label">' + esc(cur.label) + '</span>' +
      '<span class="cal-note">' + esc(tl("Сравнение") + ": " + K.prev.label + (K.partial ? " · " + fmtShort(K.prev.start) + "–" + fmtShort(addDays(K.cutPrev, -1)) : "")) + '</span></div>';

    // плитки
    const tile = (label, value, note, delta) => '<div class="card tile"><div class="text"><div class="tlabel">' + esc(label) + '</div><div class="value">' + value + '</div>' +
      '<div class="note">' + note + '</div><div class="note st-cmp">' + (delta ? delta + ' <span>' + esc(cmp) + '</span>' : '<span>' + esc(tl("сравнить не с чем")) + '</span>') + '</div></div></div>';
    const P = M.plan, Pp = Mp.plan, todayKey = dayKey(today()), todayRow = P.rows.find((d) => d.day === todayKey);
    const planNote = !server ? esc(tl("План дня виден, когда Пульт открыт ярлыком «XControlP» на рабочем столе")) :
      P.total + " " + plural(P.total, "задача", "задачи", "задач") + " · " + esc(tl("сделано")) + " " + P.done + ", " + esc(tl("частично")) + " " + P.partial + ", " +
      esc(tl("не сделано")) + " " + P.not_done + (P.open ? " · " + esc(tl("открыто")) + " " + P.open : "") + (todayRow && !todayRow.closed && P.open ? " · " + esc(tl("сегодня ещё идёт")) : "");
    const best = Object.keys(M.commitDays).sort((x, y) => M.commitDays[y] - M.commitDays[x] || (x < y ? -1 : 1))[0];
    const activeRepos = M.repos.filter((r) => r.n > 0).length;
    const tiles = [
      tile(tl("План дня"), P.percent == null ? "—" : P.percent + "%", planNote, stDelta(P.percent, Pp.percent, ST_PP)),
      tile(tl("Оценка дней"), P.rating == null ? "—" : num1(P.rating), esc(tl("дней с оценкой")) + ": " + P.ratings.length + " · " + esc(tl("дней с планом")) + ": " + P.days,
        stDelta(P.rating, Pp.rating, "", true)),
      tile(tl("Уроки"), M.commitsKnown ? M.lessonCount : "—", esc(tl("курсов")) + ": " + Object.keys(M.lessons).length + " · " + esc(tl("блоков пройдено")) + ": " + M.blocks.length,
        M.commitsKnown ? stDelta(M.lessonCount, Mp.lessonCount) : stDelta(null, null)),
      tile(tl("Проекты в движении"), M.active.length, esc(tl("записей в истории")) + ": " + M.events.length + " · " + esc(tl("стояли")) + ": " + M.stood.length,
        stDelta(M.active.length, Mp.active.length)),
      tile(tl("Новые идеи"), M.ideasNewCount, esc(tl("сделано идей")) + ": " + M.ideasDone.length, stDelta(M.ideasNewCount, Mp.ideasNewCount)),
      tile(tl("Коммиты"), M.commitsKnown ? M.commits : "—", M.commitsKnown ? esc(tl("репозиториев")) + ": " + activeRepos +
        (best ? " · " + esc(tl("больше всего")) + " " + fmtShort(parseDate(best)) + " (" + M.commitDays[best] + ")" : "") : esc(tl("появятся после синхронизации данных")),
        M.commitsKnown ? stDelta(M.commits, Mp.commits) : stDelta(null, null))
    ];

    // строки по дням (неделя, месяц) / неделям (квартал) / месяцам (год)
    const buckets = stBuckets(cur), last = dayKey(today());
    const rows = buckets.map((b) => {
      const A = dayKey(b.start), B = dayKey(addDays(b.end, -1)), r = { b, A, future: A > last, total: 0, done: 0, partial: 0, not_done: 0, open: 0, score: 0, ratings: [], lessons: 0, commits: 0, repos: {} };
      P.rows.forEach((d) => { if (d.day >= A && d.day <= B) { const c = d.counts || {};
        r.total += d.total || 0; r.done += c.done || 0; r.partial += c.partial || 0; r.not_done += c.not_done || 0; r.open += (c.planned || 0) + (c.active || 0); r.score += d.score || 0;
        if (d.rating != null) r.ratings.push(d.rating); } });
      Object.keys(M.lessonDays).forEach((k) => { if (k >= A && k <= B) r.lessons += M.lessonDays[k]; });
      M.repos.forEach((x) => Object.keys(x.days).forEach((k) => { if (k >= A && k <= B && k >= M.A && k <= M.B) { const v = +x.days[k] || 0; r.commits += v; r.repos[x.name] = (r.repos[x.name] || 0) + v; } }));
      return r;
    });
    const avg = (a) => a.length ? num1(a.reduce((x, y) => x + y, 0) / a.length) : "—";
    const dash = (n) => n ? String(n) : '<span class="muted">—</span>';
    const rowHtml = (r, label, cls) => '<tr' + (cls ? ' class="' + cls + '"' : "") + '><td>' + label + '</td><td>' + dash(r.total) + '</td><td>' + dash(r.done) + '</td><td>' + dash(r.partial) +
      '</td><td>' + dash(r.not_done) + '</td><td>' + dash(r.open) + '</td><td>' + (r.total ? Math.round(100 * r.score / r.total) + "%" : '<span class="muted">—</span>') +
      '</td><td>' + (r.ratings.length === 1 ? String(r.ratings[0]) : r.ratings.length ? avg(r.ratings) : '<span class="muted">—</span>') + '</td><td>' + dash(r.lessons) + '</td><td>' + dash(r.commits) + '</td></tr>';
    const sum = rows.filter((r) => !r.future).reduce((t, r) => { ["total", "done", "partial", "not_done", "open", "score", "lessons", "commits"].forEach((k) => { t[k] += r[k]; }); t.ratings = t.ratings.concat(r.ratings); return t; },
      { total: 0, done: 0, partial: 0, not_done: 0, open: 0, score: 0, ratings: [], lessons: 0, commits: 0 });
    const first = cur.kind === "quarter" ? tl("Неделя") : cur.kind === "year" ? tl("Месяц") : tl("День");
    const dayTable = '<table class="numtab st-tab"><thead><tr><th>' + esc(first) + '</th><th>' + esc(tl("Задач")) + '</th><th>' + esc(tl("Сделано")) + '</th><th>' + esc(tl("Частично")) +
      '</th><th>' + esc(tl("Не сделано")) + '</th><th>' + esc(tl("Открыто")) + '</th><th>' + esc(tl("Выполнение")) + '</th><th>' + esc(tl("Оценка")) + '</th><th>' + esc(tl("Уроков")) +
      '</th><th>' + esc(tl("Коммитов")) + '</th></tr></thead><tbody>' + rows.filter((r) => !r.future).map((r) => rowHtml(r, esc(r.b.row || r.b.label))).join("") +
      rowHtml(sum, esc(tl("Итого")), "total") + '</tbody></table>';

    // учёба
    const study = board.projects.filter((p) => p.group === STUDY && (p.status === "work" || (M.lessons[p.id] || []).length));
    const blocksOf = (pid) => M.blocks.filter((h) => h.project === pid).length;
    const studyCard = '<div class="card"><h2>' + esc(tl("Учёба")) + '</h2><p class="sub">' + esc(tl("Уроки за период по курсам · урок считается в день первого коммита с его кодом или по файлу продвижения курса")) + '</p>' +
      (study.length ? '<table class="numtab st-tab"><colgroup><col><col class="c-n"><col><col class="c-n"></colgroup><thead><tr><th>' + esc(tl("Курс")) + '</th><th>' + esc(tl("Уроков")) +
        '</th><th class="txt">' + esc(tl("Какие")) + '</th><th>' + esc(tl("Блоков")) + '</th></tr></thead><tbody>' +
        study.map((p) => { const ls = M.lessons[p.id] || [], was = (Mp.lessons[p.id] || []).length;
          return '<tr data-open="' + esc(p.id) + '" tabindex="0" aria-label="' + esc(tl("Все этапы: ") + p.name) + '"><td><div class="pname">' + esc(p.name) + '</div><div class="pgroup">' + esc(p.stages[p.current] || "—") + '</div></td>' +
            '<td data-tip="' + esc('<div class="t">' + esc(p.name) + '</div><div class="l">' + esc(prevName) + ": " + was + '</div>') + '">' + dash(ls.length) + '</td>' +
            '<td class="txt"><span class="st-codes">' + (ls.length ? esc(ls.join(", ")) : '<span class="muted">—</span>') + '</span></td><td>' + dash(blocksOf(p.id)) + '</td></tr>'; }).join("") +
        '<tr class="total"><td>' + esc(tl("Итого")) + '</td><td>' + M.lessonCount + '</td><td></td><td>' + M.blocks.length + '</td></tr></tbody></table>'
        : '<div class="empty">' + esc(tl("Нет курсов в работе")) + '</div>') + '</div>';

    // движение проектов
    const act = M.active.slice().sort((x, y) => (y.events.length + y.lessons + y.commits) - (x.events.length + x.lessons + x.commits) || (x.p.name < y.p.name ? -1 : 1));
    const projCard = '<div class="card"><h2>' + esc(tl("Движение проектов")) + '</h2><p class="sub">' + esc(tl("Записи истории Пульта, уроки и коммиты своего репозитория за период · нажмите на проект — откроются все этапы")) + '</p>' +
      (act.length ? '<table class="numtab st-tab"><colgroup><col><col class="c-n"><col class="c-n"><col class="c-n"></colgroup><thead><tr><th>' + esc(tl("Проект")) + '</th><th>' + esc(tl("Записей")) + '</th><th>' + esc(tl("Уроков")) + '</th><th>' + esc(tl("Коммитов")) + '</th></tr></thead><tbody>' +
        act.map((x) => { const lastEv = x.events.slice().sort((a, b) => b.date - a.date)[0];
          const own = x.events.length + x.lessons + x.commits, with_ = board.projects.filter((c) => x.p.movesWith.includes(c.id) && M.active.some((y) => y.p === c));
          return '<tr data-open="' + esc(x.p.id) + '" tabindex="0" aria-label="' + esc(tl("Все этапы: ") + x.p.name) + '"><td><div class="pname">' + esc(x.p.name) + '</div><div class="pgroup">' +
            esc(lastEv ? fmtShort(lastEv.date) + " · " + lastEv.text : !own && with_.length ? tl("движется вместе с") + ": " + with_.map((c) => c.name).join(", ") : (x.p.stages[x.p.current] || "—")) + '</div></td><td>' + dash(x.events.length) + '</td><td>' + dash(x.lessons) + '</td><td>' + dash(x.commits) + '</td></tr>'; }).join("") +
        '</tbody></table>' : '<div class="empty">' + esc(tl("За период движения не было")) + '</div>') +
      '<div class="st-stood"><b>' + esc(tl("Стояли")) + ':</b> ' + (M.stood.length ? M.stood.map((p) => esc(p.name)).join(", ") : esc(tl("никто — все проекты в работе двигались"))) +
      ' <span class="muted">' + esc(tl("(в работе, но за период ни записи, ни урока, ни коммита)")) + '</span></div></div>';

    // идеи
    const ideaName = (t) => { const set = board.ideaSets.find((s) => s.id === t.set), it = set && set.items.find((x) => x.id === t.id); return it ? { it, set } : null; };
    const done = M.ideasDone.map(ideaName).filter(Boolean);
    const ideasCard = '<div class="card"><h2>' + esc(tl("Идеи")) + '</h2><p class="sub">' + esc(tl("Новые — по дате идеи; сделанные — переход в «Сделано» по журналу общей базы идей")) + '</p>' +
      (board.ideaSets.length ? '<table class="numtab st-tab"><thead><tr><th>' + esc(tl("Отдел")) + '</th><th>' + esc(tl("Новых")) + '</th><th>' + esc(tl("Сделано")) + '</th></tr></thead><tbody>' +
        M.ideasNew.map((x) => '<tr><td>' + esc(x.set.title) + '</td><td>' + dash(x.items.length) + '</td><td>' + dash(M.ideasDone.filter((t) => t.set === x.set.id).length) + '</td></tr>').join("") +
        '<tr class="total"><td>' + esc(tl("Итого")) + '</td><td>' + M.ideasNewCount + '</td><td>' + M.ideasDone.length + '</td></tr></tbody></table>' +
        (done.length ? '<h3 class="mini-h">' + esc(tl("Сделаны за период")) + '</h3><table><colgroup><col class="c-id"><col></colgroup><tbody>' +
          done.map((x) => '<tr data-open="idea:' + esc(x.set.id) + ':' + esc(x.it.id) + '" tabindex="0"><td><span class="iid">' + esc(x.it.id) + '</span></td><td><div class="pname ititle">' + esc(x.it.title) + '</div><div class="pgroup">' + esc(x.set.title) + '</div></td></tr>').join("") +
          '</tbody></table>' : "") : '<div class="empty">' + esc(tl("Идей нет")) + '</div>') + '</div>';

    // откуда цифры
    const st = board.stats, errs = st && st.commits && Array.isArray(st.commits.errors) ? st.commits.errors : [];
    const srcCard = '<div class="card"><h2>' + esc(tl("Откуда цифры")) + '</h2><ul class="st-src">' +
      '<li>' + esc(tl("План дня — из базы плана дня, как во вкладке «Итоги дней»: выполнение — сделано и половина частичных из всех задач, кроме убранных.")) + (server ? "" : " <b>" + esc(tl("Сейчас недоступно: Пульт открыт не ярлыком.")) + "</b>") + '</li>' +
      '<li>' + (st && st.synced ? esc(tl("Уроки и коммиты — сборщик (кнопка «Синхронизировать данные»), последний раз")) + " " + esc(stamp(st.synced)) + "."
        : "<b>" + esc(tl("Уроки и коммиты — сборщик (кнопка «Синхронизировать данные»): ещё не собирались.")) + "</b>") + '</li>' +
      '<li>' + esc(tl("Коммиты — все git-репозитории папки, где лежат репозитории проектов; только число по дням, без текстов; один коммит в двух копиях считается один раз.")) + '</li>' +
      '<li>' + esc(tl("Движение проектов — история Пульта; идеи — общая база идей.")) + '</li>' +
      '<li>' + esc(tl("Неделя — с воскресенья. Пока период идёт, сравнение — с теми же первыми днями прошлого периода.")) + '</li>' +
      errs.map((e) => '<li class="muted">' + esc(e) + '</li>').join("") + '</ul></div>';

    // квартал — по неделям, год — по месяцам
    const byName = cur.kind === "quarter" ? "По неделям" : cur.kind === "year" ? "По месяцам" : "По дням";
    box.innerHTML = bar + '<div class="tiles">' + tiles.join("") + '</div>' +
      '<div class="cols2"><div class="card"><h2>' + esc(tl(ST_CHART_NAME[cur.kind] || "Коммиты по дням")) + '</h2><p class="sub" id="st-chart-sub"></p><div class="st-chart" id="st-chart"></div></div>' +
      '<div class="card"><h2>' + esc(tl("Коммиты по репозиториям")) + '</h2><p class="sub">' + esc(tl("За период · наведите на строку — сколько было в прошлом периоде")) + '</p><div id="st-repos"></div></div></div>' +
      '<div class="card"><h2>' + esc(tl(byName)) + '</h2><p class="sub">' + esc(tl("План дня, оценка, уроки и коммиты · строка «Итого» — весь период до сегодняшнего дня")) + '</p>' + dayTable + '</div>' +
      '<div class="cols2">' + studyCard + projCard + '</div><div class="cols2">' + ideasCard + srcCard + '</div>';
    stDrawChart(M, rows);
    stDrawRepos(M, Mp, prevName);
  }

  function stDrawChart(M, rows) {
    const el = $("st-chart"), sub = $("st-chart-sub");
    if (!el) return;
    if (!M.commitsKnown) { el.innerHTML = '<div class="empty">' + esc(tl("Коммиты появятся после синхронизации данных: кнопка «Синхронизировать данные» вверху справа")) + '</div>'; return; }
    const n = rows.length, max = Math.max(1, ...rows.map((r) => r.commits));
    const nice = (v) => { const p = Math.pow(10, Math.floor(Math.log10(v))), f = v / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; };
    const step = max <= 4 ? 1 : nice(max / 4), top = Math.ceil(max / step) * step;
    const W = Math.max(320, Math.round(el.clientWidth || 640)), H = 220, L = 34, R = 8, T = 16, B = 26, pw = W - L - R, ph = H - T - B;
    const slot = pw / n, bw = Math.min(28, Math.max(3, slot * 0.62)), y = (v) => T + ph - v / top * ph;
    let svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '" role="img" aria-label="' +
      esc(tl(ST_CHART_NAME[state.st.kind] || "Коммиты по дням") + ": " + rows.filter((r) => !r.future).map((r) => r.b.short + " " + r.commits).join(", ")) + '">';
    for (let v = 0; v <= top; v += step)
      svg += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="' + (v === 0 ? "var(--axis)" : "var(--grid)") + '" stroke-width="1"/>' +
        '<text class="axis-text" x="' + (L - 6) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + v + '</text>';
    const labelAll = n <= 12, maxI = rows.findIndex((r) => r.commits === max && !r.future);
    rows.forEach((r, i) => {
      const x0 = L + i * slot + (slot - bw) / 2, x1 = x0 + bw, v = r.commits;
      if (v && !r.future) {
        const h = Math.max(2, v / top * ph), rr = Math.min(4, bw / 2, h), y1 = y(0), y0 = y1 - h;
        svg += '<path fill="var(--series-1)" d="M' + x0 + ' ' + y1 + 'V' + (y0 + rr) + 'Q' + x0 + ' ' + y0 + ' ' + (x0 + rr) + ' ' + y0 + 'H' + (x1 - rr) + 'Q' + x1 + ' ' + y0 + ' ' + x1 + ' ' + (y0 + rr) + 'V' + y1 + 'Z"/>';
        if (labelAll || i === maxI) svg += '<text class="axis-text st-val" x="' + (x0 + bw / 2) + '" y="' + (y0 - 4) + '" text-anchor="middle">' + v + '</text>';
      }
      if (labelAll || i % 5 === 0 || i === n - 1)
        svg += '<text class="axis-text" x="' + (L + i * slot + slot / 2) + '" y="' + (H - 8) + '" text-anchor="middle">' + esc(r.b.short) + '</text>';
      const top5 = Object.keys(r.repos).filter((k) => r.repos[k]).sort((a, b) => r.repos[b] - r.repos[a]).slice(0, 6);
      const lines = r.future ? '<div class="l">' + esc(tl("ещё впереди")) + '</div>' : top5.map((k) => '<div class="l"><bdi>' + esc(k) + '</bdi>: ' + r.repos[k] + '</div>').join("") || '<div class="l">' + esc(tl("Коммитов не было")) + '</div>';
      svg += '<rect x="' + (L + i * slot) + '" y="' + T + '" width="' + slot + '" height="' + ph + '" fill="transparent" tabindex="0" data-tip="' +
        esc('<div class="t">' + esc(r.b.label) + (r.future ? "" : ' · ' + v + ' ' + esc(plural(v, "коммит", "коммита", "коммитов"))) + '</div>' + lines) + '"/>';
    });
    el.innerHTML = svg + '</svg>';
    if (sub) sub.textContent = tl("Все репозитории вместе · наведите на столбец — по каким репозиториям");
  }

  function stDrawRepos(M, Mp, prevName) {
    const el = $("st-repos");
    if (!el) return;
    if (!M.commitsKnown) { el.innerHTML = '<div class="empty">' + esc(tl("Коммиты появятся после синхронизации данных: кнопка «Синхронизировать данные» вверху справа")) + '</div>'; return; }
    const was = {};
    Mp.repos.forEach((r) => { was[r.name] = r.n; });
    const list = M.repos.filter((r) => r.n > 0).sort((a, b) => b.n - a.n || (a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1));
    const quiet = M.repos.length - list.length, max = Math.max(1, ...list.map((r) => r.n));
    el.innerHTML = list.length ? '<div class="bars">' + list.map((r) => {
      const p = r.project && board.projects.find((x) => x.id === r.project);
      return '<div class="bar-row" tabindex="0" data-tip="' + esc('<div class="t"><bdi>' + esc(r.name) + '</bdi></div>' + (p ? '<div class="l">' + esc(tl("Проект")) + ': ' + esc(p.name) + '</div>' : "") +
        '<div class="l">' + esc(tl("За период")) + ': ' + r.n + '</div><div class="l">' + esc(prevName) + ': ' + (was[r.name] || 0) + '</div>') + '">' +
        '<div class="bname"><bdi>' + esc(r.name) + '</bdi></div><div class="track"><div class="fill" style="width:' + (r.n / max * 100).toFixed(1) + '%"></div></div><div class="bval">' + r.n + '</div></div>'; }).join("") + '</div>' +
      (quiet ? '<p class="sub st-quiet">' + esc(tl("Без коммитов за период")) + ': ' + quiet + ' ' + esc(plural(quiet, "репозиторий", "репозитория", "репозиториев")) + '</p>' : "")
      : '<div class="empty">' + esc(tl("Коммитов за период не было")) + '</div>';
  }

  function stAction(a) {
    const S = state.st, [cmd, arg] = a.split(":"), cur = stPeriod(S.kind, S.anchor || today());
    if (cmd === "kind" && ST_KINDS.includes(arg)) { S.kind = arg; S.anchor = S.anchor ? cur.start : null; }
    else if (cmd === "prev") S.anchor = addDays(cur.start, -1);
    else if (cmd === "next") { S.anchor = cur.end; if (stPeriod(S.kind, S.anchor).start > today()) S.anchor = null; }
    else if (cmd === "now") S.anchor = null;
    if (S.anchor && stPeriod(S.kind, S.anchor).start.getTime() === stPeriod(S.kind, today()).start.getTime()) S.anchor = null;
    renderStats();
  }

  // Переключатель языков и статичная разметка окна (заголовки, кнопки сверху).
  function renderLangs() {
    const box = $("langs");
    if (!box) return;
    const code = { ru: "RU", en: "EN", he: "עב" }[LANG] || LANG.toUpperCase();
    box.innerHTML = '<button type="button" class="set-open" data-set="open" aria-haspopup="dialog" title="' + esc(tl("Настройки")) + '" aria-label="' + esc(tl("Настройки")) + '">☰</button>' +
      '<button type="button" class="lang-code" data-set="open:langs" aria-haspopup="dialog" lang="' + LANG + '" title="' + esc(tl("Язык") + ": " + LANGS[LANG]) +
      '" aria-label="' + esc(tl("Язык") + ": " + LANGS[LANG]) + '">' + esc(code) + '</button>';
  }
  async function setLang(code) {
    if (!LANGS[code] || code === LANG) return;
    try { localStorage.setItem("pult-lang", code); } catch (err) { /* без хранилища — только через программу */ }
    if (token) {
      try { await fetch("/settings?lang=" + code, { method: "POST", headers: { "X-Pult-Token": token } }); } catch (err) { /* окно перечитает как есть */ }
    }
    location.reload();
  }
