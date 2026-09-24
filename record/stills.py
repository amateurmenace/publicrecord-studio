"""The press presses pictures (specs/29 §P0.2).

The broadsheet reads a meeting around its tape: the poster large under the
score, three real frames from inside the night across the filmstrip, every
tape of the year as its own still. Those pictures are YouTube's own — the
poster `hqdefault.jpg` and the in-tape frames `hq1.jpg`, `hq2.jpg`, `hq3.jpg`
at `i.ytimg.com` — and the covenant says the reader page loads nothing from
a third party. So the press fetches them ONCE, keeps them in a cache that
outlives a pressing, and writes them into the edition at
`app/stills/<pid>.jpg` and `<pid>-1..3.jpg`; the page then loads them from
the edition like any other plane.

Two honest edges. A frame YouTube does not have for a video comes back as a
small grey placeholder with a 200, not a 404 — anything under `MIN_BYTES`,
or not a JPEG at all, is not a still and is not pressed. And a press with no
network (the desk's test bake, a press told not to fetch) presses no stills
and says so: every page that would show one shows the town's colour instead,
and the bytes are the same on every such press (determinism is a law here).

In the cloud the cache is seeded from the edition bucket before the fetch —
a Cloud Run job's disk is new on every execution, and the bucket already
holds last night's stills — so a still is fetched from YouTube on the night
its meeting lands and never again. Nothing here calls a model.
"""

from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Tuple

YT = "https://i.ytimg.com/vi/{vid}/{name}.jpg"
# (the file's suffix in the edition, YouTube's name for it)
FRAMES: Tuple[Tuple[str, str], ...] = (("", "hqdefault"), ("-1", "hq1"),
                                        ("-2", "hq2"), ("-3", "hq3"))
MIN_BYTES = 2_500          # YouTube's "no such frame" card is ~1 KB, grey, and a 200
MAX_BYTES = 2_000_000      # nothing YouTube serves at hq size is near this
TIMEOUT = 8.0
_JPEG = b"\xff\xd8"
_UA = "publicrecord.studio press (+https://publicrecord.studio)"


def fetch(url: str, timeout: float = TIMEOUT) -> Optional[bytes]:
    """One GET, or None — a failure is a missing still, never a failed press."""
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if getattr(r, "status", 200) != 200:
                return None
            return r.read(MAX_BYTES + 1)
    except Exception:
        return None


def is_still(data: Optional[bytes]) -> bool:
    """A real picture: JPEG bytes, bigger than YouTube's placeholder card."""
    return bool(data) and data[:2] == _JPEG and MIN_BYTES <= len(data) <= MAX_BYTES


def still_path(pid: str, frame: int = 0, base: str = "/app") -> str:
    """The edition path of a meeting's poster (frame 0) or in-tape frame 1–3."""
    return f"{base}/stills/{pid}{'-' + str(frame) if frame else ''}.jpg"


class Stills:
    """The press's picture desk: a cache that outlives a pressing, and a
    fetcher that is asked only for what the cache lacks. `fetch=False`
    presses what the cache holds and nothing else (the desk's default)."""

    def __init__(self, cache: Optional[Path] = None, fetch: bool = True,
                 fetcher: Callable[[str], Optional[bytes]] = fetch):
        self.cache = Path(cache) if cache else None
        self.fetch = bool(fetch)
        self.fetcher = fetcher
        self.fetched = self.copied = self.missed = 0

    # -- the cache -------------------------------------------------------
    def _cached(self, fn: str) -> Optional[bytes]:
        if not self.cache:
            return None
        p = self.cache / fn
        try:
            data = p.read_bytes() if p.is_file() else None
        except OSError:
            return None
        return data if is_still(data) else None

    def _keep(self, fn: str, data: bytes) -> None:
        if not self.cache:
            return
        try:
            self.cache.mkdir(parents=True, exist_ok=True)
            (self.cache / fn).write_bytes(data)
        except OSError:
            pass   # a cache that cannot be written is a slower press, not a broken one

    def seed_from_bucket(self, bucket: str, prefix: str = "app/stills") -> int:
        """Copy the stills a previous pressing already put in the bucket into
        the cache, so tonight's press asks YouTube only for tonight's tapes.
        Best effort: no client, no credentials, no bucket → 0, and the press
        goes on (it will fetch instead)."""
        if not self.cache or not bucket:
            return 0
        try:
            from google.cloud import storage
            client = storage.Client()
            n = 0
            for b in client.list_blobs(bucket, prefix=prefix.strip("/") + "/"):
                fn = b.name.rsplit("/", 1)[-1]
                if not fn.endswith(".jpg") or (self.cache / fn).is_file():
                    continue
                data = b.download_as_bytes()
                if is_still(data):
                    self._keep(fn, data)
                    n += 1
            return n
        except Exception:
            return 0

    # -- the press ---------------------------------------------------------
    def press(self, rows: Iterable[Tuple[str, str]], out_dir: Path) -> Dict[str, dict]:
        """Press the poster and the three frames for every (pid, video_id) into
        `out_dir`. Returns what was pressed: {pid: {"poster": bool,
        "frames": [1, 2, 3]}} — only meetings with at least one picture."""
        out = Path(out_dir)
        have: Dict[str, dict] = {}
        for pid, vid in sorted((str(p or ""), str(v or "")) for p, v in rows):
            if not pid or not vid:
                continue
            rec = {"poster": False, "frames": []}
            for suffix, name in FRAMES:
                fn = f"{pid}{suffix}.jpg"
                data = self._cached(fn)
                if data is not None:
                    self.copied += 1
                elif self.fetch:
                    got = self.fetcher(YT.format(vid=vid, name=name))
                    if is_still(got):
                        data = got
                        self.fetched += 1
                        self._keep(fn, data)
                if data is None:
                    self.missed += 1
                    continue
                out.mkdir(parents=True, exist_ok=True)
                (out / fn).write_bytes(data)
                if suffix:
                    rec["frames"].append(int(suffix[1:]))
                else:
                    rec["poster"] = True
            if rec["poster"] or rec["frames"]:
                have[pid] = rec
        return have

    def note(self) -> str:
        return (f"{self.fetched} fetched · {self.copied} from the cache · "
                f"{self.missed} not available")


def copy_tree(src: Path, dst: Path) -> int:
    """A helper for a press that keeps its stills beside the edition."""
    n = 0
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for p in sorted(src.glob("*.jpg")):
            shutil.copyfile(p, dst / p.name)
            n += 1
    return n
