"use strict";
  // ---------------------------------------------------------------- общий уровень производительности
  function perfScore() {
    const work = board.projects.filter((p) => p.group !== DEV && p.status === "work");
    const moving = work.filter((p) => p.days != null && p.days <= 14);
    const ideas = board.ideaSets.flatMap((set) => set.items), c = outcomeCounts(ideas), n = ideas.length;
    const real = c.done + c.road, base = n - c.dropped;
    const parts = {
      move: { name: tl("Движение проектов"), value: work.length ? pct(moving.length, work.length) : null,
        text: moving.length + tl(" из ") + work.length + tl(" проектов в работе сдвигались за 14 дней") },
      real: { name: tl("Реализация идей"), value: base ? pct(real, base) : null,
        text: real + tl(" из ") + base + tl(" идей (кроме отказов) воплощены или в проекте") },
      sorted: { name: tl("Разобранность идей"), value: n ? pct(n - c.idea, n) : null,
        text: (n - c.idea) + tl(" из ") + n + tl(" идей уже не на полке: проверяются, ждут, отложены на будущее, в проекте, сделаны или отклонены") }
    };
    let sum = 0, w = 0;
    for (const k in PERF_WEIGHTS) if (parts[k].value != null) { sum += parts[k].value * PERF_WEIGHTS[k]; w += PERF_WEIGHTS[k]; }
    return { total: w ? Math.round(sum / w) : 0, parts, work, c, n };
  }
  function paceStats() {
    const ids = new Set(board.projects.filter((p) => p.group !== DEV).map((p) => p.id));
    const ev = board.history.filter((h) => ids.has(h.project));
    const t0 = today().getTime();
    const between = (fromDays, toDays) => ev.filter((h) => { const d = Math.round((t0 - h.date.getTime()) / DAY); return d >= fromDays && d <= toDays; });
    const weeks = Array.from({ length: 8 }, (_, i) => { const end = new Date(t0 - i * 7 * DAY), start = new Date(t0 - (i * 7 + 6) * DAY);
      return { start, end, items: between(i * 7, i * 7 + 6) }; }).reverse();
    return { d7: between(0, 6).length, d30: between(0, 29).length, prev30: between(30, 59).length, weeks };
  }
  function renderPerf() {
    const box = $("insight"), S = perfScore(), P = paceStats();
    const w = PERF_WEIGHTS, frac = (x) => x === 0.5 ? "½" : x === 0.25 ? "¼" : Math.round(x * 100) + "%";
    const hero = tl('<div class="card"><div class="hero"><div><div class="tlabel">Общий уровень</div><div class="big">') + S.total + '%</div></div>' +
      '<div class="grow"><div class="meter" role="img" aria-label="' + esc(tl("Общий уровень производительности ") + S.total + "%") + '"><span style="width:' + S.total + '%"></span></div>' +
      '<div class="parts">' + Object.keys(w).map((k) => '<span>' + esc(S.parts[k].name) + ': <b>' + (S.parts[k].value == null ? "—" : S.parts[k].value + "%") + '</b></span>').join("") + '</div>' +
      tl('<div class="formula">Как считается: ') + frac(w.move) + tl(' — движение проектов в работе, ') + frac(w.real) + tl(' — реализация идей, ') + frac(w.sorted) +
      tl(' — разобранность идей. Каждая часть — доля от 0 до 100%; формулу можно поменять.</div></div></div></div>');
    const partTile = (k) => { const x = S.parts[k]; return '<div class="card tile">' + ring(x.value || 0, "var(--series-1)", x.name) +
      '<div class="text"><div class="tlabel">' + esc(x.name) + '</div><div class="value">' + (x.value == null ? "—" : x.value + "%") + '</div><div class="note">' + esc(x.text) + '</div></div></div>'; };
    const diff = P.d30 - P.prev30;
    const tiles = [partTile("move"), partTile("real"), partTile("sorted"),
      tl('<div class="card tile"><div class="text"><div class="tlabel">В работе</div><div class="value">') + S.work.length + '</div><div class="note">' + plural(S.work.length, "проект", "проекта", "проектов") + tl(' сейчас</div></div></div>'),
      tl('<div class="card tile"><div class="text"><div class="tlabel">Темп за 30 дней</div><div class="value">') + P.d30 + '</div><div class="note">' + plural(P.d30, "сдвиг", "сдвига", "сдвигов") +
        ' · <span class="trend ' + (diff > 0 ? "up" : diff < 0 ? "down" : "") + '">' + (diff > 0 ? "▲ +" + diff : diff < 0 ? "▼ " + diff : "= ") + tl('</span> к прошлым 30</div></div></div>'),
      tl('<div class="card tile"><div class="text"><div class="tlabel">Идей всего</div><div class="value">') + S.n + tl('</div><div class="note">в проект перешли ') + pct(S.c.done + S.c.road, S.n) + '%</div></div></div>'];
    // Темп по неделям
    const max = Math.max(1, ...P.weeks.map((x) => x.items.length)), maxI = P.weeks.findIndex((x) => x.items.length === max);
    const cols = P.weeks.map((x, i) => { const n = x.items.length, label = fmtShort(x.start) + "–" + fmtShort(x.end);
      const lines = x.items.slice(0, 8).map((h) => '<div class="l">' + esc(nameOf(h.project)) + ': ' + esc(h.text) + '</div>').join("") || tl('<div class="l">Сдвигов не было</div>');
      return '<div class="col" tabindex="0" data-tip="' + esc('<div class="t">' + label + ' · ' + n + ' ' + plural(n, "сдвиг", "сдвига", "сдвигов") + '</div>' + lines) + '">' +
        '<span class="val">' + (n && (i === maxI || i === P.weeks.length - 1) ? n : "") + '</span>' +
        (n ? '<span class="bar" style="height:' + Math.max(3, n / max * 128) + 'px"></span>' : "") + '</div>'; }).join("");
    const labels = P.weeks.map((x, i) => '<span>' + (i === P.weeks.length - 1 ? tl("эта неделя") : fmtShort(x.start)) + '</span>').join("");
    const paceCard = tl('<div class="card"><h2>Темп</h2><p class="sub">Сдвиги этапов по неделям, последние 8 недель · наведите на столбец, чтобы увидеть, что сдвинулось</p>') +
      '<div class="wk" role="img" aria-label="' + esc(tl("Сдвиги по неделям: ") + P.weeks.map((x) => x.items.length).join(", ")) + '">' + cols + '</div><div class="wk-labels">' + labels + '</div>' +
      tl('<div class="pace"><span>За 7 дней: <b>') + P.d7 + tl('</b></span><span>За 30 дней: <b>') + P.d30 + tl('</b></span><span>Прошлые 30 дней: <b>') + P.prev30 + '</b></span>' +
      tl('<span>В среднем в неделю: <b>') + (P.d30 / 30 * 7).toFixed(1).replace(".", ",") + '</b></span></div></div>';
    // Проекты в работе
    const work = S.work.slice().sort((a, b) => (a.days == null ? 1e9 : a.days) - (b.days == null ? 1e9 : b.days));
    const workCard = tl('<div class="card"><h2>Проекты в работе</h2><p class="sub">Сейчас в работе ') + work.length + tl(' · без движения больше 14 дней отмечены</p>') +
      (work.length ? tl('<table><thead><tr><th>Проект</th><th>Сейчас</th><th>Движение</th><th>Прогресс</th></tr></thead><tbody>') + work.map((p) =>
        '<tr data-open="' + esc(p.id) + '" tabindex="0" aria-label="' + esc(tl("Все этапы: ") + p.name) + '"><td><div class="pname">' + esc(p.name) + '</div><div class="pgroup">' + esc(td(p.group)) + '</div></td>' +
        '<td>' + esc(p.stages[p.current] || "—") + '</td><td><span class="idate' + (p.days > 14 ? " stale" : "") + '">' + (p.days == null ? "—" : daysText(p.days)) + '</span></td>' +
        '<td><span class="idate">' + p.percent + '%</span></td></tr>').join("") + '</tbody></table>' : tl('<div class="empty">Сейчас нет проектов в работе</div>')) + '</div>';
    // Идеи: реализуются и нет
    const all = allIdeas(), c = S.c;
    const going = all.filter((x) => x.it.kind === "road" || x.it.kind === "done").sort((a, b) => (b.it.date || 0) - (a.it.date || 0)).slice(0, 5);
    const stuck = all.filter((x) => x.it.kind === "idea").sort((a, b) => (a.it.date || 0) - (b.it.date || 0)).slice(0, 5);
    const list = (items, right) => items.length ? '<table><colgroup><col class="c-id"><col><col class="c-date"></colgroup><tbody>' + items.map((x) => ideaRow(x, right(x))).join("") + '</tbody></table>' : tl('<div class="empty">Нет</div>');
    const ideasCard = tl('<div class="card"><h2>Идеи: реализуются и нет</h2><p class="sub">Все ') + S.n + ' ' + plural(S.n, "идея", "идеи", "идей") + tl(' · <button type="button" class="jump" data-goto="idea-stats">Подробнее — аналитика идей ›</button></p>') +
      outcomeLegend() + tl('<div class="orow"><div class="oname"><b>Все идеи</b></div>') + outcomeBar(c, tl("все идеи")) + '<div class="ototal">' + S.n + '</div></div>' +
      tl('<div class="cols2"><div><h3 class="mini-h">РЕАЛИЗУЮТСЯ · ') + (c.done + c.road) + '</h3>' + list(going, (x) => esc(OUT[x.it.kind].name)) + '</div>' +
      tl('<div><h3 class="mini-h">НЕ РЕАЛИЗУЮТСЯ — НА ПОЛКЕ · ') + c.idea + '</h3>' + list(stuck, (x) => ageText(daysAgo(x.it.date))) + '</div></div></div>';
    box.innerHTML = hero + '<div class="tiles">' + tiles.join("") + '</div>' + '<div class="cols2">' + paceCard + workCard + '</div>' + ideasCard;
  }

  // Номера других идей в тексте (A-17, B-4) — ссылки: нажал — открылась та идея (связи, а не дубли).
  let openIdeaId = "";  // номер идеи в открытой карточке: на саму себя ссылку не ставим
  function linkIds(text) {
    return esc(text).replace(/\b([A-Z]-\d{2,3})\b/g, (whole, id) => {
      const set = id !== openIdeaId && board && board.ideaSets.find((x) => x.items.some((it) => it.id === id));
      return set ? '<button type="button" class="ilink" data-open="idea:' + esc(set.id) + ':' + id + '">' + id + '</button>' : whole;
    });
  }

  function noteHtml(n) {
    // "CEO (29.09): … [штаб] …" — words of the CEO and notes of the staff are shown apart.
    let label = n.label || "", text = String(n.text || ""), cls = "";
    const ceo = /^(CEO\s*\([^)]*\)|CEO):\s*/.exec(text);
    if (!label && ceo) { label = ceo[1]; text = text.slice(ceo[0].length); cls = " ceo"; }
    const parts = text.split("[штаб]");
    let body = parts[0].trim() ? '<div class="ntext">' + linkIds(parts[0].trim()) + '</div>' : "";
    parts.slice(1).forEach((p) => { body += tl('<div class="ntext staff"><b>ШТАБ</b>') + linkIds(p.trim()) + '</div>'; });
    if (/^суть/i.test(label)) cls += " main";
    if (/^ceo/i.test(label) && !cls.includes("ceo")) cls += " ceo";
    const sub = (n.sub || []).length ? '<ul>' + n.sub.map((s) => '<li>' + linkIds(s) + '</li>').join("") + '</ul>' : "";
    return '<div class="inote' + cls + '">' + (label ? '<div class="nlabel">' + esc(n.label && label === n.label && n.labelShown ? n.labelShown : label) + '</div>' : "") + body + sub + '</div>';
  }

  // Кнопки услуги в карточке идеи: флажок (снять / поставить), «Добавить в услуги», «Убрать из услуг» с подтверждением.
  function flagButton(it) {
    const sv = serviceOf(it.id), d = (x) => x ? fmt(parseDate(x)) : "";
    if (!sv) return '<div class="svc-row"><button type="button" class="svc-btn" data-flag="' + esc(it.id) + ':1">⚑ ' + esc(tl("Добавить в услуги")) +
      '</button><span class="svc-note">' + esc(tl("не в услугах")) + '</span></div>';
    const toggle = '<button type="button" class="svc-btn' + (sv.flag ? " on" : "") + '" aria-pressed="' + !!sv.flag + '" data-flag="' + esc(it.id) + ':' + (sv.flag ? "0" : "1") +
      '" title="' + esc(sv.flag ? tl("Снять флажок «Услуга» с этой идеи") : tl("Отметить как нашу платную услугу")) + '">' + (sv.flag ? "⚑ " : "⚐ ") + esc(tl("Услуга")) + '</button>';
    const note = '<span class="svc-note">' + esc(sv.flag ? tl("наша платная услуга · отмечено ") + d(sv.flag_at) : tl("в услугах · флажок снят ") + d(sv.flag_at)) + '</span>';
    const del = svcDelAsk === it.id
      ? '<span class="svc-ask">' + esc(tl("Убрать эту услугу из отдела услуг?")) + '<button type="button" class="svc-btn danger" data-svcdel="yes:' + esc(it.id) + '">' +
        esc(tl("Да, убрать")) + '</button><button type="button" class="svc-btn" data-svcdel="no:' + esc(it.id) + '">' + esc(tl("Нет, оставить")) + '</button></span>'
      : '<button type="button" class="svc-del" data-svcdel="ask:' + esc(it.id) + '">' + esc(tl("Убрать из услуг")) + '</button>';
    return '<div class="svc-row">' + toggle + note + del + '</div>';
  }
  function renderIdeaDrawer(it, set) {
    openIdeaId = it.id;
    // Обратные связи: идеи (в любом подотделе), в тексте которых упоминается эта.
    const mention = new RegExp("\\b" + it.id.replace(/[-]/g, "\\-") + "\\b");
    const refs = [];
    board.ideaSets.forEach((s) => s.items.forEach((x) => {
      if (x !== it && !it.links.includes(x.id) && x.notes.some((n) => mention.test(String(n.text || "") + " " + (n.sub || []).join(" ")))) refs.push({ s, x });
    }));
    const linked = it.links.map((id) => { const s = board.ideaSets.find((z) => z.items.some((x) => x.id === id)); return s ? { s, x: s.items.find((x) => x.id === id) } : null; }).filter(Boolean);
    const linksHtml = linked.length ? tl('<h3>СВЯЗАННЫЕ ИДЕИ · ') + linked.length + '</h3>' + linked.map((r) => ideaLine(r, set)).join("") : "";
    const refsHtml = refs.length ? tl('<h3>УПОМИНАЕТСЯ В</h3>') + refs.map((r) => ideaLine(r, set)).join("") : "";
    const proj = it.project ? board.projects.find((p) => p.id === it.project) : null;
    const projHtml = it.project ? tl('<div class="inote"><div class="nlabel">Проект на Пульте</div><div class="ntext">') +
      (proj ? '<button type="button" class="ilink" data-open="' + esc(proj.id) + '">' + esc(proj.name) + '</button> · ' + esc(proj.stages[proj.current] || "") : esc(it.project)) + '</div></div>' : "";
    drawer.innerHTML = '<div class="dw"><div class="dw-head">' +
      tl('<button type="button" class="dw-close" data-close aria-label="Закрыть">✕</button>') +
      tl('<div class="dw-meta"><span>Идея · ') + esc(it.id) + ' · ' + fmt(it.date) + '</span><span>' + esc(set.title) + '</span></div>' +
      '<h2 id="dw-title">' + esc(it.fullTitle || it.title) + '</h2>' + ideaChip(it) + flagButton(it) +
      '</div><div class="dw-body">' + rsBox(it) + projHtml + (it.notes.length ? it.notes.map(noteHtml).join("") : tl('<div class="empty">Подробностей в реестре нет</div>')) + linksHtml + refsHtml +
      '<p class="source">' + (set.fromDb ? tl('Из общей базы идей ') : tl('Из файла ')) + esc(set.source) + '</p></div></div>';
  }
  // Строка идеи в карточке: номер-ссылка, название, подотдел (если другой), статус.
  const ideaLine = (r, here) => '<div class="irow"><button type="button" class="ilink" data-open="idea:' + esc(r.s.id) + ':' + esc(r.x.id) + '">' + esc(r.x.id) + '</button>' +
    '<span class="rt">' + esc(r.x.title) + (r.s !== here ? '<span class="iid">· ' + esc(r.s.title) + '</span>' : "") + '</span>' + ideaChip(r.x) + '</div>';

  // Stage list of one project: opens on the right when a project is clicked.
  const drawer = $("drawer");
  function findIdea(key) {
    const m = /^idea:([^:]*):(.+)$/.exec(key || "");
    const set = m && board ? board.ideaSets.find((x) => x.id === m[1]) : null;
    const item = set ? set.items.find((x) => x.id === m[2]) : null;
    return item ? { set, item } : null;
  }
  function renderDrawer() {
    if (String(state.open || "").startsWith("day:")) { renderDayDrawer(state.open.slice(4)); return; }
    const idea = findIdea(state.open);
    if (idea) { renderIdeaDrawer(idea.item, idea.set); return; }
    const p = board && board.projects.find((x) => x.id === state.open);
    if (!p) { if (drawer.open) drawer.close(); return; }
    const ahead = Math.max(p.total - p.current - 1, 0);
    const stages = p.stages.map((s, i) => {
      const kind = i < p.current ? "done" : i === p.current ? "now" : "ahead";
      const mark = kind === "done" ? "✓" : "";
      const tag = kind === "done" ? tl("пройден") : kind === "now" ? tl("СЕЙЧАС") : i === p.current + 1 ? tl("следующий") : "";
      return '<li class="st ' + kind + '"' + (kind === "now" ? ' aria-current="step"' : "") + '><span class="num">' + (i + 1) + '</span><span class="dot" aria-hidden="true">' + mark +
        '</span><span class="txt">' + esc(s) + '</span><span class="tag">' + tag + '</span></li>';
    }).join("");
    const events = board.history.filter((h) => h.project === p.id).slice(0, 6);
    const pIdeas = board.ideaSets.flatMap((s) => s.items.filter((x) => x.project === p.id).map((x) => ({ s, x })))
      .sort((a, b) => (b.x.date || 0) - (a.x.date || 0) || b.x.id.localeCompare(a.x.id, undefined, { numeric: true }));
    // Подотдел, откуда большинство идей проекта, не подписываем — подписаны только идеи из других.
    const bySet = new Map(); pIdeas.forEach((r) => bySet.set(r.s, (bySet.get(r.s) || 0) + 1));
    const mainSet = [...bySet.entries()].sort((a, b) => b[1] - a[1]).map((e) => e[0])[0] || null;
    drawer.innerHTML = '<div class="dw"><div class="dw-head">' +
      tl('<button type="button" class="dw-close" data-close aria-label="Закрыть">✕</button>') +
      '<div class="dw-meta"><span>' + esc(td(p.group)) + '</span><span class="lamp ' + p.status + '"><i></i><span>' + STATUS_LABEL[p.status] + '</span></span></div>' +
      '<h2 id="dw-title">' + esc(p.name) + '</h2>' + (p.about ? '<p class="dw-about">' + esc(p.about) + '</p>' : "") +
      '<div class="dw-progress"><div class="meter"><span style="width:' + p.percent + '%"></span></div><b>' + p.percent + '%</b></div>' +
      tl('<div class="dw-counts"><span>Пройдено: <b>') + p.done + tl('</b></span><span>Сейчас: <b>') + (p.total ? 1 : 0) + tl('</b></span><span>Впереди: <b>') + ahead + '</b></span>' +
      tl('<span>Движение: <b>') + (p.days == null ? "—" : daysText(p.days)) + '</b></span></div>' +
      (p.link ? '<a class="dw-link" href="' + esc(p.link) + tl('" target="_blank" rel="noopener">Открыть доску в Trello ↗</a>') : "") +
      autoLine(p) +
      tl('</div><div class="dw-body"><h3>ВСЕ ЭТАПЫ · ') + p.total + '</h3>' +
      (p.total ? '<ol class="stages">' + stages + '</ol>' : tl('<div class="empty">Этапы ещё не записаны</div>')) +
      (events.length ? tl('<h3>СОБЫТИЯ ПРОЕКТА</h3><div class="dw-events">') + events.map((h) => '<div class="ev done"><div class="body">' + esc(h.text) + (h.auto ? tl('<span class="auto">АВТО</span>') : "") +
        '</div><div class="when">' + fmt(h.date) + '</div></div>').join("") + '</div>' : "") +
      (pIdeas.length ? tl('<h3>ИДЕИ ПРОЕКТА · ') + pIdeas.length + '</h3>' + outcomeBar(outcomeCounts(pIdeas.map((r) => r.x)), tl("идеи проекта")) +
        '<div style="height:10px"></div>' + pIdeas.slice(0, state.moreIdeas ? pIdeas.length : 8).map((r) => ideaLine(r, mainSet)).join("") +
        (pIdeas.length > 8 && !state.moreIdeas ? tl('<button type="button" class="jump" data-more>Показать все ') + pIdeas.length + ' ' + plural(pIdeas.length, "идею", "идеи", "идей") + ' ›</button>' : "") : "") +
      '</div></div>';
  }
  function openStages(id) {
    state.open = id;
    state.moreIdeas = false;
    tip.hidden = true;
    renderDrawer();
    if (!state.open || !(String(id).startsWith("day:") || findIdea(id) || board.projects.some((x) => x.id === id))) return;
    if (!drawer.open) drawer.showModal();
    const now = drawer.querySelector(".st.now");
    if (now) now.scrollIntoView({ block: "center" });
    const close = drawer.querySelector(".dw-close");
    if (close) close.focus();
  }
  drawer.addEventListener("close", () => { state.open = null; });
  drawer.addEventListener("click", (e) => {
    // Ссылка на другую идею внутри карточки — открыть ту идею.
    const link = e.target.closest(".ilink");
    if (link) { openStages(link.dataset.open); return; }
    if (e.target.closest("[data-more]")) { state.moreIdeas = true; renderDrawer(); return; }
    // A click on the dark area outside the panel lands on the dialog itself.
    if (e.target === drawer || e.target.closest("[data-close]")) drawer.close();
  });

