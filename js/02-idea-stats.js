"use strict";
  // ---------------------------------------------------------------- аналитика идей
  const pct = (a, b) => b ? Math.round(a / b * 100) : 0;
  const ageText = (n) => n == null ? "—" : n === 0 ? tl("меньше дня") : n + " " + plural(n, "день", "дня", "дней");
  const allIdeas = () => board.ideaSets.flatMap((set) => set.items.map((it) => ({ it, set })));
  function outcomeCounts(items) {
    const c = Object.fromEntries(OUTCOMES.map((o) => [o.k, 0]));
    items.forEach((it) => { c[it.kind in c ? it.kind : "idea"]++; });
    return c;
  }
  function outcomeBar(c, what) {
    const total = OUTCOMES.reduce((a, o) => a + c[o.k], 0);
    if (!total) return '<div class="stack"></div>';
    const shown = OUTCOMES.filter((o) => c[o.k]);
    return '<div class="stack" role="img" aria-label="' + esc(what + ": " + shown.map((o) => o.name + " " + c[o.k]).join(", ")) + '">' +
      shown.map((o) => '<span tabindex="0" style="flex:' + c[o.k] + ';background:' + o.color + '" data-tip="' +
        esc('<div class="t">' + esc(o.name) + ' · ' + esc(what) + '</div><div class="l">' + c[o.k] + ' ' + plural(c[o.k], "идея", "идеи", "идей") + ' · ' + pct(c[o.k], total) + '%</div>') +
        '"></span>').join("") + '</div>';
  }
  const outcomeLegend = () => '<div class="olegend">' + OUTCOMES.map((o) => '<span><i style="background:' + o.color + '"></i>' + o.name + '</span>').join("") + '</div>';
  const ideaRow = (x, right) => '<tr data-open="idea:' + esc(x.set.id) + ':' + esc(x.it.id) + '" tabindex="0" aria-label="' + esc(tl("Открыть идею ") + x.it.id) + '">' +
    '<td><span class="iid">' + esc(x.it.id) + '</span></td><td><div class="pname ititle">' + flagMark(x.it.id) + esc(x.it.title) + '</div><div class="pgroup">' + esc(x.set.title) + '</div></td>' +
    '<td><span class="idate">' + right + '</span></td></tr>';
  const weekStart = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate() - (d.getDay() + 6) % 7);
  function median(list) {
    if (!list.length) return null;
    const a = list.slice().sort((x, y) => x - y), m = Math.floor(a.length / 2);
    return a.length % 2 ? a[m] : Math.round((a[m - 1] + a[m]) / 2);
  }

  function renderIdeaStats() {
    const box = $("insight"), all = allIdeas(), c = outcomeCounts(all.map((x) => x.it)), n = all.length || 1;
    const moved = c.done + c.road;
    const shelf = all.filter((x) => x.it.kind === "idea");
    const ages = shelf.map((x) => daysAgo(x.it.date)).filter((d) => d != null);
    const med = median(ages);
    const tile = (label, value, note, ringPct, color) => '<div class="card tile">' + (ringPct == null ? "" : ring(ringPct, color, label)) +
      '<div class="text"><div class="tlabel">' + label + '</div><div class="value">' + value + '</div><div class="note">' + note + '</div></div></div>';
    const tiles = [
      tile(tl("Перешли в проект"), moved, tl("воплощены или в дорожной карте"), pct(moved, n), "var(--k-road)"),
      tile(tl("Воплощены"), c.done, tl("уже сделано"), pct(c.done, n), "var(--k-done)"),
      tile(tl("Проверяются"), c.explore, tl("исследуются сейчас"), pct(c.explore, n), "var(--k-explore)"),
      tile(tl("Решения CEO"), c.decision, tl("решено, ещё не выполнено"), pct(c.decision, n), "var(--k-decision)"),
      tile(tl("На паузе"), c.wait, tl("ждут условия или отложены"), pct(c.wait, n), "var(--k-wait)"),
      tile(tl("На будущее"), c.future, tl("отложены сознательно"), pct(c.future, n), "var(--k-future)"),
      tile(tl("На полке"), c.idea, med == null ? tl("не проверялись") : tl("не проверялись · медиана ") + med + " " + plural(med, "день", "дня", "дней"), pct(c.idea, n), "var(--k-shelf)"),
      tile(tl("Отказались"), c.dropped, tl("решено не делать"), pct(c.dropped, n), "var(--k-dropped)")
    ];
    // Куда приходят идеи: все вместе и по подотделам
    const rows = [{ name: tl("Все идеи"), items: all.map((x) => x.it), bold: true }].concat(board.ideaSets.map((set) => ({ name: set.title, items: set.items })));
    const bars = rows.map((r) => '<div class="orow"><div class="oname">' + (r.bold ? "<b>" + esc(r.name) + "</b>" : esc(r.name)) + '</div>' +
      outcomeBar(outcomeCounts(r.items), r.name) + '<div class="ototal">' + r.items.length + ' ' + plural(r.items.length, "идея", "идеи", "идей") + '</div></div>').join("");
    const numtab = tl('<table class="numtab"><thead><tr><th>В числах</th>') + OUTCOMES.map((o) => '<th>' + o.name + '</th>').join("") + tl('<th>Перешли в проект</th></tr></thead><tbody>') +
      rows.map((r) => { const k = outcomeCounts(r.items); return '<tr><td>' + esc(r.name) + '</td>' + OUTCOMES.map((o) => '<td>' + k[o.k] + '</td>').join("") +
        '<td>' + pct(k.done + k.road, r.items.length) + '%</td></tr>'; }).join("") + '</tbody></table>';
    // Сколько лежат на полке
    const b7 = ages.filter((d) => d < 7).length, b30 = ages.filter((d) => d >= 7 && d <= 30).length, bOld = ages.filter((d) => d > 30).length;
    const oldest = shelf.slice().sort((a, b) => (a.it.date || 0) - (b.it.date || 0)).slice(0, 6);
    const shelfCard = tl('<div class="card"><h2>Сколько идеи лежат на полке</h2><p class="sub">Идеи, которые ещё не проверялись: сколько дней прошло с их появления</p>') +
      '<div class="minis"><div><div class="v">' + b7 + tl('</div><div class="k">меньше 7 дней</div></div><div><div class="v">') + b30 + tl('</div><div class="k">от 7 до 30 дней</div></div>') +
      '<div><div class="v">' + bOld + tl('</div><div class="k">больше 30 дней</div></div></div>') +
      (oldest.length ? tl('<table><colgroup><col class="c-id"><col><col class="c-date"></colgroup><thead><tr><th>№</th><th>Дольше всех на полке</th><th>Лежит</th></tr></thead><tbody>') +
        oldest.map((x) => ideaRow(x, ageText(daysAgo(x.it.date)))).join("") + '</tbody></table>' : tl('<div class="empty">На полке пусто</div>')) + '</div>';
    // По неделям появления
    const weeks = new Map();
    all.forEach((x) => { if (!x.it.date) return; const w = weekStart(x.it.date).getTime(); if (!weeks.has(w)) weeks.set(w, []); weeks.get(w).push(x.it); });
    const weekRows = [...weeks.entries()].sort((a, b) => b[0] - a[0]).map(([w, items]) => {
      const from = new Date(w), to = new Date(w + 6 * DAY), k = outcomeCounts(items), label = fmtShort(from) + " — " + fmtShort(to);
      return '<div class="orow"><div class="oname">' + label + '</div>' + outcomeBar(k, tl("неделя ") + label) +
        '<div class="ototal">' + items.length + ' · ' + pct(k.done + k.road, items.length) + '%</div></div>';
    }).join("");
    const weekCard = tl('<div class="card"><h2>Идеи по неделям появления</h2><p class="sub">Сколько идей появилось за неделю и что с ними сейчас · справа — сколько и какая доля перешла в проект</p>') +
      outcomeLegend() + (weekRows || tl('<div class="empty">У идей нет дат</div>')) + '</div>';
    // Движение идей (история статусов)
    const H = board.ideaHistory, started = H.started ? fmt(H.started) : "";
    const tr = H.transitions.slice(0, 12).map((t) => {
      const set = board.ideaSets.find((x) => x.id === t.set), it = set && set.items.find((x) => x.id === t.id);
      if (!it) return "";
      const a = OUT[t.from] || OUT.idea, b = OUT[t.to] || OUT.idea;
      return ideaRow({ it, set }, fmt(t.date) + ' · <span class="tdot" style="background:' + a.color + '"></span>' + a.name + ' → <span class="tdot" style="background:' + b.color + '"></span>' + b.name);
    }).join("");
    const histCard = tl('<div class="card"><h2>Движение идей</h2><p class="sub">Как идеи переходят дальше: ') +
      (H.fromDb ? tl('каждая смена статуса записывается в журнал общей базы идей') : tl('Пульт записывает итог каждой идеи при запуске и синхронизации')) +
      (started ? tl(' · история ведётся с ') + started : "") + '</p>' +
      (H.error ? '<div class="empty">' + esc(H.error) + '</div>' : tr ? tl('<table><colgroup><col class="c-id"><col><col class="c-istatus"></colgroup><thead><tr><th>№</th><th>Идея</th><th>Переход</th></tr></thead><tbody>') + tr + '</tbody></table>' :
        tl('<div class="empty">Переходов пока нет: они появятся, когда у идей сменится статус') + (started ? tl(' (история с ') + started + ')' : "") + '</div>') + '</div>';
    box.innerHTML = '<div class="tiles t8">' + tiles.join("") + '</div>' +
      tl('<div class="card"><h2>Куда приходят идеи</h2><p class="sub">Все идеи и по подотделам · наведите на часть полосы, чтобы увидеть число</p>') + outcomeLegend() + bars + numtab + '</div>' +
      '<div class="cols2">' + shelfCard + weekCard + '</div>' + histCard;
  }

