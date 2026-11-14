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
function page(board) {
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

  console.log("\nPassed " + PASSED.length + ", failed " + FAILED.length + (FAILED.length ? ": " + FAILED.join(", ") : ""));
  return FAILED.length ? 1 : 0;
}

process.exitCode = main();
