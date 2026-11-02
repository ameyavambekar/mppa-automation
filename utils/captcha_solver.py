"""OCR helpers for the server-side image CAPTCHAs on the agency and admin login pages.

The CAPTCHA value lives only in the PHP session, so the only way to read it is
from the rendered image. Callers must pass the bytes of the image *as shown in
the page* (e.g. ``locator.screenshot()``) — re-requesting ``captcha_image.php``
generates a new value in the session and invalidates the one on screen.

Agency login / Forgot password (``solve_captcha_image``): the image holds 6
well-separated characters, each in its own
colour, on a light grid. Each character is located from its "ink" (saturated
or dark pixels), cropped with a fixed-width window, cleaned up (grayscale,
autocontrast, 3x upscale) and classified on its own by ddddocr, restricted to
``CAPTCHA_ALPHABET``. On 27 labelled screenshots from test runs this read
27/27 correctly; ddddocr on the whole image read 12/27.

Admin login (``solve_admin_captcha_image``): since the 02-Nov-2026 redesign the
admin page draws 6 dark-navy characters in a fixed pixel font, often touching,
with pale wavy lines across them, from a smaller alphabet
(``ADMIN_CAPTCHA_ALPHABET``). ddddocr reads that style badly (23/40 whole codes),
so each glyph is matched against templates averaged from the labelled
screenshots in ``utils/captcha_samples/admin/`` (file name = the code shown).
Leave-one-out on those 82 samples: 82/82; live on dev: 58/60 accepted by the
server, against about 60% for ddddocr. A glyph that matches no template well
makes the reader return "" so the caller refreshes the image instead of
submitting a guess. Add newly labelled screenshots there to extend it.

If the dev server is ever configured to accept a fixed CAPTCHA, set
``CAPTCHA_BYPASS_VALUE`` in ``.env`` and OCR is skipped entirely.
"""
import io
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from PIL import Image, ImageOps

load_dotenv()

CAPTCHA_BYPASS_VALUE = os.getenv("CAPTCHA_BYPASS_VALUE", "").strip()
CAPTCHA_LENGTH = 6
# Characters the portal draws: A-Z and 2-9 without the look-alikes I, O, 0, 1.
CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

_FRAME = 3          # px of image border (frame) ignored when looking for ink
_HALF_WIDTH = 8     # half-width of each character window (glyphs ~10 px, pitch ~30 px)
_SCALE = 3          # upscale factor applied to each character crop

_ocr = None         # lazily-created ddddocr.DdddOcr; loading the model takes ~1s
_alphabet_cols = None  # CAPTCHA_ALPHABET char -> model output columns (upper + lower case)


def _get_ocr():
    # No set_ranges(): in ddddocr 1.6.1 restricting the charset makes
    # classification() drop characters or return "". The alphabet is applied
    # to the model's probabilities in _read_char() instead.
    global _ocr
    if _ocr is None:
        import ddddocr

        _ocr = ddddocr.DdddOcr(show_ad=False)
    return _ocr


def _ink_mask(rgb: np.ndarray) -> np.ndarray:
    """True for character pixels: saturated colour or dark (the grid is pale grey)."""
    a = rgb.astype(int)
    mx, mn = a.max(2), a.min(2)
    return ((mx - mn) >= 60) | (mx <= 110)


def _char_boxes(im: Image.Image) -> list:
    """Returns CAPTCHA_LENGTH (x0, x1, y0, y1) boxes, one per character, left to right."""
    mask = _ink_mask(np.asarray(im))[_FRAME:-_FRAME, _FRAME:-_FRAME]
    on = mask.sum(0) >= 2
    runs, x = [], 0
    while x < len(on):
        if on[x]:
            start = x
            while x < len(on) and on[x]:
                x += 1
            runs.append([start, x])
        x += 1
    runs = [r for r in runs if mask[:, r[0]:r[1]].sum() >= 15]          # drop specks
    while len(runs) > CAPTCHA_LENGTH:                                     # merge the closest pair
        gaps = [runs[i + 1][0] - runs[i][1] for i in range(len(runs) - 1)]
        i = int(np.argmin(gaps))
        runs[i] = [runs[i][0], runs[i + 1][1]]
        del runs[i + 1]
    if len(runs) != CAPTCHA_LENGTH:                                       # fall back to equal slots
        slot = mask.shape[1] / CAPTCHA_LENGTH
        runs = [[int(i * slot), int((i + 1) * slot)] for i in range(CAPTCHA_LENGTH)]

    # The ink mask often catches only a glyph's thick stroke (e.g. the stem of a
    # "T"), so crop a fixed-width window around each run's centre instead.
    boxes = []
    for x0, x1 in runs:
        cx = (x0 + x1) // 2 + _FRAME
        wx0, wx1 = max(_FRAME, cx - _HALF_WIDTH), min(im.width - _FRAME, cx + _HALF_WIDTH)
        rows = np.where(mask[:, wx0 - _FRAME:wx1 - _FRAME].sum(1) > 0)[0] + _FRAME
        y0, y1 = (rows.min() - 1, rows.max() + 2) if len(rows) else (_FRAME, im.height - _FRAME)
        boxes.append((wx0, wx1, max(_FRAME, y0), min(im.height - _FRAME, y1)))
    return boxes


def _char_png(im: Image.Image, box) -> bytes:
    x0, x1, y0, y1 = box
    c = im.crop((max(0, x0 - 2), max(0, y0 - 2), x1 + 2, y1 + 2))
    c = ImageOps.autocontrast(ImageOps.grayscale(c), cutoff=2)
    c = ImageOps.expand(c, border=8, fill=255)
    c = c.resize((c.width * _SCALE, c.height * _SCALE), Image.LANCZOS).convert("RGB")
    buf = io.BytesIO()
    c.save(buf, "PNG")
    return buf.getvalue()


def _read_char(png: bytes) -> str:
    """Classifies one character crop, picking the most likely CAPTCHA_ALPHABET char."""
    global _alphabet_cols
    result = _get_ocr().classification(png, probability=True)
    probs = np.asarray(result["probabilities"], dtype=float).reshape(len(result["probabilities"]), -1)
    if _alphabet_cols is None:
        charset = result["charset"]
        _alphabet_cols = {ch: [i for i, c in enumerate(charset) if c and c.upper() == ch]
                          for ch in CAPTCHA_ALPHABET}
    scores = {ch: probs[:, cols].max() for ch, cols in _alphabet_cols.items() if cols}
    return max(scores, key=scores.get)


def solve_captcha_image(image_bytes: bytes) -> str:
    """Returns the CAPTCHA text read from ``image_bytes`` (CAPTCHA_LENGTH
    characters from CAPTCHA_ALPHABET). A wrong read is still possible — the
    server then rejects it and shows a new CAPTCHA."""
    if CAPTCHA_BYPASS_VALUE:
        return CAPTCHA_BYPASS_VALUE
    im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return "".join(_read_char(_char_png(im, box)) for box in _char_boxes(im))


# ── Admin login CAPTCHA (pixel font, template matching) ─────────────────────────

# Characters the admin page draws: no B, I, O, S, Z, 0, 1, 2, 5, 8 or 9 in 240 sampled characters.
ADMIN_CAPTCHA_ALPHABET = "ACDEFGHJKLMNPQRTUVWXY3467"
ADMIN_SAMPLES_DIR = Path(__file__).parent / "captcha_samples" / "admin"

_GLYPH_H = 17               # glyph height in px (glyphs are about 17 x 14)
_CANVAS = (21, 19)          # each glyph is centred on a canvas this size (rows, cols)
_SHIFT = 2                  # +/- px tried when matching a glyph to a template
_MIN_RUN_INK = 12           # ink px below which a column run is a fragment, not a glyph
_ADMIN_MIN_SCORE = 0.70     # weakest match accepted; below it the image is treated as unreadable

_admin_templates = None     # ADMIN_CAPTCHA_ALPHABET char -> mean glyph canvas


def _admin_ink(rgb: np.ndarray) -> np.ndarray:
    """True for glyph pixels: dark and blue. The wavy lines are paler, so they mostly drop out."""
    a = rgb.astype(int)
    mask = (a[..., 0] < 110) & (a[..., 2] - a[..., 0] > 30)
    mask[:_FRAME] = mask[-_FRAME:] = False
    mask[:, :_FRAME] = mask[:, -_FRAME:] = False
    return mask


def _admin_runs(mask: np.ndarray) -> list:
    """Column runs of ink, left to right. A fragment (e.g. the thin foot of an L) joins the
    neighbouring run when it is at most 2 px away, otherwise it is dropped as a speck."""
    on = mask.sum(0) > 0
    runs, x = [], 0
    while x < len(on):
        if on[x]:
            start = x
            while x < len(on) and on[x]:
                x += 1
            runs.append([start, x])
        x += 1
    i = 0
    while i < len(runs):
        if len(runs) > 1 and mask[:, runs[i][0]:runs[i][1]].sum() < _MIN_RUN_INK:
            neighbours = [j for j in (i - 1, i + 1) if 0 <= j < len(runs)]
            gaps = [runs[i][0] - runs[j][1] if j < i else runs[j][0] - runs[i][1] for j in neighbours]
            j = neighbours[int(np.argmin(gaps))]
            if min(gaps) <= 2:
                a, b = min(i, j), max(i, j)
                runs[a:b + 1] = [[runs[a][0], runs[b][1]]]
            else:
                del runs[i]
            i = 0
            continue
        i += 1
    return runs


def _admin_glyph(mask: np.ndarray, x0: int, x1: int) -> np.ndarray:
    """The glyph in columns x0..x1: its densest _GLYPH_H-row band (lines above or below drop out),
    trimmed and centred on a _CANVAS-sized float canvas."""
    sub = mask[:, x0:x1]
    rows = sub.sum(1)
    if len(rows) > _GLYPH_H:
        y0 = int(np.argmax(np.convolve(rows, np.ones(_GLYPH_H), "valid")))
        sub = sub[y0:y0 + _GLYPH_H]
    canvas = np.zeros(_CANVAS)
    ys, xs = np.where(sub)
    if len(ys):
        g = sub[ys.min():ys.max() + 1, xs.min():xs.max() + 1][:_CANVAS[0], :_CANVAS[1]]
        y, x = (_CANVAS[0] - g.shape[0]) // 2, (_CANVAS[1] - g.shape[1]) // 2
        canvas[y:y + g.shape[0], x:x + g.shape[1]] = g
    return canvas


def _match(glyph: np.ndarray, templates: dict) -> tuple:
    """(char, score): the template with the highest cosine similarity over small shifts."""
    best_ch, best = "", -1.0
    shifted = [np.roll(np.roll(glyph, dy, 0), dx, 1)
               for dy in range(-_SHIFT, _SHIFT + 1) for dx in range(-_SHIFT, _SHIFT + 1)]
    norms = [np.sqrt((s * s).sum()) for s in shifted]
    for ch, t in templates.items():
        tn = np.sqrt((t * t).sum())
        for s, sn in zip(shifted, norms):
            v = (s * t).sum() / (sn * tn + 1e-9)
            if v > best:
                best_ch, best = ch, v
    return best_ch, best


def _admin_read(rgb: np.ndarray, templates: dict) -> tuple:
    """(text, weakest match score). Too few runs means glyphs touch: the widest run is cut where
    the two halves match templates best. Too many means a glyph broke apart: the closest pair is
    merged."""
    mask = _admin_ink(rgb)
    runs = _admin_runs(mask)
    while len(runs) > CAPTCHA_LENGTH:
        gaps = [runs[i + 1][0] - runs[i][1] for i in range(len(runs) - 1)]
        i = int(np.argmin(gaps))
        runs[i:i + 2] = [[runs[i][0], runs[i + 1][1]]]
    while 0 < len(runs) < CAPTCHA_LENGTH:
        i = int(np.argmax([x1 - x0 for x0, x1 in runs]))
        x0, x1 = runs[i]
        if x1 - x0 < 8:
            break
        cut = max(range(x0 + 4, x1 - 3),
                  key=lambda c: _match(_admin_glyph(mask, x0, c), templates)[1]
                  + _match(_admin_glyph(mask, c, x1), templates)[1])
        runs[i:i + 1] = [[x0, cut], [cut, x1]]
    reads = [_match(_admin_glyph(mask, x0, x1), templates) for x0, x1 in runs]
    return "".join(ch for ch, _ in reads), min((v for _, v in reads), default=0.0)


def build_admin_templates(samples) -> dict:
    """Mean glyph canvas per character from ``samples`` = [(image bytes, code shown), ...].
    Only samples whose ink splits into exactly CAPTCHA_LENGTH runs are used."""
    glyphs = {}
    for image_bytes, code in samples:
        mask = _admin_ink(np.asarray(Image.open(io.BytesIO(image_bytes)).convert("RGB")))
        runs = _admin_runs(mask)
        if len(runs) != CAPTCHA_LENGTH:
            continue
        for ch, (x0, x1) in zip(code, runs):
            glyphs.setdefault(ch, []).append(_admin_glyph(mask, x0, x1))
    return {ch: np.mean(gs, 0) for ch, gs in glyphs.items()}


def _get_admin_templates() -> dict:
    global _admin_templates
    if _admin_templates is None:
        _admin_templates = build_admin_templates(
            [(f.read_bytes(), f.stem.upper()) for f in sorted(ADMIN_SAMPLES_DIR.glob("*.png"))])
    return _admin_templates


def read_admin_captcha(image_bytes: bytes, templates: dict = None) -> tuple:
    """(text, weakest match score) for the admin login CAPTCHA in ``image_bytes``."""
    rgb = np.asarray(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    return _admin_read(rgb, templates or _get_admin_templates())


def solve_admin_captcha_image(image_bytes: bytes) -> str:
    """Returns the admin login CAPTCHA text read from ``image_bytes``, or "" when a glyph matches
    no template well (BasePage.read_image_captcha then refreshes the image and reads again)."""
    if CAPTCHA_BYPASS_VALUE:
        return CAPTCHA_BYPASS_VALUE
    text, weakest = read_admin_captcha(image_bytes)
    return text if len(text) == CAPTCHA_LENGTH and weakest >= _ADMIN_MIN_SCORE else ""
