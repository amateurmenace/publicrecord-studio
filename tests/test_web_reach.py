"""The reach (v2.2.10): what a sweep of the live edition found a reader
could not reach or read — an id two transcript lines shared, counts a
cell's own colour drowned, targets a finger could not hit, a table twin
that stacked a date into a column of characters. Each pinned here."""

import re
import unittest
from pathlib import Path

from web import emit

REPO = Path(__file__).resolve().parents[1]
CSS = (REPO / "web" / "static" / "app.web.css").read_text()


def _lum(c):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def _ratio(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


MANIFEST = {"version": "9", "corpus_hash": "x", "edition_date": "2026-09-01", "counts": {}, "schema": 1}


class TestTheReach(unittest.TestCase):
    def test_a_second_s_anchor_is_its_first_line_s_alone(self):
        """Two lines that start in one second shared its id (t116 four times
        on a live page): the id goes on the second's first line only; every
        line keeps its own time link, and #t<sec> lands where it always did."""
        segs = [{"start": 116.2, "text": "one"}, {"start": 116.7, "text": "two"}, {"start": 116.9, "text": "three"},
                {"start": 117.0, "text": "four"}]
        m = {"pid": "p", "id": "p", "title": "A night", "date": "2026-03-10", "town": "Brookline", "body": "Select Board",
             "source_kind": "youtube", "video_id": "abcdefghijk", "url": "u", "duration": 200.0, "segments": segs,
             "summary": "", "summary_origin": "", "analysis": {}, "issues": [], "votes": [], "documents": [],
             "tracks": [], "ad": None, "moments": [], "n_speakers": 0}
        page = emit.page_meeting(m, MANIFEST, "https://example.org")
        ids = re.findall(r'\bid="([^"]+)"', page)
        self.assertEqual(len(ids), len(set(ids)), [i for i in ids if ids.count(i) > 1])
        rows = re.findall(r'<p class="seg"( id="t\d+")? data-t="([\d.]+)"', page)
        self.assertEqual([bool(a) for a, _ in rows], [True, False, False, True])
        self.assertEqual(page.count('<a class="ts" href="#t116">'), 3)          # each line keeps its time link

    def test_every_count_in_the_heat_reads_at_aa(self):
        """The record drawn: the numbers on the framing heat flipped to white
        at 0.46 and read 2.9:1 there. Every cell's count now reads at 4.5:1 or
        better on its own colour (the cell composited on the card)."""
        rows = [{"pid": f"p{i}", "date": "2026-03-10", "body": "Select Board", "title": "t", "total": 100,
                 "lenses": {"financial": i, "community": 100 - i}} for i in range(0, 101)]
        page = emit.page_analytics({"lens_order": ["financial", "community"], "lens_color": {}, "framing": rows,
                                    "topics": [], "names": [], "towns": []}, MANIFEST, "https://example.org")
        cells = re.findall(r'<td style="background:rgba\(5,46,22,([\d.]+)\);color:(#[0-9a-f]{6})"', page)
        self.assertGreater(len(cells), 150)
        card, green = (251, 249, 244), (5, 46, 22)
        for a, ink in cells:
            a = float(a)
            bg = tuple(a * g + (1 - a) * c for g, c in zip(green, card))
            fg = tuple(int(ink[i:i + 2], 16) for i in (1, 3, 5))
            self.assertGreaterEqual(_ratio(fg, bg), 4.5, (a, ink))
        self.assertFalse(any(0.56 < float(a) < 0.62 for a, _ in cells))     # the dead band is never drawn

    def test_a_finger_s_targets_and_the_twins_on_a_phone(self):
        """WCAG 2.5.8: the scope and range buttons stand 25 px tall; on a
        phone's screen the way back, the colophon and the glossary's index
        stand 24 px; a table twin's first column (its date) is never split
        into a column of characters — its wrapper scrolls instead."""
        self.assertIn(".scopeacts .btn{font-size:var(--text-xs);padding:6px 11px}", CSS)
        sq = CSS[CSS.index(".sq-rb{"):]
        self.assertIn("cursor:pointer;padding:6px 10px;", sq[:sq.index("}")])
        phone = CSS[CSS.index("@media screen and (max-width:720px){"):]
        phone = phone[:phone.index("\n}\n")]
        for rule in (".back{display:inline-block;padding:5px 0}", ".bs-site{padding:3px 0}", ".cov{display:inline-block;padding:4px 0}",
                     ".gl-index a{display:inline-block;padding:5px 0}",
                     ".fp-twinwrap table.twin td:first-child a,.pb-twinwrap table.twin td:first-child a{white-space:nowrap}"):
            self.assertIn(rule, phone)
            self.assertEqual(CSS.count(rule), 1, rule)                           # a phone's alone: desktop and paper unchanged
        # a tape the station keeps says so on the player's own dark ground, in the rule's light colour (11.8:1)
        self.assertIn(".player.local .phint{position:static;background:none;color:var(--rule)}", CSS)
        self.assertIn(".player{", CSS); self.assertIn("background:var(--surface-inverse)", CSS[CSS.index(".player{"):][:400])
        # a tape's 48 slices: each link reaches a pixel into the gaps beside its bar — one strip, no dead gaps
        self.assertIn(".fp-sbar::after{content:\"\";position:absolute;top:0;bottom:0;left:-1px;right:-1px}", CSS)
        bars = CSS[CSS.index(".fp-sbars{"):]
        self.assertIn("gap:2px;height:24px", bars[:bars.index("}")])


    def test_the_word_cloud_s_rarest_words_still_read(self):
        """The cloud fades its rarer words — down to 0.40, 2.5:1 on the paper
        (a review's catch). The fade now stops where a word reads at AA: 4.5:1
        for the smaller bold words, 3:1 for the large."""
        from web import charts
        words = [{"word": f"w{i:02d}{'x' * (i % 5)}", "count": 200 - i * 3} for i in range(60)]
        svg = charts.word_cloud(words)
        ink = (0x19, 0x17, 0x12)
        for fs, op in re.findall(r'font-size="([\d.]+)" fill="#[0-9A-Fa-f]{6}" fill-opacity="([\d.]+)"', svg):
            fs, op = float(fs), float(op)
            for bg in ((251, 249, 244), (243, 238, 227)):                       # the card and the paper
                fg = tuple(op * i + (1 - op) * b for i, b in zip(ink, bg))
                self.assertGreaterEqual(_ratio(fg, bg), 4.5 if fs < 18.66 else 3.0, (fs, op))


if __name__ == "__main__":
    unittest.main()
