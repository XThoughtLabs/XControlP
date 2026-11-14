"use strict";
  // ---------------------------------------------------------------- План дня
  // Задачи на день: из проектов и этапов или свои; очередь и приоритет; отметки; «на завтра».
  // Хранит программа Пульта (day.db); окно читает /day.json и шлёт изменения в /day/op.
  // Claude пишет запросы в day-inbox — программа применяет их сама, окно видит их при следующем чтении.
  const DP_STATUS = [["planned", "○", tl("План")], ["active", "▶", tl("В работе")], ["done", "✓", tl("Сделано")], ["partial", "◐", tl("Частично")], ["not_done", "✗", tl("Не сделано")]];
  const DP_LABEL = { planned: tl("запланировано"), active: tl("в работе"), done: tl("сделано"), partial: tl("частично"), not_done: tl("не сделано"), moved: tl("перенесено"), removed: tl("убрано") };
  const DP_PRIO = { high: tl("Важно"), normal: tl("Обычно"), low: tl("Потом") };
  const DP_NEXT_PRIO = { high: "normal", normal: "low", low: "high" };
  const DP_KIND = { stage: tl("Завершить этап"), advance: tl("Продвинуться"), task: tl("Задача") };
  const DP_CHIPS = [tl("1 урок"), tl("2 урока"), tl("1 час"), tl("2 часа"), tl("1 глава")];
  state.day = { key: "", data: null, text: "", busy: false, err: "", showHidden: false, noteOpen: "", loading: false,
    form: { project: "", kind: "task", stage: null, amount: "", title: "", priority: "normal" } };

  function dpServer() { return !!token && location.protocol.startsWith("http"); }
  function dpKey() { if (!state.day.key) state.day.key = dayKey(today()); return state.day.key; }
  function dpProject(id) { return board.projects.find((p) => p.id === id) || null; }
  function dpVisible(items) { return items.filter((i) => i.status !== "moved" && i.status !== "removed"); }
  function dpTodaySummary() {
    const D = state.day.data;
    return D && Array.isArray(D.summary) ? D.summary.find((x) => x.day === D.today) || null : null;
  }
  function dayLeftCount() { const s = dpTodaySummary(); return s ? s.left : 0; }
  function dpShort(key) { const d = parseDate(key); return d ? String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0") : key; }
  function dpDayTitle(key) {
    const d = parseDate(key);
    if (!d) return key;
    const diff = Math.round((d - today()) / DAY);
    const rel = diff === 0 ? tl("сегодня") : diff === 1 ? tl("завтра") : diff === -1 ? tl("вчера") : "";
    const wd = WD_FULL[d.getDay()];
    return (rel ? rel[0].toUpperCase() + rel.slice(1) + ", " + wd : wd[0].toUpperCase() + wd.slice(1)) + ", " + d.getDate() + " " + MONTHS_GEN[d.getMonth()] + " " + d.getFullYear();
  }

  async function dayLoad(silent) {
    const S = state.day;
    if (!dpServer() || S.loading) return;
    const key = dpKey();
    S.loading = true;
    try {
      const r = await fetch("/day.json?day=" + encodeURIComponent(key) + "&v=" + Date.now(), { cache: "no-store" });
      const res = await r.json();
      if (key !== S.key) return;                         // пока ждали, перешли на другой день
      if (!res.ok) { S.err = res.error || tl("План дня не прочитался"); }
      else {
        const text = JSON.stringify(res);
        if (S.err && !silent) S.err = "";
        if (text === S.text && silent) return;
        S.text = text; S.data = res;
        if (!silent) S.err = "";
      }
    } catch (err) {
      S.err = tl("Программа Пульта не отвечает: ") + (err && err.message || err);
    } finally {
      S.loading = false;
    }
    renderNav();
    if (state.view === "day") renderDay();
    else if (document.querySelector("[data-plan], .plan-in")) render();   // кнопки «В план дня» узнают, что уже в плане
  }

  async function dayPost(ops) {
    const S = state.day;
    if (!dpServer()) { S.err = tl("Изменения работают, когда Пульт открыт ярлыком «XControlP» на рабочем столе."); renderDay(); return false; }
    if (S.busy) return false;
    S.busy = true;
    try {
      const r = await fetch("/day/op", { method: "POST", headers: { "X-Pult-Token": token, "Content-Type": "application/json" },
        body: JSON.stringify({ day: dpKey(), ops }) });
      let res = {};
      try { res = await r.json(); } catch (err) { res = { ok: false, error: tl("ответ ") + r.status }; }
      if (!r.ok || !res.ok) { S.err = res.error || (tl("ответ ") + r.status); return false; }
      S.err = ""; S.data = res; S.text = JSON.stringify(res);
      return true;
    } catch (err) {
      S.err = tl("Не сохранилось: ") + (err && err.message || err);
      return false;
    } finally {
      S.busy = false;
      renderNav(); renderDay();
    }
  }

  // «В план дня»: тревогу, риск или предложение одной кнопкой — в план на сегодня.
  // Задача своя (вид task), с проектом, если он известен. Источник пишется в заметку задачи в квадратных скобках:
  // по нему кнопка видит, что задача уже в плане, и после перезапуска Пульта. Отменить — «убрать» в плане дня.
  const PLAN = { done: new Set(), req: {}, busy: new Set() };
  const planTag = (src) => "[" + src + "]";
  function planHas(src) {
    if (PLAN.done.has(src)) return true;
    const D = state.day.data;
    return !!(D && D.day === dayKey(today()) && (D.items || []).some((i) => i.status !== "removed" && String(i.note || "").indexOf(planTag(src)) >= 0));
  }
  function planBtn(src, title, project, from) {
    if (!dpServer()) return "";
    if (planHas(src)) return '<span class="plan-in">✓ ' + esc(tl("уже в плане")) + '</span>';
    PLAN.req[src] = { title, project, from };
    return '<button type="button" class="albtn plan-btn" data-plan="' + esc(src) + '">' + esc(tl("В план дня")) + '</button>';
  }
  async function planAdd(src, el) {
    const q = PLAN.req[src];
    if (!q || PLAN.busy.has(src) || planHas(src)) return;
    const day = dayKey(today());
    const title = String(q.title || "").replace(/\*\*/g, "").replace(/\s+/g, " ").trim().slice(0, 300);
    const op = { op: "add", day, kind: "task", priority: "normal", title, note: (q.from ? q.from + " " : "") + planTag(src) };
    if (q.project && dpProject(q.project)) op.project = q.project;
    PLAN.busy.add(src);
    if (el) el.disabled = true;
    try {
      const r = await fetch("/day/op", { method: "POST", headers: { "X-Pult-Token": token, "Content-Type": "application/json" }, body: JSON.stringify({ day, ops: [op] }) });
      let res = {};
      try { res = await r.json(); } catch (err) { res = { ok: false, error: tl("ответ ") + r.status }; }
      if (!r.ok || !res.ok) throw new Error(res.error || (tl("ответ ") + r.status));
      PLAN.done.add(src);
      if (src.startsWith("pr:")) prMarkSet(src.slice(3), "accepted", null);
      if (!state.day.key || state.day.key === day) { state.day.data = res; state.day.text = JSON.stringify(res); }
      render();
    } catch (err) {
      if (el) el.disabled = false;
      showSync("bad", tl("Задача не добавилась в план дня"), [["err", esc(String(err && err.message || err))]]);
    } finally {
      PLAN.busy.delete(src);
    }
  }

  function dpItemHtml(it, n) {
    const p = it.project_id ? dpProject(it.project_id) : null;
    const pname = p ? p.name : td(it.project_name || "");
    const what = it.kind === "stage" ? tl("Этап ") + (it.stage_index + 1) + ": " + tdt(it.title) : tdt(it.title);
    const hidden = it.status === "moved" || it.status === "removed";
    const open = state.day.noteOpen === it.id;
    let html = '<div class="dp-item st-' + esc(it.status) + ' pr-' + esc(it.priority) + '" data-item="' + esc(it.id) + '">' +
      '<div class="dp-num">' + (hidden ? "" : n) + '</div><div class="dp-body"><div class="dp-what">' +
      (pname ? '<span class="dp-proj" data-open="' + esc(it.project_id) + tl('" title="Этапы проекта">') + esc(pname) + '</span>' : "") +
      '<span class="dp-kind">' + esc(DP_KIND[it.kind]) + '</span><span class="dp-title">' + esc(what) + '</span>' +
      (it.priority !== "normal" ? '<span class="dp-prio ' + esc(it.priority) + '">' + esc(DP_PRIO[it.priority]) + '</span>' : "") +
      (it.added_by === "claude" ? tl('<span class="dp-by" title="Добавил Claude">Claude</span>') : "") + '</div>';
    const meta = [];
    if (it.moved_from) meta.push(tl("перенесено с ") + dpShort(it.moved_from_day));
    if (it.status === "moved") meta.push(tl("перенесено на ") + dpShort(it.moved_to_day));
    if (it.status === "removed") meta.push(tl("убрано"));
    if (meta.length) html += '<div class="dp-meta">' + esc(meta.join(" · ")) + '</div>';
    if (it.note && !open) html += '<div class="dp-note">' + esc(it.note) + '</div>';
    if (open) html += '<div class="dp-noteedit"><textarea id="dp-note-' + esc(it.id) + tl('" rows="2" maxlength="2000" placeholder="Что получилось, что осталось">') + esc(it.note) + '</textarea>' +
      '<button type="button" class="cal-btn primary" data-dp="note-save:' + esc(it.id) + tl('">Сохранить</button>') +
      tl('<button type="button" class="cal-btn" data-dp="note-cancel">Отмена</button></div>');
    html += '</div>';
    if (it.status === "moved") {
      html += '<div class="dp-acts"><button type="button" class="cal-btn" data-dp="goto:' + esc(it.moved_to_day) + tl('">Открыть ') + esc(dpShort(it.moved_to_day)) + '</button></div>';
    } else if (it.status === "removed") {
      html += '<div class="dp-acts"><button type="button" class="cal-btn" data-dp="restore:' + esc(it.id) + tl('">Вернуть</button></div>');
    } else {
      html += tl('<div class="dp-ctl"><div class="dp-status" role="group" aria-label="Выполнение">') + DP_STATUS.map(([s, icon, label]) =>
        '<button type="button" class="dp-st ' + s + (it.status === s ? " on" : "") + '" data-dp="st:' + esc(it.id) + ':' + s + '" aria-pressed="' + (it.status === s) +
        '" title="' + label + '"><span>' + icon + '</span>' + label + '</button>').join("") + '</div>' +
        '<div class="dp-acts">' +
        '<button type="button" class="dp-ic" data-dp="up:' + esc(it.id) + tl('" title="Выше в очереди" aria-label="Выше">↑</button>') +
        '<button type="button" class="dp-ic" data-dp="down:' + esc(it.id) + tl('" title="Ниже в очереди" aria-label="Ниже">↓</button>') +
        '<button type="button" class="dp-ic" data-dp="prio:' + esc(it.id) + tl('" title="Приоритет: ') + esc(DP_PRIO[it.priority]) + tl(' (нажмите, чтобы сменить)" aria-label="Приоритет">⚑</button>') +
        '<button type="button" class="dp-ic" data-dp="note:' + esc(it.id) + tl('" title="Заметка" aria-label="Заметка">✎</button>') +
        (it.status !== "done" ? '<button type="button" class="cal-btn" data-dp="carry:' + esc(it.id) + tl('" title="Перенести на следующий день">На завтра</button>') : "") +
        '<button type="button" class="dp-ic" data-dp="remove:' + esc(it.id) + tl('" title="Убрать из плана (можно вернуть)" aria-label="Убрать">✕</button></div></div>');
    }
    return html + '</div>';
  }

  function dpFormHtml() {
    const F = state.day.form;
    const groups = board.groups.filter((g) => board.projects.some((p) => p.group === g));
    const opts = tl('<option value="">Без проекта — своя задача</option>') + groups.map((g) => '<optgroup label="' + esc(td(g)) + '">' +
      board.projects.filter((p) => p.group === g).map((p) => '<option value="' + esc(p.id) + '"' + (F.project === p.id ? " selected" : "") + '>' +
        esc(p.name) + (p.status === "work" ? "" : " · " + esc(STATUS_LABEL[p.status] || "")) + '</option>').join("") + '</optgroup>').join("");
    const p = F.project ? dpProject(F.project) : null;
    if (!p) F.kind = "task";
    const kinds = [["stage", tl("Завершить этап")], ["advance", tl("Продвинуться")], ["task", tl("Своя задача")]].map(([k, l]) =>
      '<button type="button" data-dp="kind:' + k + '" class="' + (F.kind === k ? "active" : "") + '"' + (!p && k !== "task" ? " disabled" : "") + '>' + l + '</button>').join("");
    let detail = "";
    if (F.kind === "stage" && p) {
      if (F.stage == null || F.stage < p.current || F.stage >= p.stages.length) F.stage = p.current;
      detail = tl('<label class="dp-l">Какой этап завершить<select id="dp-stage" data-dp-field="stage">') + p.stages.map((s, i) => i < p.current ? "" :
        '<option value="' + i + '"' + (F.stage === i ? " selected" : "") + '>' + (i + 1) + '. ' + esc(s) + (i === p.current ? tl(" — сейчас") : "") + '</option>').join("") + '</select></label>';
    } else if (F.kind === "advance" && p) {
      detail = tl('<label class="dp-l">Насколько продвинуться<input id="dp-amount" data-dp-field="amount" maxlength="200" placeholder="например: 1 урок" value="') + esc(F.amount) + '"></label>' +
        '<div class="dp-chips">' + DP_CHIPS.map((c) => '<button type="button" class="cal-chip" data-dp="chip:' + esc(c) + '">' + esc(c) + '</button>').join("") + '</div>' +
        tl('<div class="dp-hint">Сейчас этап ') + (p.current + 1) + ': ' + esc(p.stages[p.current] || "—") + '</div>';
    } else {
      detail = tl('<label class="dp-l">Что сделать<input id="dp-title" data-dp-field="title" maxlength="300" placeholder="например: позвонить в банк" value="') + esc(F.title) + '"></label>';
    }
    const prio = ["high", "normal", "low"].map((k) => '<button type="button" data-dp="fprio:' + k + '" class="' + (F.priority === k ? "active" : "") + '">' + DP_PRIO[k] + '</button>').join("");
    const quick = board.projects.filter((x) => x.status === "work").map((x) =>
      '<button type="button" class="cal-chip" data-dp="quick:' + esc(x.id) + '" title="' + esc(x.group === "Учёба" ? tl("Продвинуться: 1 урок") : tl("Завершить этап ") + (x.current + 1) + ": " + (x.stages[x.current] || "")) + '">＋ ' +
      esc(x.name) + ' <b>' + (x.group === "Учёба" ? tl("1 урок") : tl("этап ") + (x.current + 1)) + '</b></button>').join("");
    return tl('<div class="card dp-add"><h2>Добавить в план</h2><p class="sub">Выберите проект и что в нём сделать за день</p>') +
      tl('<label class="dp-l">Проект<select id="dp-project" data-dp-field="project">') + opts + '</select></label>' +
      tl('<div class="dp-l">Что сделать<span class="cal-seg">') + kinds + '</span></div>' + detail +
      tl('<div class="dp-l">Приоритет<span class="cal-seg">') + prio + '</span></div>' +
      '<button type="button" class="cal-btn primary dp-addbtn" data-dp="add"' + (state.day.busy ? " disabled" : "") + tl('>Добавить в план</button>') +
      (quick ? tl('<div class="dp-quick"><div class="dp-hint">Быстро — проекты в работе:</div><div class="dp-chips">') + quick + '</div></div>' : "") + '</div>';
  }

  function dpCalendarHtml(key) {
    const d = parseDate(key), end = addDays(d, 1);
    const list = (board.calendar.events || []).filter((e) => e.start < end && e.end > d).sort((a, b) => a.start - b.start);
    const rows = list.map((e) => {
      const night = overnightLabel(e);
      return '<div class="dp-ev"><i style="background:' + calColor(e.cal) + '"></i><span class="when">' +
        (e.allDay ? tl("весь день") : hm(e.start) + "–" + hm(e.end)) + '</span><span class="what">' + esc(e.title) +
        (night ? ' <span class="night">' + esc(night) + '</span>' : "") + '</span></div>';
    }).join("");
    return tl('<div class="card"><h2>Календарь в этот день</h2><p class="sub">Ваши календари Google — чтобы видеть занятое время</p>') +
      (rows || tl('<div class="empty">Записей нет') + (board.calendar.available && board.calendar.events.length ? "" : tl(" (календарь не подключён или пуст)")) + '</div>') + '</div>';
  }

  function dpClaudeHtml(D) {
    const req = (D && D.requests || []).slice(0, 5).map((r) => {
      const res = r.result || {}, n = (res.results || []).reduce((a, x) => a + (x.op === "plan" ? (x.added || []).length : x.op === "add" ? 1 : 0), 0);
      return '<li class="' + (r.ok ? "" : "err") + '">' + esc(stamp(r.at)) + ' — ' + (r.ok ? tl("принят") + (n ? tl(": задач ") + n : "") : tl("не принят: ") + esc(res.error || "")) + '</li>';
    }).join("");
    return tl('<div class="card dp-claude"><h2>Через Claude</h2><p class="dp-text">Скажите мне в чате, например: <i>«спланируй завтра: урок английского, отчёт и этап сайта»</i> или <i>«давай сделаем день так…»</i>. ') +
      tl('Я добавлю задачи сюда — они придут с пометкой <span class="dp-by">Claude</span>. Если Пульт закрыт, появятся при следующем открытии.</p>') +
      (D && D.pending ? tl('<p class="dp-hint">Ждут добавления: ') + D.pending + '</p>' : "") +
      (req ? tl('<div class="dp-hint">Последние запросы:</div><ul class="dp-req">') + req + '</ul>' : "") + '</div>';
  }

  function dpRecentHtml(D) {
    const key = dpKey();
    const list = (D && D.summary || []).filter((s) => s.total > 0 && s.day <= D.today).slice(-7).reverse();
    const ahead = (D && D.summary || []).filter((s) => s.total > 0 && s.day > D.today).slice(0, 3);
    const row = (s) => '<button type="button" class="dp-day' + (s.day === key ? " on" : "") + '" data-dp="goto:' + esc(s.day) + '">' +
      '<span class="d">' + esc(WD[parseDate(s.day).getDay()] + " " + dpShort(s.day)) + '</span>' +
      '<span class="bar"><span style="width:' + s.percent + '%"></span></span>' +
      '<span class="n">' + s.counts.done + (s.counts.partial ? "+½" : "") + tl(' из ') + s.total + '</span></button>';
    return tl('<div class="card"><h2>Дни</h2><p class="sub">Сколько из плана сделано · нажмите, чтобы открыть день</p>') +
      (ahead.length ? tl('<div class="dp-hint">Впереди:</div>') + ahead.map(row).join("") : "") +
      (list.length ? (ahead.length ? tl('<div class="dp-hint">Сегодня и раньше:</div>') : "") + list.map(row).join("") : tl('<div class="empty">Пока ни одного дня с планом</div>')) + '</div>';
  }

  function renderDay() {
    const S = state.day, box = $("dayplan");
    if (!box || state.view !== "day") return;
    const key = dpKey();
    const D = S.data && S.data.day === key ? S.data : null;
    const focus = document.activeElement && box.contains(document.activeElement) ? document.activeElement.id : "";
    const caret = focus && "selectionStart" in document.activeElement ? [document.activeElement.selectionStart, document.activeElement.selectionEnd] : null;
    const items = D ? D.items : [];
    const vis = dpVisible(items), hid = items.filter((i) => !vis.includes(i));
    const sum = D && (D.summary || []).find((s) => s.day === key);
    const bar = '<div class="cal-bar">' +
      tl('<button type="button" class="cal-btn" data-dp="prev" aria-label="Предыдущий день">‹</button>') +
      tl('<button type="button" class="cal-btn" data-dp="today">Сегодня</button>') +
      tl('<button type="button" class="cal-btn" data-dp="next" aria-label="Следующий день">›</button>') +
      '<span class="cal-label">' + esc(dpDayTitle(key)) + '</span>' +
      '<input type="date" class="dp-date" value="' + esc(key) + tl('" aria-label="Перейти к дню">') +
      '<button type="button" class="cal-btn" data-dp="review">' + tl("Закрыть день") + '</button>' +
      (sum && sum.total ? tl('<span class="dp-sum">Сделано ') + sum.counts.done + (sum.counts.partial ? tl(", частично ") + sum.counts.partial : "") + tl(' из ') + sum.total + ' · <b>' + sum.percent + '%</b></span>' : "") + '</div>';
    let main;
    if (!dpServer()) {
      main = tl('<div class="card"><div class="empty">План дня работает, когда Пульт открыт ярлыком «XControlP» на рабочем столе (через программу Пульта).</div></div>');
    } else if (!D) {
      main = '<div class="card"><div class="empty">' + (S.err ? "" : tl("Загрузка…")) + '</div></div>';
    } else {
      main = tl('<div class="card"><div class="dp-head"><div><h2>Задачи дня</h2><p class="sub">Сверху вниз — по очереди · ↑ ↓ — переставить · ⚑ — приоритет</p></div>') +
        (vis.length > 1 ? tl('<button type="button" class="cal-btn" data-dp="sortprio" title="Важные — наверх, «потом» — вниз; внутри — как было">По приоритету</button>') : "") + '</div>' +
        (vis.length ? '<div class="dp-list">' + vis.map((it, i) => dpItemHtml(it, i + 1)).join("") + '</div>'
          : tl('<div class="empty">На этот день задач нет. Добавьте справа или попросите Claude.</div>')) +
        (hid.length ? '<button type="button" class="dp-more" data-dp="hidden" aria-expanded="' + S.showHidden + '">' + (S.showHidden ? "▾" : "▸") +
          tl(' Перенесённые и убранные (') + hid.length + ')</button>' + (S.showHidden ? '<div class="dp-list dim">' + hid.map((it) => dpItemHtml(it, 0)).join("") + '</div>' : "") : "") + '</div>' +
        tl('<div class="card"><h2>Итог дня</h2><p class="sub">Что получилось за день, что мешало — для себя</p><div class="dp-noteedit">') +
        tl('<textarea id="dp-daynote" rows="3" maxlength="4000" placeholder="Например: урок английского сделан, отчёт — завтра">') + esc(D.note || "") + '</textarea>' +
        tl('<button type="button" class="cal-btn" data-dp="daynote">Сохранить итог</button></div></div>');
    }
    box.innerHTML = bar + (S.err ? '<div class="cal-hint dp-err">' + esc(S.err) + tl('<button type="button" class="cal-btn" data-dp="reload">Обновить</button></div>') : "") +
      '<div class="dp-cols"><div class="dp-main">' + main + '</div><div class="dp-side">' +
      (dpServer() ? dpFormHtml() : "") + dpClaudeHtml(D) + dpCalendarHtml(key) + (D ? dpRecentHtml(D) : "") + '</div></div>' +
      tl('<div class="cal-note">Этапы проектов на Пульте план дня не двигает — их передвигает штаб. Задачи не удаляются: «убрать» можно вернуть.</div>');
    if (focus) {
      const el = document.getElementById(focus);
      if (el) { el.focus(); if (caret && "setSelectionRange" in el) try { el.setSelectionRange(caret[0], caret[1]); } catch (err) { /* select */ } }
    }
  }

  function dpOrder(ids) { return dayPost([{ op: "order", day: dpKey(), ids }]); }

  async function dayAction(a) {
    const S = state.day, F = S.form, D = S.data && S.data.day === dpKey() ? S.data : null;
    const vis = D ? dpVisible(D.items).map((i) => i.id) : [];
    const [cmd, arg, arg2] = a.split(":");
    const go = (key) => { S.key = key; S.noteOpen = ""; S.err = ""; renderDay(); dayLoad(false); };
    if (cmd === "prev" || cmd === "next") return go(dayKey(addDays(parseDate(dpKey()), cmd === "prev" ? -1 : 1)));
    if (cmd === "today") return go(dayKey(today()));
    if (cmd === "goto") return parseDate(arg) ? go(arg) : undefined;
    if (cmd === "reload") { S.err = ""; return dayLoad(false); }
    if (cmd === "review") { state.rev.key = dpKey(); state.rev.rating = null; state.rev.note = null; state.view = "review"; history.replaceState(null, "", "#review"); render(); return revLoad(false); }
    if (cmd === "hidden") { S.showHidden = !S.showHidden; return renderDay(); }
    if (cmd === "kind") { F.kind = arg; return renderDay(); }
    if (cmd === "fprio") { F.priority = arg; return renderDay(); }
    if (cmd === "chip") { F.amount = a.slice(5); return renderDay(); }
    if (cmd === "note") { S.noteOpen = S.noteOpen === arg ? "" : arg; renderDay(); const t = document.getElementById("dp-note-" + arg); if (t) t.focus(); return; }
    if (cmd === "note-cancel") { S.noteOpen = ""; return renderDay(); }
    if (cmd === "note-save") {
      const t = document.getElementById("dp-note-" + arg);
      if (await dayPost([{ op: "note", id: arg, note: t ? t.value : "" }])) { S.noteOpen = ""; renderDay(); }
      return;
    }
    if (cmd === "daynote") { const t = $("dp-daynote"); return dayPost([{ op: "day_note", day: dpKey(), note: t ? t.value : "" }]); }
    if (cmd === "st") return dayPost([{ op: "status", id: arg, status: arg2 }]);
    if (cmd === "carry") return dayPost([{ op: "carry", id: arg }]);
    if (cmd === "remove") return dayPost([{ op: "remove", id: arg }]);
    if (cmd === "restore") return dayPost([{ op: "restore", id: arg }]);
    if (cmd === "prio") {
      const it = D && D.items.find((i) => i.id === arg);
      return it ? dayPost([{ op: "priority", id: arg, priority: DP_NEXT_PRIO[it.priority] }]) : undefined;
    }
    if (cmd === "up" || cmd === "down") {
      const i = vis.indexOf(arg), j = cmd === "up" ? i - 1 : i + 1;
      if (i < 0 || j < 0 || j >= vis.length) return;
      [vis[i], vis[j]] = [vis[j], vis[i]];
      return dpOrder(vis);
    }
    if (cmd === "sortprio") {
      const rank = { high: 0, normal: 1, low: 2 }, items = dpVisible(D.items);
      const sorted = items.map((it, n) => [it, n]).sort((x, y) => rank[x[0].priority] - rank[y[0].priority] || x[1] - y[1]).map((x) => x[0].id);
      return sorted.join() === vis.join() ? undefined : dpOrder(sorted);
    }
    if (cmd === "quick") {
      const p = dpProject(arg);
      if (!p) return;
      return dayPost([p.group === "Учёба" ? { op: "add", day: dpKey(), kind: "advance", project: p.id, amount: tl("1 урок") }
        : { op: "add", day: dpKey(), kind: "stage", project: p.id, stage: p.current }]);
    }
    if (cmd === "add") {
      const op = { op: "add", day: dpKey(), kind: F.kind, priority: F.priority };
      if (F.project) op.project = F.project;
      if (F.kind === "stage") op.stage = +F.stage;
      if (F.kind === "advance") { if (!F.amount.trim()) { S.err = tl("Напишите, насколько продвинуться: например, «1 урок»."); return renderDay(); } op.amount = F.amount; }
      if (F.kind === "task") { if (!F.title.trim()) { S.err = tl("Напишите, что сделать."); return renderDay(); } op.title = F.title; }
      if (await dayPost([op])) { F.amount = ""; F.title = ""; renderDay(); }
    }
  }
  function dayField(el) {
    const F = state.day.form, f = el.dataset.dpField;
    if (f === "project") { F.project = el.value; F.stage = null; const p = dpProject(F.project); F.kind = p ? (p.group === "Учёба" || !p.stages.length ? "advance" : "stage") : "task"; renderDay(); }
    else if (f === "stage") F.stage = +el.value;
    else if (f === "amount") F.amount = el.value;
    else if (f === "title") F.title = el.value;
  }

