# 26 — The meeting, cut and found: Community Highlighter's desk, in the paper

**Status:** v1.0 · **Stage:** BUILT on branch `topic-story` (after specs/25),
629 tests green, pane-checked on the local twin. Ships with specs/25 as
**v2.1.21 / r44**. **Owner:** Stephen Walter (Weird Machine) · **Related:**
specs/25 (a word, over time), specs/22 (the cutting room), specs/20 §6
(the moments plane, the reel viewer), `CLAUDE.md` (the laws).

## 1. Problem — the desk's features, one press away, were not on the page

Stephen's direction (2026-09-23): *continue making the app have all of the
features of Community Highlighter, but in a more elegant package; think
critically about the UX and UI.* Read against the Highlighter's own
inventory (its `CLAUDE.md`: the hero "Make AI Highlight Reel" button, the
reel styles, search within a video with a sparkline and Watch / + Timeline,
the word cloud hero, the section navigation bar, the download center, the
keyboard shortcuts overlay, the reel player) and against the record's
meeting page, the gaps were plain:

- The moments were cards with ticks; the reel itself — the night in three
  minutes — took five presses and a trip to the panel. The Highlighter's
  first feature is one press.
- Nothing searched *within* a meeting. A reader with a four-hour transcript
  and one word in mind had the site search (every meeting) or Ctrl-F (no
  times, no tape, no reel).
- The word cloud — the Highlighter's signature — lived on the front page
  only; the meeting page had a list of topic beads.
- A four-hour tape is a long page with no orientation: the tape, the
  summary, the moments, the votes, the filings, the framing, the questions,
  the transcript, the downloads — with no way to know what was there or
  to jump to it.
- The keys existed (`/`, `j`/`k`, `c`, Space, the arrows) and nothing said
  so.
- On the front page the bodies filter — a control for the meeting list —
  sat above the stories, pushing the story a screen down on a phone.

Two Highlighter features stay at the desk, by design and by the covenant:
rendering a reel to a video file (the reel.json opens in the desk app) and
the outbound "Investigate" (news, maps, Wikipedia — a third party's
server). Translation on the fly waits on the drain (specs/15).

## 2. What was built

### 2.1 The night, cut (`web/cuts.py`; the meeting page; the latest story)

The press cuts every meeting's reels from its own moments plane: **▶ the
night in 3:40** — its five loudest moments in tape order — and one reel per
kind: the roll calls, the decisions, the pushback, the questions (a kind
stops at sixteen clips and says "the first 16 of 24"). Each is the viewer's
own link (`topic.reel_url`, v1: one meeting), so it plays clip to clip at
`/app/r` with the transport, shares as its address, and opens back into a
tray with *make this reel yours*. Pressed as a card under the tape, in the
paper palette, no button, no script; the front page's latest story closes
with the same ▶. Pure over the plane: the same meeting presses the same
links every night.

### 2.2 Find in this meeting (`app.js` wireFind · mpFind · mpTray)

A find box over the transcript, minted by the script (a pressed box that
did nothing with the script off would be the lie the covenant forbids):
whole-word, case-blind (the engine's own `phraseRe` / `mentionsIn`), over
the rows already on the page. The lines that say the word stay, the rest
fold away; the count reads "12 lines · 14 mentions"; a sparkline says where
on the night the word fell (48 slices, each a seek); **▶ play the mentions
as a reel** (each line and the twelve seconds after it — the sentence, not
the caption line — runs merged, never past the tape: the tray's rule for a
hit, the search page's and the supercut's) and **✂ put them on my tray**; *show the whole transcript* restores it; Esc clears; `/` lands in
the box on a meeting page. A deep link into a folded transcript reveals its
row. Nothing leaves the browser.

### 2.3 The meeting in words (the pressed cloud)

The Highlighter's word cloud hero, pressed on every meeting page: the words
said most, sized by how often, civic stopwords out, each a deep link to its
first mention on the tape (the answer with the script off); with the script
on, a word runs the find. The front page's cloud and this one are the same
picture (`charts.word_cloud`), so the record's face is one face.

### 2.4 On this page (the jump bar), the downloads

A pressed line of anchors under the title naming only the sections this
meeting has — the tape · the summary · the night, cut · the moments · the
votes · the town's paper · the framing · the questions · in words · the
transcript · downloads — each section carrying its id. The transcript bar
says that ＋ on a line cuts it, and the downloads gain the kit.json beside
the transcript and the tracks.

### 2.5 The keys (`?`)

One sheet, on every page, that lists what the keyboard does *here* — `/`,
`?`, Esc everywhere; `j` `k` Enter `c` on the search page; `c` on a
transcript line and Esc in the find box on a meeting; Space and the arrows
on a reel; the mode bar's arrows in the studio. A `<dialog>`, script-built,
opened by `?`, closed by Esc or its button; the Highlighter's shortcuts
overlay, in the paper. Every key is a shortcut for something a pointer can
do.

### 2.6 The front page and the search page, adjusted

The bodies filter moves under the stories, beside the list it filters; the
story is the first thing after the search. The search page's story offers
*the N lines themselves ↓* so the hits are one press away on a phone.

## 3. Bounds — the laws

- **Byte-clean**: the cut card, the words and the jump bar are pressed
  content (`mp-` namespace, `kb-` for the keys); the find box and the sheet
  are script-built; no `<button`, no `cz-`, no studio hue on the pressed
  page.
- **Covenant**: nothing on the make path touches a server; the reels are
  links; the tray is localStorage; the find reads the page.
- **Store**: nothing new.
- **Counted, never modeled**: the cuts are the analyzer's scored moments,
  a measurement — the card says so.
- **Controls describe the painted state**: the find's count and fold are
  the rows as they stand; the sheet lists only keys this page answers.

## 4. What is Stephen's

- **Ship** with specs/25 (v2.1.21 / r44).
- **Reel thumbnails** on the tray (the Highlighter's per-clip stills) — a
  YouTube thumbnail per clip is one image request per clip to a third
  party; the covenant's click-to-load line applies, so it is his call.
- **Drag to reorder** on the tray (the up/down buttons stand; the keyboard
  is the house's first-class way).
- **A glossary** ("what is a warrant article?") — content, not code.

## 5. Verification

An adversarial review found eleven defects, every one folded and pinned:
the kit link stands only where a kit was pressed; a draft-only reading is
the summary jump's target; overlapping moment windows play once (the
night's reels merge like the supercut); a miss keeps the transcript whole;
a deep link into a folded transcript reveals and lands; ✂ before the plane
lands waits for it; the cloud's label says what its words do; the keys
sheet toggles, lists only what the page answers, and closes from the
backdrop alone; the jump link carries no number its list would contradict.
The folds were re-reviewed and five more findings folded: the keys sheet
keeps the search page's own keys out; the find's play button counts clips;
the merge has one rule; the night's reels merge under the supercut's cap;
a miss leaves nothing to reveal into.

`tests/test_web_cuts.py`: the loudest five in tape order and one reel per
kind; the cap; no moments, no cut; the links decode with the reader's
decodeReel; the pressed meeting page carries the cut card, the words, the
jump bar (only what the page has), the ids and the downloads, byte-clean,
with no pressed find box; the front page's latest story closes with the
night and the bodies filter sits under the stories; the reader carries the
find, the tray and the keys, wired from the router. Pane-checked on the
local twin: the jump bar, the cut card's links open the viewer, the cloud's
words run the find, the find folds the transcript and plays the mentions,
`?` opens the sheet.
