// Checks of the window's own code (js/*.js) in Node, without a browser: the files 01 to 09 run in a vm
// with a stub page (10-settings.js starts the window and is not run). Nothing is written to disk.
//
//   node tests/window_test.js        exit 0: every check passes; exit 1: a check failed
//
// Each check tries to break one rule of the optional "icons" key and of the digest topic labels.
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const PASSED = [];
const FAILED = [];

function check(name, cond, detail) {
  (cond ? PASSED : FAILED).push(name);
  console.log((cond ? "ok   " : "FAIL ") + name + (cond ? "" : "  - " + (detail || "")));
}

function stubElement(id) {
  return {
    id, innerHTML: "", textContent: "", hidden: false, value: "", dataset: {}, style: {}, children: [],
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    addEventListener() {}, removeEventListener() {}, setAttribute() {}, removeAttribute() {}, getAttribute() { return null; },
    appendChild(child) { return child; }, remove() {}, querySelector() { return null; }, querySelectorAll() { return []; },
    closest() { return null; }, focus() {}, showModal() {}, close() {},
    getBoundingClientRect() { return { left: 0, top: 0, width: 0, height: 0 }; },
  };
}

// A fresh page: its own globals, the window files 01 to 09 loaded in order; board: window.BOARD at load (its language).
function page(board, withI18n) {
  const els = {};
  const document = {
    getElementById: (id) => els[id] || (els[id] = stubElement(id)), createElement: (tag) => stubElement(tag),
    addEventListener() {}, body: stubElement("body"), documentElement: stubElement("html"),
    querySelector: () => null, querySelectorAll: () => [], title: "",
  };
  const ctx = {
    document, location: { protocol: "http:", hash: "", search: "" },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} }, navigator: { language: "ru" },
    setTimeout, clearTimeout, setInterval: () => 0, clearInterval() {}, console,
  };
  ctx.window = ctx;
  if (board) ctx.BOARD = board;
  vm.createContext(ctx);
  if (withI18n) vm.runInContext(fs.readFileSync(path.join(ROOT, "i18n.js"), "utf8"), ctx, { filename: "i18n.js" });
  const files = fs.readdirSync(path.join(ROOT, "js")).filter((f) => /^0\d-.*\.js$/.test(f)).sort();
  for (const f of files) vm.runInContext(fs.readFileSync(path.join(ROOT, "js", f), "utf8"), ctx, { filename: f });
  return { ctx, els, run: (code) => vm.runInContext(code, ctx) };
}

function data(icons, extra) {
  const d = {
    projects: [{ id: "p1", name: "P", group: "Work", status: "в работе", stages: ["a"] }],
    groups: ["Work", "Технологии", "calendar"],
  };
  if (icons !== undefined) d.icons = icons;
  return Object.assign(d, extra || {});
}

function main() {
  // W1: a group's symbol reaches the menu as text, never as markup (style "base", the default).
  {
    const p = page();
    p.ctx.DATA = data({ groups: { Work: { symbol: "<!--" } } });
    p.run("board = normalize(DATA); renderNav();");
    const html = p.els.nav.innerHTML;
    check("W1 group symbol escaped in the menu (style base)", !html.includes("<!--") && html.includes("&lt;!--"),
      html.slice(Math.max(0, html.indexOf("Work") - 120), html.indexOf("Work") + 10));
  }

  // W2: the same in the other branches that fall back to the symbol: no image name, a file:// page, a missing image.
  {
    const p = page();
    const noName = p.run('iconImg("comic", "", "<b>")');
    p.ctx.location.protocol = "file:";
    const fromFile = p.run('iconImg("comic", "tech", "<b>")');
    p.ctx.location.protocol = "http:";
    p.run('ICON_MISSING.add("comic/tech")');
    const missing = p.run('iconImg("comic", "tech", "<b>")');
    check("W2 symbol escaped without an image, on file:// and for a missing image",
      [noName, fromFile, missing].every((s) => s === "&lt;b&gt;"), JSON.stringify([noName, fromFile, missing]));
  }

  // W3: set, changed, then removed without reloading the page: the icons follow the data every time.
  {
    const p = page();
    const state = () => p.run('JSON.stringify([GROUP_ICON.Work || null, NAV_ICON.Work || null, SET_ICON.main, RP_ICON.summary])');
    p.ctx.DATA = data({ groups: { Work: { symbol: "★", image: "tech" } }, idea_sets: { main: "idea-stats" }, reports: { summary: "study" } });
    p.run("board = normalize(DATA);");
    const set = state();
    p.ctx.DATA = data({ groups: { Work: { symbol: "☆", image: "books" } }, idea_sets: { main: "perf" }, reports: { summary: "tech" } });
    p.run("board = normalize(DATA);");
    const changed = state();
    p.ctx.DATA = data({ groups: { Work: { symbol: "", image: "Not Valid" } }, idea_sets: { main: 5 }, reports: { summary: "../x" } });
    p.run("board = normalize(DATA);");
    const invalid = state();
    p.ctx.DATA = data();
    p.run("board = normalize(DATA); renderNav();");
    const removed = state();
    const nav = p.els.nav.innerHTML;
    const workIcon = (nav.match(/data-view="Work"[^>]*><span class="icon">([^<]*)</) || [])[1];
    check("W3 icons follow the data: set, changed, invalid, removed",
      set === JSON.stringify(["★", "tech", "idea-stats", "study"]) && changed === JSON.stringify(["☆", "books", "perf", "tech"])
      && invalid === JSON.stringify([null, null, "ideas", "obzor"]) && removed === JSON.stringify([null, null, "ideas", "obzor"])
      && workIcon === "•", JSON.stringify({ set, changed, invalid, removed, workIcon }));
  }

  // W4: a group named like a built-in section cannot take that section's image; a built-in group still can change its own.
  {
    const p = page();
    p.ctx.DATA = data({ groups: { calendar: { image: "tech" }, all: { image: "tech" }, alerts: { image: "tech" }, proposals: { image: "tech" },
      "Технологии": { image: "growth" } } });
    p.run("board = normalize(DATA);");
    const got = p.run('JSON.stringify([NAV_ICON.calendar, NAV_ICON.all, NAV_ICON.alerts, NAV_ICON.proposals || null, NAV_ICON["Технологии"]])');
    check("W4 built-in section images kept (proposals included), a built-in group's own image still set",
      got === JSON.stringify(["calendar", "obzor", "alerts", null, "growth"]), got);
  }

  // W5: an image name of 40 characters is taken, 41 is not (the server serves at most 40: pult/settings.py ICON_PATH).
  {
    const p = page();
    const n40 = "a".repeat(40), n41 = "a".repeat(41);
    p.ctx.DATA = data({ groups: { Work: { image: n40 } }, idea_sets: { main: n41 }, reports: { summary: n41 } });
    p.run("board = normalize(DATA);");
    const got = p.run("JSON.stringify([NAV_ICON.Work, SET_ICON.main, RP_ICON.summary])");
    check("W5 image name: 40 characters taken, 41 refused", got === JSON.stringify([n40, "ideas", "obzor"]), got);
  }

  // W6: a digest topic's label is looked up only among own keys: "constructor" and "toString" are ordinary topic ids.
  {
    const p = page();
    p.ctx.BOARD = { digests: { ok: true, topics: { constructor: "Construction" }, digests: [{ date: "2026-11-14", items: [
      { id: "a", topic: "constructor", title: "t1" }, { id: "b", topic: "toString", title: "t2" }, { id: "c", topic: "llm-models", title: "t3" }] }] } };
    p.run('state.view = "digest"; renderDigest();');
    const labels = [...p.els.digest.innerHTML.matchAll(/<span class="dg-topic">([^<]*)<\/span>/g)].map((m) => m[1]);
    check("W6 topic labels from own keys only", JSON.stringify(labels) === JSON.stringify(["Construction", "toString", "Модели"]),
      JSON.stringify(labels));
  }

  // W7: group names from the data equal to built-in JavaScript names are ordinary keys of the icon maps.
  {
    const p = page();
    p.ctx.DATA = { projects: [{ id: "p1", name: "P", group: "constructor", status: "в работе", stages: ["a"] }], groups: ["constructor", "toString"] };
    p.run("board = normalize(DATA); renderNav();");
    const nav = p.els.nav.innerHTML;
    const icons = ["constructor", "toString"].map((g) => (nav.match(new RegExp('data-view="' + g + '"[^>]*><span class="icon">([^<]*)<')) || [])[1]);
    const maps = p.run("JSON.stringify([GROUP_ICON, NAV_ICON, SET_ICON, RP_ICON].map((m) => [typeof m.constructor, typeof m.toString]))");
    check("W7 groups named constructor and toString get the default icon; the icon maps inherit nothing",
      JSON.stringify(icons) === JSON.stringify(["•", "•"]) && maps === JSON.stringify(Array(4).fill(["undefined", "undefined"])),
      JSON.stringify({ icons, maps }));
  }

  // W8: names equal to built-in JavaScript names are translated as ordinary strings (here the window in English).
  {
    const p = page({ settings: { lang: "en" } });
    p.ctx.DATA = data(undefined, { translations: { en: { "Работа": "Work", "Начат": "Started" } } });
    p.run("board = normalize(DATA);");
    const got = p.run('JSON.stringify([td("Работа"), td("constructor"), td("toString"), trIdea("constructor"), td("Начат toString")])');
    check("W8 data translations: constructor and toString stay as they are",
      got === JSON.stringify(["Work", "constructor", "toString", "constructor", "Started toString"]), got);
  }

  // W9: in the image branch the symbol kept for a missing picture (data-sym) is escaped too.
  {
    const p = page();
    const html = p.run('iconImg("comic", "tech", "<b>")');
    check("W9 symbol escaped in data-sym of an image", html.includes('data-sym="&lt;b&gt;"') && !html.includes("<b>"), html);
  }

  // W10: a group symbol of 4 UTF-16 units is taken, 5 is not ("abcde"; the emoji "👨‍💻" is 5 units).
  {
    const p = page();
    p.ctx.DATA = data({ groups: { Work: { symbol: "abcd" }, "Учёба": { symbol: "abcde" }, "Технологии": { symbol: "👨‍💻" } } });
    p.run("board = normalize(DATA);");
    const got = p.run('JSON.stringify([GROUP_ICON.Work, GROUP_ICON["Учёба"], GROUP_ICON["Технологии"]])');
    check("W10 group symbol: 4 units taken, 5 refused", got === JSON.stringify(["abcd", "◎", "⚙"]), got);
  }

  // XCP-25 B: the HQ sections, their marks, the overview summary card, the arrows on big cards.
  const ans = (id, kind, written, extra) => ({ file: id + ".json", id, error: "", data: Object.assign({ format: "pult-answer", version: 1, kind, written,
    title: { ru: "T", en: "T", he: "T" }, summary: { ru: "S", en: "S", he: "S" } }, extra || {}) });
  const hqPage = (answers, requests, settings) => {
    const p = page({ settings: Object.assign({ lang: "ru" }, settings || {}) });
    Object.assign(p.ctx, { token: "", stamp: (x) => String(x || ""), refresh() {}, showSync() {} });
    p.ctx.DATA = data(undefined, { answers, requests });
    p.run("board = normalize(DATA);");
    return p;
  };
  const navClass = (p, key) => { p.run("renderNav();"); const m = p.els.nav.innerHTML.match(new RegExp('data-view="' + key + '" class="([^"]*)"')); return m ? m[1] : null; };

  // W11: yellow while a request of the section waits; green for an answer not yet opened there; nothing once opened.
  {
    const waiting = hqPage([], [{ id: "request-2026-01-15-090000-summary", kind: "summary", created: "2026-01-15T09:00:00", answered: false }]);
    const fresh = hqPage([ans("request-2026-01-15-090000-summary", "summary", "2026-01-15T09:30")], []);
    const opened = hqPage([ans("request-2026-01-15-090000-summary", "summary", "2026-01-15T09:30")], [],
      { ui: { collapsed: [], summary_hidden: "", seen: { summary: "request-2026-01-15-090000-summary" } } });
    const ideas = hqPage([ans("request-2026-01-15-100000-digest-ideas", "digest-ideas", "2026-01-15T10:30")], []);
    const got = [navClass(waiting, "summary"), navClass(fresh, "summary"), navClass(opened, "summary"), navClass(ideas, "proposals"), navClass(ideas, "summary")];
    check("W11 section marks: wait, new, none once seen; digest-ideas marks Proposals only",
      JSON.stringify(got) === JSON.stringify([" hq-wait", " hq-new", "", " hq-new", ""]), JSON.stringify(got));
  }

  // W12: the overview summary card: the cross hides that summary only; a new summary shows again; the switch hides it for good.
  {
    const today = (p) => p.run("dayKey(today())");
    const mk = (settings, id) => { const p = hqPage([], [], settings); const d = today(p);
      p.ctx.DATA = data(undefined, { answers: [ans(id || "request-x-summary", "summary", d + "T08:00")], requests: [] });
      p.run("board = normalize(DATA); state.view = 'all'; renderHqDay();"); return p.els.hqday; };
    const shown = mk({});
    const hiddenSame = mk({ ui: { collapsed: [], summary_hidden: "request-x-summary", seen: {} } });
    const newOne = mk({ ui: { collapsed: [], summary_hidden: "request-x-summary", seen: {} } }, "request-y-summary");
    const off = mk({ summary_card: "off" });
    check("W12 overview card: cross hides that summary, a new one shows, the switch hides it",
      !shown.hidden && shown.innerHTML.includes('data-ui="hide-summary:request-x-summary"') && hiddenSame.hidden === true
      && !newOne.hidden && newOne.innerHTML.includes("hide-summary:request-y-summary") && off.hidden === true,
      JSON.stringify([shown.hidden, hiddenSame.hidden, newOne.hidden, off.hidden]));
  }

  // W13: «Сводка дня» lists only summaries; «Предложения» shows the other answers, not summaries or digest collections.
  {
    const list = [ans("request-a-summary", "summary", "2026-01-15T09:00"), ans("request-b-proposals", "proposals", "2026-01-15T08:00"),
      ans("request-c-digest-useful", "digest-useful", "2026-01-15T07:00"), ans("request-d-digest-ideas", "digest-ideas", "2026-01-15T06:00")];
    const p = hqPage(list, []);
    p.run("renderSummary();");
    const sum = p.els.ideas.innerHTML;
    p.run("renderProposals();");
    const prop = p.els.ideas.innerHTML;
    const ids = (html) => ["request-a", "request-b", "request-c", "request-d"].filter((k) => html.includes(k));
    const cnt = (html) => (html.match(/class="card pr-card"/g) || []).length;
    check("W13 summary view: summaries only; proposals view: proposals and digest ideas",
      cnt(sum) === 1 && cnt(prop) === 2 && !prop.includes('<span class="pr-kind">Сводка дня</span>'),
      JSON.stringify({ sum: cnt(sum), prop: cnt(prop), ids: ids(prop) }));
  }

  // W14: the key of a folded card: a Latin view name kept, any other name turned into a short Latin hash; always a valid key.
  {
    const p = page();
    const keys = p.run('JSON.stringify([foldView("all"), foldView("Технологии"), foldView("Технологии"), foldView("Учёба"), foldView("A b")])');
    const k = JSON.parse(keys), re = /^[a-z0-9][a-z0-9:_|.-]{0,79}$/;
    check("W14 fold keys: stable, Latin, valid for the program", k[0] === "all" && k[1] === k[2] && k[1] !== k[3] && k.every((x) => re.test(x + ":tiles:0")), keys);
  }

  // XCP-25 C: the «Интересное» and «Полезное» collections and the three digest requests.
  const it = (id, topic) => ({ id, topic, title: "Т " + id, summary: "С " + id, why: "П " + id, url: "https://example.com/" + id, source: "src",
    i18n: { en: { title: "T " + id } } });
  const digests = { ok: true, topics: {}, digests: [
    { date: "2026-01-15", items: [it("a", "t1"), it("b", "t2"), it("c", "t1")],
      marks: { a: { interesting: true, useful: true, at: "2026-01-15 09:00" }, b: { interesting: true, useful: false, at: "" }, c: { interesting: false, useful: false } } },
    { date: "2026-01-01", items: [it("d", "t2")], marks: { d: { interesting: false, useful: true, at: "2026-01-02 10:00" } } },
    { date: "2025-11-01", items: [it("e", "t1")], marks: { e: { interesting: true, useful: false, at: "2025-11-01 08:00" }, ghost: { interesting: true } } }] };
  const dgPage = () => {
    const p = page({ settings: { lang: "ru" }, digests });
    Object.assign(p.ctx, { token: "", stamp: (x) => String(x || ""), refresh() {}, showSync() {} });
    p.ctx.DATA = data(undefined, {});
    p.run("board = normalize(DATA);");
    return p;
  };

  // W15: each collection holds exactly the marked items (an item with both marks in both; a mark without an item ignored);
  // newest first; the period (digest date) and the topic filter apply.
  {
    const p = dgPage();
    const ids = (code) => JSON.parse(p.run("JSON.stringify(" + code + ".map((x) => x.it.id))"));
    const L = "window.BOARD.digests.digests";
    const marks = (k) => digests.digests.reduce((n, d) => n + d.items.filter((i) => d.marks[i.id] && d.marks[i.id][k] === true).length, 0);
    const allI = ids('dgCollect(' + L + ', "interesting", null, "all")'), allU = ids('dgCollect(' + L + ', "useful", null, "all")');
    const rng = '{ from: "2026-01-01", to: "2026-01-15" }';
    const inI = ids('dgCollect(' + L + ', "interesting", ' + rng + ', "all")'), inU = ids('dgCollect(' + L + ', "useful", ' + rng + ', "all")');
    const topic = ids('dgCollect(' + L + ', "interesting", ' + rng + ', "t1")');
    check("W15 collections: counts equal the marks, both marks in both, period and topic filters",
      allI.length === marks("interesting") && allU.length === marks("useful") && JSON.stringify(allI) === '["a","b","e"]' && JSON.stringify(allU) === '["a","d"]'
      && JSON.stringify(inI) === '["a","b"]' && JSON.stringify(inU) === '["a","d"]' && JSON.stringify(topic) === '["a"]',
      JSON.stringify({ allI, allU, inI, inU, topic }));
  }

  // W16: a request snapshot holds the period and only the items marked in it, Russian originals; «ideas» adds the projects.
  {
    const p = dgPage();
    p.run('state.dgPeriod = "custom"; state.dgFrom = "2026-01-01"; state.dgTo = "2026-01-15";');
    const useful = JSON.parse(p.run('JSON.stringify(dgSnapshot("digest-useful", window.BOARD.digests.digests))'));
    const ideas = JSON.parse(p.run('JSON.stringify(dgSnapshot("digest-ideas", window.BOARD.digests.digests))'));
    const inter = JSON.parse(p.run('JSON.stringify(dgSnapshot("digest-interesting", window.BOARD.digests.digests))'));
    p.run('state.dgPeriod = "custom"; state.dgFrom = "2026-02-01"; state.dgTo = "2026-02-28";');
    const none = JSON.parse(p.run('JSON.stringify(dgSnapshot("digest-useful", window.BOARD.digests.digests))'));
    check("W16 snapshot: period, items in it only, originals; ideas add projects; an empty period gives no items",
      useful.period.from === "2026-01-01" && useful.period.to === "2026-01-15" && JSON.stringify(useful.items.map((i) => i.id)) === '["a","d"]'
      && useful.items[0].title === "Т a" && useful.items[0].marks.useful === true && !useful.projects
      && JSON.stringify(inter.items.map((i) => i.id)) === '["a","b"]' && Array.isArray(ideas.projects) && ideas.projects[0].id === "p1"
      && none.items.length === 0, JSON.stringify({ useful: useful.items.map((i) => i.id), inter: inter.items.map((i) => i.id), ideas: ideas.projects }));
  }

  // W17: the collections view shows its count and the request buttons only with the program; the new kinds have names.
  {
    const p = dgPage();
    p.run('state.view = "digest"; state.dgTab = "interesting"; state.dgPeriod = "all"; renderDigest();');
    const html = p.els.digest.innerHTML;
    const names = p.run('JSON.stringify(["digest-interesting", "digest-useful", "digest-ideas", "constructor"].map(prKindName))');
    check("W17 collections view: count, no request buttons without the program; kind names",
      html.includes("Показано: 3") && !html.includes('data-dg="req:') && html.includes('data-dg="tab:useful"')
      && names === JSON.stringify(["Подборка «Интересное»", "Подборка «Полезное»", "Идеи для моих проектов", "Предложения"]), names + " " + html.slice(0, 200));
  }

  // XCP-26: opening a section puts its green mark out (and asks the program to remember); the digest tabs per kind;
  // no translation key that the lookup can never match; a topic without a chip on a tab falls back to all topics.
  {
    const posts = [];
    const p = hqPage([ans("request-a-summary", "summary", "2026-01-15T09:00")], []);
    Object.assign(p.ctx, { token: "t", fetch: (url) => { posts.push(url); return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }); } });
    const before = navClass(p, "summary");
    p.run("renderSummary();");
    const after = navClass(p, "summary");
    const d = page({ settings: { lang: "ru" }, digests, answers: [] });
    Object.assign(d.ctx, { token: "", stamp: (x) => String(x || ""), refresh() {}, showSync() {} });
    d.ctx.DATA = data(undefined, { answers: [ans("request-u-digest-useful", "digest-useful", "2026-01-15T10:00"),
      ans("request-i-digest-interesting", "digest-interesting", "2026-01-15T09:00")], requests: [] });
    d.run("board = normalize(DATA); state.view = 'digest'; state.dgTab = 'interesting'; renderDigest();");
    const afterInteresting = navClass(d, "digest");
    d.run("state.dgTab = 'useful'; renderDigest();");
    const afterUseful = navClass(d, "digest");
    check("W18 opening a section puts out its mark and posts it; digest tabs per kind",
      before === " hq-new" && after.indexOf("hq-new") < 0 && posts.length === 1 && posts[0] === "/ui?op=seen&section=summary&id=request-a-summary"
      && afterInteresting.indexOf("hq-new") >= 0 && afterUseful.indexOf("hq-new") < 0, JSON.stringify({ before, after, posts, afterInteresting, afterUseful }));
  }
  {
    const p = page();
    const ctx = { window: {} };
    vm.createContext(ctx);
    vm.runInContext(fs.readFileSync(path.join(ROOT, "i18n.js"), "utf8"), ctx);
    const dict = ctx.window.PULT_I18N;
    const bad = ["en", "he"].flatMap((l) => Object.keys(dict[l]).filter((k) => p.run("CORE_RE.exec(" + JSON.stringify(k) + ")[2]") !== k).map((k) => l + ": " + k));
    const en = page({ settings: { lang: "en" } }, true);
    const names = en.run('JSON.stringify([prKindName("digest-interesting"), prKindName("digest-useful"), tl("Напишите в чате штаба: «разбери запрос». Сводка появится в разделе «Сводка дня».")])');
    // XCP-33: no English or Hebrew translation keeps a Russian word (the request phrase was «разбери запрос»).
    const cyr = ["en", "he"].flatMap((l) => Object.entries(dict[l]).filter(([, v]) => /[а-яё]/i.test(v)).map(([k]) => l + ": " + k));
    check("W19 no translation key with edge characters; no Russian letter in an English or Hebrew translation; the kind names and the toast are translated",
      bad.length === 0 && cyr.length === 0 && !/[а-яё]/i.test(names), JSON.stringify(bad.slice(0, 5)) + " " + JSON.stringify(cyr.slice(0, 5)) + " " + names);
  }
  {
    const p = dgPage();
    p.run('state.view = "digest"; state.dgTab = "useful"; state.dgPeriod = "all"; state.dgTopic = "t2"; renderDigest();');
    p.run('state.dgTab = "interesting"; state.dgPeriod = "custom"; state.dgFrom = "2026-01-15"; state.dgTo = "2026-01-15"; state.dgTopic = "t9"; renderDigest();');
    const html = p.els.digest.innerHTML, topic = p.run("state.dgTopic");
    check("W20 a topic without a chip on the tab falls back to all topics", topic === "all" && html.includes("Показано: 2"), topic + " " + (html.match(/Показано: \d+/) || [""])[0]);
  }

  // XCP-27: «Предложения» puts out its own mark and posts it once; each digest tab posts its own kind once;
  // the lookup is per kind (a newer «Полезное» answer is not hidden by an «Интересное» one already opened).
  {
    const posts = [];
    const fetchStub = (url) => { posts.push(url); return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }); };
    const p = hqPage([ans("request-p-proposals", "proposals", "2026-01-15T09:00")], []);
    Object.assign(p.ctx, { token: "t", fetch: fetchStub });
    const before = navClass(p, "proposals");
    p.run("renderProposals(); renderProposals();");
    const after = navClass(p, "proposals");
    const d = page({ settings: { lang: "ru" }, digests, answers: [] });
    Object.assign(d.ctx, { token: "t", fetch: fetchStub, stamp: (x) => String(x || ""), refresh() {}, showSync() {} });
    d.ctx.DATA = data(undefined, { answers: [ans("request-u-digest-useful", "digest-useful", "2026-01-15T10:00"),
      ans("request-i-digest-interesting", "digest-interesting", "2026-01-15T09:00")], requests: [] });
    d.run("board = normalize(DATA); state.view = 'digest'; state.dgTab = 'interesting'; renderDigest(); renderDigest();" +
      " state.dgTab = 'useful'; renderDigest(); renderDigest();");
    const want = ["/ui?op=seen&section=proposals&id=request-p-proposals", "/ui?op=seen&section=digest-interesting&id=request-i-digest-interesting",
      "/ui?op=seen&section=digest-useful&id=request-u-digest-useful"];
    check("W21 «Предложения» and each digest tab put out their own mark and post their own kind, once",
      before === " hq-new" && after.indexOf("hq-new") < 0 && JSON.stringify(posts) === JSON.stringify(want), JSON.stringify({ before, after, posts }));
  }
  {
    const seen = { collapsed: [], summary_hidden: "", seen: { "digest-interesting": "request-i-digest-interesting" } };
    const d = page({ settings: { lang: "ru", ui: seen }, digests, answers: [] });
    Object.assign(d.ctx, { token: "", stamp: (x) => String(x || ""), refresh() {}, showSync() {} });
    d.ctx.DATA = data(undefined, { answers: [ans("request-u-digest-useful", "digest-useful", "2026-01-15T10:00"),
      ans("request-i-digest-interesting", "digest-interesting", "2026-01-15T09:00")], requests: [] });
    d.run("board = normalize(DATA);");
    const before = navClass(d, "digest");
    d.run("state.view = 'digest'; state.dgTab = 'useful'; renderDigest();");
    const after = navClass(d, "digest");
    check("W22 the digest marks are looked up per kind: opening «Полезное» puts the mark out when «Интересное» was opened",
      before.indexOf("hq-new") >= 0 && after.indexOf("hq-new") < 0, JSON.stringify({ before, after }));
  }
  // XCP-27: the update's refusals are shown in the window's language and name the files in the way; an unknown code
  // shows the program's text as it is, with no file list.
  {
    const got = ["en", "he"].map((lang) => page({ settings: { lang } }, true).run('typeof updRefusal !== "function" ? "null" : JSON.stringify([' +
      'updRefusal({ ok: false, code: "incoming-over-files", error: "обновление …", files: ["notes", "<b>x</b>"] }),' +
      'updRefusal({ ok: false, code: "local-changes", error: "в файлах …", files: ["app.py"] }),' +
      'updRefusal({ ok: false, code: "constructor", error: "git: boom", files: ["x"] }), updRefusal({ ok: false }),' +
      'updRefusal({ ok: false, code: "state", state: "current" }), updRefusal({ ok: false, code: "state", state: "unavailable", detail: "git не найден" }),' +
      'updRefusal({ ok: false, code: "state", state: "off" }), updRefusal({ ok: false, code: "update-failed", detail: "fatal: x" }),' +
      'updRefusal({ ok: false, code: "state", state: "constructor", error: "raw" })])'));
    const parsed = got.map((s) => JSON.parse(s));
    const ok = parsed.every((r) => r && !/[а-яё]/i.test(r[0].msg + r[1].msg + r[3].msg) && r[0].msg && r[1].msg
      && JSON.stringify(r[0].files) === JSON.stringify(["notes", "<b>x</b>"]) && JSON.stringify(r[1].files) === JSON.stringify(["app.py"])
      && r[2].msg === "git: boom" && r[2].files.length === 0 && r[3].files.length === 0
      && !/[а-яё]/i.test(r[4].msg + r[6].msg) && r[4].msg && r[6].msg && r[5].msg.endsWith(": git не найден") && !/[а-яё]/i.test(r[5].msg.replace(": git не найден", ""))
      && r[7].msg.endsWith(": fatal: x") && !/[а-яё]/i.test(r[7].msg) && r[8].msg === "raw");
    check("W23 update answers translated (en, he), files named, git's text kept as data; an unknown code shown as is", ok, JSON.stringify(parsed));
  }

  // XCP-28: the menu read as the program draws it (no extra redraw by the check); opening one section puts out only its
  // own mark (an unopened summary keeps its mark) and posts once; a newer answer after an opened one lights the mark again.
  const navNow = (p, key) => { const m = p.els.nav.innerHTML.match(new RegExp('data-view="' + key + '" class="([^"]*)"')); return m ? m[1] : null; };
  {
    const posts = [];
    const fetchStub = (url) => { posts.push(url); return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }); };
    const p = hqPage([ans("request-p-proposals", "proposals", "2026-01-15T09:00"), ans("request-s-summary", "summary", "2026-01-15T08:00")], []);
    Object.assign(p.ctx, { token: "t", fetch: fetchStub });
    p.run("renderNav();");
    const before = [navNow(p, "proposals"), navNow(p, "summary")];
    p.run("renderProposals();");
    const after = [navNow(p, "proposals"), navNow(p, "summary")];
    const d = page({ settings: { lang: "ru" }, digests, answers: [] });
    Object.assign(d.ctx, { token: "t", fetch: fetchStub, stamp: (x) => String(x || ""), refresh() {}, showSync() {} });
    d.ctx.DATA = data(undefined, { answers: [ans("request-u-digest-useful", "digest-useful", "2026-01-15T10:00"),
      ans("request-s2-summary", "summary", "2026-01-15T08:00")], requests: [] });
    d.run("board = normalize(DATA); renderNav(); state.view = 'digest'; state.dgTab = 'useful'; renderDigest();");
    const dAfter = [navNow(d, "digest"), navNow(d, "summary")];
    check("W24 opening a section puts out only its own mark at once, an unopened summary keeps its mark, one POST each",
      before[0].indexOf("hq-new") >= 0 && before[1].indexOf("hq-new") >= 0 && after[0].indexOf("hq-new") < 0 && after[1].indexOf("hq-new") >= 0
      && dAfter[0].indexOf("hq-new") < 0 && dAfter[1].indexOf("hq-new") >= 0
      && JSON.stringify(posts) === JSON.stringify(["/ui?op=seen&section=proposals&id=request-p-proposals", "/ui?op=seen&section=digest-useful&id=request-u-digest-useful"]),
      JSON.stringify({ before, after, dAfter, posts }));
  }
  {
    const posts = [];
    const p = hqPage([ans("request-s2-summary", "summary", "2026-01-15T10:00"), ans("request-s1-summary", "summary", "2026-01-14T10:00")], [],
      { ui: { collapsed: [], summary_hidden: "", seen: { summary: "request-s1-summary" } } });
    Object.assign(p.ctx, { token: "t", fetch: (url) => { posts.push(url); return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }); } });
    const before = navClass(p, "summary");
    p.run("renderSummary();");
    const after = navNow(p, "summary");
    check("W25 a newer answer after an opened one lights the mark again; opening remembers the newer one",
      before.indexOf("hq-new") >= 0 && after.indexOf("hq-new") < 0 && JSON.stringify(posts) === JSON.stringify(["/ui?op=seen&section=summary&id=request-s2-summary"]),
      JSON.stringify({ before, after, posts }));
  }

  console.log("\nPassed " + PASSED.length + ", failed " + FAILED.length + (FAILED.length ? ": " + FAILED.join(", ") : ""));
  return FAILED.length ? 1 : 0;
}

process.exitCode = main();
