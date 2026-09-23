# 23 — The open newsroom: the making half, visible and powerful

**Status:** v0.2 · **Stage:** **Phase A SHIPPED + LIVE (v2.1.11 / r33,
2026-09-23)** — the front door, ＋ your paper on the cards, the on-page
editor, the teaching draft; SETTLED (Stephen, 2026-09-23 — all four scope
answers on the record below); **Phase B (the cutting room) is next.** ·
**Owner:**
Stephen Walter (Weird Machine) · **Related:** specs/20 (the reader + reels),
specs/21 (the studio + your paper, shipped whole), specs/22 (the cutting
room, settled 2026-07-22, partial in control-z's tree), `CLAUDE.md` (the
laws), `record/OPERATING.md` (deploy).

## 1. Problem — the product's second half is invisible

Verified live 2026-09-23 (v2.1.10, headless walk of the front page): a
visitor sees a complete, beautiful READER — and the entire making half is
one corner pill ("Enter the studio →") plus one quiet `.featline` sentence.
Stephen, the owner, could not find the way to customize a front page.
specs/21 §1 named this exact failure ("the interactivity is the key
feature, and it's hidden") and P0 answered with a compact pill; the volume
law protected the reading so thoroughly it buried the making. Nothing is
broken — everything is undiscoverable.

## 2. Resolved with Stephen (2026-09-23) — build to these

1. **The front door**: a REAL front-page section for the making half —
   benefit copy, a Start button, template starts, the featured papers grown
   from one line into cards — plus visible make-affordances on meeting and
   issue cards in preview/studio modes. **Home stays the record's front
   page** (paper-as-homepage was offered and NOT taken).
2. **The editor**: `/app/p` in studio mode becomes a true on-page editor
   for YOUR DRAFT — arrange on the paper itself, not only in the sidebar.
3. **The rich tier — all four**: layout power, multiple papers, richer
   blocks, print/PDF.
4. **Sequence**: A (this spec's front door + editor) → B (the cutting
   room, specs/22) → C (the rich tier) → D (openness mechanics + the
   record grows). One deploy per phase; tags advance one per deploy
   (A targets v2.1.11/r33).

## 3. Bounds — the laws still hold, precisely

- **Volume**: the INVITATION lives on preview/studio surfaces and the
  record's own baked prose (paper palette, deep green, benefit-forward —
  a skeptical 70-year-old should trust it). Paper mode and every RENDERED
  paper stay exactly as quiet as today. Zero fuchsia, ever.
- **Byte-clean**: pressed pages carry NO studio chrome. The front-page
  section is baked CONTENT (the record inviting, like the covenant line —
  new namespace, grep the sheet first; `cz-`, `pb-`, `rt-`, `pf-`,
  `.featline`, `cz-tpl*` are taken). Card affordances are SCRIPT-ADDED in
  preview/studio modes only — never in the baked HTML, never in paper mode
  (extend the byte-clean guard to prove it).
- **Covenant**: composing stays client-only. The editor's add-search reads
  the record's own static index — no new API doors (the door-count guard
  stays at its number).
- **Store strictness**: free text stored remains title + notes ONLY. Every
  Phase C schema extension is refs-and-enums by design (see §4C); anything
  that would store new free text needs Stephen's explicit sign-off first.
- **A11y floor**: every pointer affordance keeps a keyboard path (the
  panel's ↑↓✕ remain; drag handles get aria); focus never lands on a
  destructive control; painted-truth rule for any stateful control.

## 4. Phasing

**A — the front door + the real editor (v2.1.11/r33). ✓ SHIPPED + LIVE 2026-09-23** — as specified below, plus a fold of 23 + 3 review findings (CHANGELOG).
- A1 Front-page section (baked, in `web/emit.py page_home`): kicker
  ("YOUR PAPER — BE THE EDITOR" register), two sentences of benefit copy
  ("the record is raw material… no account, lives in your browser"), a
  primary **Start your paper** button → `/app/p#edit`, template starts
  (surface the P3 templates as links the editor reads from the hash), and
  the featured-papers row grown from `.featline` into 2–3 quiet cards
  (the `pf-` press-time machinery already exists).
- A2 Make-affordances on cards: app.js decorates meeting/issue cards
  (home, officials, issue pages) with a small "＋ your paper" (and, after
  Phase B, "✂ cut") affordance in preview+studio modes. Generalize
  `addPageToPaper` → `addStoryRef(ref)` so a card can add without
  navigation. Never painted in paper mode; never baked.
- A3 The on-page editor (`/app/p`, studio mode, DRAFT ONLY — shared/stored
  papers stay read-only; make-this-yours arrives with specs/22): drag
  handles per block (HTML5 DnD; keyboard path = the existing panel
  controls + handle aria), per-block ✕, the title editable in place, an
  insertion-point "＋ add" opening an INLINE lexical search over the
  static index (meetings + issues; the tray remains the reel source).
  Draft edits re-render live (the debounce machinery exists).
- A4 First-run: the empty draft at `/app/p#edit` becomes a teaching
  surface — three big starts (the templates + "browse the record");
  the pill's verb changes from "Enter the studio" to the thing itself
  ("✎ Your paper — edit"; update the pinned copy tests).
- Tests: bake (section present; affordance classes ABSENT from pressed
  HTML; palette guard; JS-off honest), the studio covenant scans stay
  green, editor markers pinned, node twins untouched (A changes no codec).

**B — the cutting room (specs/22 P0 → its own deploy; then B2 the scoped
preview stage).** Per the five settled answers (2026-07-22): all three
cutting surfaces (transcript rows, search hits, issue beads), ONE tray +
file-into-paper, append-or-replace explicit on `/app/r` make-this-yours,
segment-snapped trim with cross-page bounds from the clip's meeting
`transcript.txt`, new-tab preview now / scoped stage as B2. **Triage the
~531-line uncommitted partial in `~/control-z` first** (read via
`git -C ~/control-z diff`): port what survives reading into THIS repo as
your own work; never commit it blind; after the port ships, ask Stephen
whether to discard the control-z copy.

**C — the rich tier (two deploys).**
- C1 **Multiple papers + layout power**: named drafts (`cz-papers` map +
  an active pointer; migrate the single `cz-paper` draft once, the
  loadReel-migration pattern); per-block layout as ENUMS (lead story,
  section header, half-width pair) carried in the doc, the link, the
  export, and the store (schema extension: enums only, strict refusal of
  unknown values; version the codec by `paperV`'s rule and keep old links
  reading). Templates gain layout.
- C2 **Richer blocks + print**: pull-quote block (a transcript line by
  `(pid, t)` — the TEXT is fetched from the plane at render, never
  stored: refs only), document block (agenda/minutes refs from the
  meeting plane), "what changed" digest block (an issue ref + a window,
  computed at render). Each extends `record/papers.py::_block` with the
  same strictness (exact keys, refs only). Print stylesheet: `@media
  print` makes a rendered paper a real printable page (masthead, columns,
  page breaks, citations legible in ink).

**D — openness mechanics + the record grows.**
- D1 Repoint `SOURCE_REPO` in `web/emit.py` to this repo; OPERATING §5
  gains the native release step (push + tag `vX.Y.Z` at every deployed
  commit); minimal CI (Actions: the no-PG suite run on push/PR).
- D2 The freeze (edition_date 2026-06-18): diagnose (scheduler execution
  history; poll previews — zero filed + zero unmatched means the feed
  itself returned nothing, check channel ids in `record/sources.py`; the
  steward queue), fix what is ours, PROVE one meeting lands
  ingest→press→live. Re-pointing sources or new spend is Stephen's
  (AskUserQuestion). Then the growth checkpoint: which towns/bodies,
  how far to backfill, inside the $100/mo. Success: edition_date moves
  weekly, untouched.

## 5. Non-goals

Accounts or server-side identity (ever). Paper-as-homepage (offered,
declined). WYSIWYG rich text or stored HTML (notes stay plain, capped).
New AI surfaces (any change to AI use updates `/app/ai` in the same
commit). Loudening paper mode or any rendered paper.
