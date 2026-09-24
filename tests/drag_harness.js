// The drag's executed twin (specs/28 §3.2; the review's harness, kept): a
// fake DOM faithful where wireDrag is fragile — connectedness, pointer
// capture LOST when its target leaves the document (lostpointercapture at
// the document, later events hit-tested instead), capture/bubble dispatch,
// a rAF queue, scroll offsets that move the rects, computed overflow.
// Run by tests/test_web_desk.py with APPJS pointing at the reader.
"use strict";
const fs = require("fs");
const JS = fs.readFileSync(process.env.APPJS, "utf8");
const lift = re => { const m = JS.match(re); if (!m) throw new Error("not found: " + re); return m[0]; };
const SRC = [
  lift(/  const clipKey = .+?;\n/),
  lift(/  function trayMove\(from, to, origin, key\) \{[\s\S]+?\n  \}/),
  lift(/  const dgSlot = .+?;\n/),
  lift(/  let DG = .+?\n/),
  lift(/  function wireDrag\(list, rowSel, onMove\) \{[\s\S]+?\n  \}\n/),
].join("\n");

function makeWorld() {
  const W = { scrollY: 0, docHeight: 5000, innerHeight: 800, rafQ: [], rafId: 0, rafRuns: 0, winScrolls: 0, capture: {} };
  class El {
    constructor(tag, cls) {
      this.tag = tag; this.cls = new Set((cls || "").split(" ").filter(Boolean)); this.attrs = {};
      this.kids = []; this.parent = null; this.L = { cap: {}, bub: {} }; this.style = {}; this.hidden = false;
      this.y0 = 0; this.h = 0; this.scrollTop = 0; this.clientHeight = 0; this.scrollHeight = 0;
      this.nodeType = 1; this.fixed = false; this.scroller = false;
      const self = this;
      this.classList = { add: c => self.cls.add(c), remove: c => self.cls.delete(c), contains: c => self.cls.has(c) };
    }
    set className(v) { this.cls = new Set(String(v).split(" ").filter(Boolean)); }
    get className() { return [...this.cls].join(" "); }
    get parentElement() { return this.parent; }
    get isConnected() { let e = this; while (e) { if (e === DOCEL) return true; e = e.parent; } return false; }
    appendChild(k) { if (k.parent) k.remove(); this.kids.push(k); k.parent = this; return k; }
    remove() { if (this.parent) { this.parent.kids = this.parent.kids.filter(k => k !== this); this.parent = null; } }
    contains(el) { for (let e = el; e; e = e.parent) if (e === this) return true; return false; }
    matches(sel) {
      if (sel.startsWith("[")) return Object.prototype.hasOwnProperty.call(this.attrs, sel.slice(1, -1));
      if (sel.startsWith(".")) return this.cls.has(sel.slice(1));
      return this.tag === sel;
    }
    closest(sel) { for (let e = this; e && e !== DOCEL; e = e.parent) if (e.matches(sel)) return e; return null; }
    addEventListener(t, f, c) { const b = c === true || (c && c.capture) ? this.L.cap : this.L.bub; (b[t] ||= []).push(f); }
    removeEventListener(t, f, c) { const b = c === true || (c && c.capture) ? this.L.cap : this.L.bub; b[t] = (b[t] || []).filter(x => x !== f); }
    setPointerCapture(id) { if (!this.isConnected) throw new Error("InvalidStateError"); W.capture[id] = this; }
    getBoundingClientRect() {
      if (!this.isConnected) return { top: 0, bottom: 0, height: 0 };
      let top = this.y0;
      for (let p = this.parent; p && p !== DOCEL; p = p.parent) top += p.y0 - (p.scroller ? p.scrollTop : 0);
      top -= W.scrollY;
      return { top, bottom: top + this.h, height: this.h };
    }
    scrollBy(x, y) { if (this.isConnected) this.scrollTop = Math.max(0, Math.min(this.scrollHeight - this.clientHeight, this.scrollTop + y)); }
  }
  const DOCEL = new El("html");
  DOCEL.parent = null;
  const BODY = DOCEL.appendChild(new El("body"));
  const document = { createElement: t => new El(t),
    addEventListener: (t, f, c) => DOCEL.addEventListener(t, f, c), removeEventListener: (t, f, c) => DOCEL.removeEventListener(t, f, c) };
  function dispatch(target, type, ev) {
    ev.type = type; ev.target = target; ev.defaultPrevented = false; let stopped = false;
    ev.preventDefault = () => { ev.defaultPrevented = true; };
    ev.stopPropagation = () => { stopped = true; };
    const path = []; for (let e = target; e; e = e.parent) path.push(e);
    for (const e of path.slice().reverse()) { for (const f of (e.L.cap[type] || []).slice()) f(ev); if (stopped) return ev; }
    for (const e of path) { for (const f of (e.L.bub[type] || []).slice()) f(ev); if (stopped) return ev; }
    return ev;
  }
  function pointer(type, ev, hit) {
    const id = ev.pointerId;
    let t = W.capture[id];
    if (t && !t.isConnected) { delete W.capture[id]; dispatch(DOCEL, "lostpointercapture", { pointerId: id }); t = null; }
    const out = dispatch(t || hit || BODY, type, ev);
    if (type === "pointerup" || type === "pointercancel") delete W.capture[id];
    return out;
  }
  return { document, El, DOCEL, BODY, W, dispatch, pointer,
    getComputedStyle: el => ({ overflowY: el.scroller ? "auto" : "visible", position: el.fixed ? "fixed" : "static" }),
    requestAnimationFrame: cb => { W.rafQ.push({ id: ++W.rafId, cb }); return W.rafId; },
    cancelAnimationFrame: id => { W.rafQ = W.rafQ.filter(x => x.id !== id); },
    scrollBy: (x, y) => { W.winScrolls++; W.scrollY = Math.max(0, Math.min(W.docHeight - W.innerHeight, W.scrollY + y)); },
    frame(n) { for (let i = 0; i < (n || 1); i++) { const q = W.rafQ; W.rafQ = []; for (const x of q) { W.rafRuns++; x.cb(); } } } };
}
// a tray: a persistent holder whose list is REPLACED on every paint, as
// buildTray / refreshReelSummary replace theirs
function makeTray(rt, spec) {
  const { El, BODY } = rt;
  const holder = BODY.appendChild(new El("section"));
  holder.y0 = spec.listDocTop; holder.fixed = !!spec.fixed;
  const T = { holder, list: null, rows: [] };
  T.paint = n => {
    if (T.list) T.list.remove();
    const list = holder.appendChild(new El("div", spec.listCls));
    const rows = []; let y = 0;
    for (let i = 0; i < n; i++) {
      const row = list.appendChild(new El("div", spec.rowCls));
      row.y0 = y; row.h = spec.rowH;
      const grip = row.appendChild(new El("div", spec.gripCls));
      if (n > 1) { grip.attrs["data-grip"] = ""; row.glyph = grip.appendChild(new El("span", "dg-grip")); }
      grip.y0 = spec.gripOff; grip.h = 30;
      row.grip = grip; rows.push(row); y += spec.rowH + spec.gap;
    }
    list.scrollHeight = Math.max(0, y - spec.gap);
    if (spec.maxH && list.scrollHeight > spec.maxH) { list.scroller = true; list.clientHeight = spec.maxH; }
    else { list.scroller = false; list.clientHeight = list.scrollHeight; }
    list.h = list.clientHeight;
    T.list = list; T.rows = rows;
  };
  return T;
}
function boot(rt, tray, clips) {
  const env = { CLIPS: clips.slice(), MOVES: [], TOASTS: [], WRITES: [] };
  const $$ = (sel, root) => (root.kids || []).filter(k => k.matches(sel));
  const trayClips = () => env.CLIPS.map(c => ({ ...c }));
  const toast = m => env.TOASTS.push(m);
  let rowSel = null;
  const writeTray = (c, focus, origin) => { env.CLIPS = c; env.WRITES.push({ order: c.map(x => x.pid), focus, origin }); repaint(); };
  const WIN = { L: {} };
  const winAdd = (t, f) => { (WIN.L[t] ||= []).push(f); }, winRemove = (t, f) => { WIN.L[t] = (WIN.L[t] || []).filter(x => x !== f); };
  rt.blur = () => { for (const f of (WIN.L.blur || []).slice()) f({ type: "blur" }); };
  const f = new Function("document", "requestAnimationFrame", "cancelAnimationFrame", "innerHeight", "scrollBy", "getComputedStyle",
    "$$", "trayClips", "toast", "writeTray", "r1", "addEventListener", "removeEventListener",
    SRC + "\nreturn { clipKey, trayMove, dgSlot, wireDrag };");
  const api = f(rt.document, rt.requestAnimationFrame, rt.cancelAnimationFrame, rt.W.innerHeight, rt.scrollBy, rt.getComputedStyle,
    $$, trayClips, toast, writeTray, x => Math.round(x * 10) / 10, winAdd, winRemove);
  function repaint() {
    tray.paint(env.CLIPS.length);
    api.wireDrag(tray.list, rowSel, (from, to, key) => { env.MOVES.push([from, to, key]); api.trayMove(from, to, "tray", key); });
  }
  env.start = sel => { rowSel = sel; repaint(); };
  env.repaint = repaint;
  return env;
}

const mk = p => ({ pid: p, kind: "hit", t: 1 });
const MEETING = { listCls: "rt-clips", rowCls: "rt-clip", gripCls: "rt-ord", rowH: 98, gap: 8, gripOff: 8, listDocTop: 1200 };
const PANEL = { listCls: "cz-rclips", rowCls: "cz-rclip", gripCls: "cz-rord", rowH: 147, gap: 8, gripOff: 10, listDocTop: 300, maxH: 352 };
const setup = (spec, n, sel) => { const rt = makeWorld(); const tray = makeTray(rt, spec);
  const env = boot(rt, tray, typeof n === "number" ? Array.from({ length: n }, (_, i) => mk("abcdefgh"[i])) : n); env.start(sel);
  return { rt, tray, env }; };
const down = (rt, g, extra) => rt.pointer("pointerdown", { pointerId: 1, pointerType: "mouse", button: 0, buttons: 1, isPrimary: true,
  clientY: g.getBoundingClientRect().top + 5, ...(extra || {}) }, g);
const out = {};

// a plain drag: the first clip to the end, committed once, focus quiet
{ const { rt, tray, env } = setup(MEETING, 3, ".rt-clip"); rt.W.scrollY = 1100;
  down(rt, tray.rows[0].grip);
  rt.pointer("pointermove", { pointerId: 1, pointerType: "mouse", buttons: 1, clientY: 330 });
  rt.pointer("pointerup", { pointerId: 1, clientY: 330 });
  out.plain = { order: env.CLIPS.map(c => c.pid).join(""), writes: env.WRITES, toast: env.TOASTS[0], raf: rt.W.rafQ.length,
    listeners: Object.values(rt.DOCEL.L.cap).reduce((n, a) => n + a.length, 0) }; }
// a repaint mid-drag ends the drag: nothing runs on, nothing is dropped
{ const { rt, tray, env } = setup(MEETING, 5, ".rt-clip"); rt.W.scrollY = 800;
  const g = tray.rows[3].grip;
  down(rt, g, { pointerType: "touch" });
  rt.pointer("pointermove", { pointerId: 1, pointerType: "touch", clientY: 785 }); rt.frame(3);
  env.repaint();
  rt.pointer("pointermove", { pointerId: 1, pointerType: "touch", clientY: 500 });
  rt.pointer("pointerup", { pointerId: 1, clientY: 500 });
  const s0 = rt.W.winScrolls; rt.frame(600);
  const esc = rt.dispatch(rt.BODY, "keydown", { key: "Escape" });
  out.repaint = { moves: env.MOVES.length, raf: rt.W.rafQ.length, scrolls: rt.W.winScrolls - s0,
    keyListeners: (rt.DOCEL.L.cap.keydown || []).length, laterEscapePrevented: esc.defaultPrevented }; }
// a press that never moves, held at an edge, moves nothing
{ const res = [];
  for (const fr of [10, 30, 90]) { const { rt, tray, env } = setup(MEETING, 6, ".rt-clip"); rt.W.scrollY = 1200 + 212 - 780;
    const g = tray.rows[2].grip; const y = g.getBoundingClientRect().top + 5; down(rt, g); rt.frame(fr);
    rt.pointer("pointerup", { pointerId: 1, clientY: y }); res.push(env.MOVES.length + ":" + env.CLIPS.map(c => c.pid).join("")); }
  out.stillPress = res; }
// the panel's slot-0 line never sits above the list's top
{ const { rt, tray, env } = setup(PANEL, 3, ".cz-rclip");
  down(rt, tray.rows[1].grip); const lr = tray.list.getBoundingClientRect();
  rt.pointer("pointermove", { pointerId: 1, pointerType: "mouse", buttons: 1, clientY: lr.top + 20 });
  const line = tray.list.kids.find(k => k.cls.has("dg-line"));
  out.slot0 = { top: line.style.top, hidden: line.hidden };
  rt.pointer("pointerup", { pointerId: 1, clientY: lr.top + 20 }); out.slot0.order = env.CLIPS.map(c => c.pid).join(""); }
// a second finger is not a second drag
{ const { rt, tray, env } = setup(MEETING, 4, ".rt-clip"); rt.W.scrollY = 1100;
  const g0 = tray.rows[0].grip, g2 = tray.rows[2].grip;
  rt.pointer("pointerdown", { pointerId: 1, pointerType: "touch", button: 0, isPrimary: true, clientY: g0.getBoundingClientRect().top + 5 }, tray.rows[0].glyph);
  rt.pointer("pointerdown", { pointerId: 2, pointerType: "touch", button: 0, isPrimary: false, clientY: g2.getBoundingClientRect().top + 5 }, tray.rows[2].glyph);
  const lines = tray.list.kids.filter(k => k.cls.has("dg-line")).length, lifted = tray.rows.filter(r => r.cls.has("dg-lift")).length;
  rt.pointer("pointermove", { pointerId: 2, pointerType: "touch", clientY: 790 });
  rt.pointer("pointermove", { pointerId: 1, pointerType: "touch", clientY: 300 });
  rt.pointer("pointerup", { pointerId: 1, clientY: 300 }); rt.pointer("pointerup", { pointerId: 2, clientY: 790 });
  const s0 = rt.W.winScrolls; rt.frame(300);
  out.twoFingers = { lines, lifted, moves: env.MOVES.length, raf: rt.W.rafQ.length, scrolls: rt.W.winScrolls - s0 }; }
// only the primary button of a mouse or pen lifts a clip; a Mac's ctrl-click is a right click
{ const res = {};
  for (const [name, ev] of [["penBarrel", { pointerType: "pen", button: 2 }], ["penEraser", { pointerType: "pen", button: 5 }],
                            ["ctrlClick", { pointerType: "mouse", button: 0, ctrlKey: true }], ["right", { pointerType: "mouse", button: 2 }],
                            ["pen", { pointerType: "pen", button: 0 }]]) {
    const { rt, tray } = setup(MEETING, 3, ".rt-clip"); down(rt, tray.rows[0].grip, ev);
    res[name] = tray.rows[0].cls.has("dg-lift") ? "drag" : "ignored"; }
  out.buttons = res; }
// Escape cancels the drag and is the drag's alone
{ const { rt, tray } = setup(MEETING, 3, ".rt-clip");
  const input = rt.BODY.appendChild(new rt.El("input")); let other = false;
  input.addEventListener("keydown", e => { if (e.key === "Escape") other = true; });
  down(rt, tray.rows[0].grip);
  const ev = rt.dispatch(input, "keydown", { key: "Escape" });
  out.escape = { cancelled: !tray.rows[0].cls.has("dg-lift"), otherRan: other, prevented: ev.defaultPrevented }; }
// a duplicate identity moves the copy that was lifted
{ const A = { pid: "m", kind: "cut", t: 10, tag: "A" }, B = { pid: "m", kind: "cut", t: 30, tag: "B" }, A2 = { pid: "m", kind: "cut", t: 10, tag: "A'" };
  const { rt, tray, env } = setup(MEETING, [A, B, A2], ".rt-clip"); rt.W.scrollY = 1100;
  down(rt, tray.rows[2].grip); const r1 = tray.rows[1].getBoundingClientRect();
  rt.pointer("pointermove", { pointerId: 1, pointerType: "mouse", buttons: 1, clientY: r1.top + 10 });
  rt.pointer("pointerup", { pointerId: 1, clientY: r1.top + 10 });
  out.duplicates = env.CLIPS.map(c => c.tag).join(" "); }
// a release the page never saw: the next press anywhere ends the drag; so does a blur
{ const { rt, tray, env } = setup(MEETING, 4, ".rt-clip"); rt.W.scrollY = 1100;
  down(rt, tray.rows[0].grip); rt.pointer("pointermove", { pointerId: 1, pointerType: "mouse", buttons: 1, clientY: 380 });
  delete rt.W.capture[1];
  const other = rt.BODY.appendChild(new rt.El("button"));
  rt.pointer("pointerdown", { pointerId: 1, pointerType: "mouse", button: 0, buttons: 1, isPrimary: true, clientY: 600 }, other);
  rt.pointer("pointerup", { pointerId: 1, pointerType: "mouse", buttons: 0, clientY: 600 }, other);
  const r0 = rt.W.rafRuns; rt.frame(60);
  out.lostRelease = { moves: env.MOVES.length, raf: rt.W.rafRuns - r0, lifted: tray.rows.filter(r => r.cls.has("dg-lift")).length }; }
{ const { rt, tray } = setup(MEETING, 4, ".rt-clip"); rt.W.scrollY = 1100;
  down(rt, tray.rows[0].grip); rt.pointer("pointermove", { pointerId: 1, pointerType: "mouse", buttons: 1, clientY: 380 });
  rt.blur(); const r0 = rt.W.rafRuns; rt.frame(60);
  out.blur = { raf: rt.W.rafRuns - r0, lifted: tray.rows.filter(r => r.cls.has("dg-lift")).length }; }
// a finger on a row's number scrolls the page; only the ⠿ lifts the clip
{ const a = setup(MEETING, 3, ".rt-clip");
  a.rt.pointer("pointerdown", { pointerId: 1, pointerType: "touch", button: 0, isPrimary: true, clientY: 0 }, a.tray.rows[0].grip);
  const b = setup(MEETING, 3, ".rt-clip");
  b.rt.pointer("pointerdown", { pointerId: 1, pointerType: "touch", button: 0, isPrimary: true, clientY: 0 }, b.tray.rows[0].glyph);
  out.touch = { number: a.tray.rows[0].cls.has("dg-lift") ? "drag" : "scrolls", glyph: b.tray.rows[0].cls.has("dg-lift") ? "drag" : "scrolls" }; }
// a list that does not scroll inside a fixed sidebar: the page behind it never scrolls
{ const { rt, tray } = setup({ ...PANEL, fixed: true, maxH: 0 }, 2, ".cz-rclip");
  down(rt, tray.rows[0].grip);
  rt.pointer("pointermove", { pointerId: 1, pointerType: "mouse", buttons: 1, clientY: 795 });
  const s0 = rt.W.winScrolls; rt.frame(30);
  out.fixed = { scrolls: rt.W.winScrolls - s0 };
  rt.pointer("pointerup", { pointerId: 1, clientY: 795 }); }
console.log(JSON.stringify(out));
