"""OCR helper for the server-side image CAPTCHAs on the agency and admin login pages.

The CAPTCHA value lives only in the PHP session, so the only way to read it is
from the rendered image. Callers must pass the bytes of the image *as shown in
the page* (e.g. ``locator.screenshot()``) — re-requesting ``captcha_image.php``
generates a new value in the session and invalidates the one on screen.

How it reads: the image holds 6 well-separated characters, each in its own
colour, on a light grid. Each character is located from its "ink" (saturated
or dark pixels), cropped with a fixed-width window, cleaned up (grayscale,
autocontrast, 3x upscale) and classified on its own by ddddocr, restricted to
``CAPTCHA_ALPHABET``. On 27 labelled screenshots from test runs this read
27/27 correctly; ddddocr on the whole image read 12/27.

If the dev server is ever configured to accept a fixed CAPTCHA, set
``CAPTCHA_BYPASS_VALUE`` in ``.env`` and OCR is skipped entirely.
"""
import io
import os

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
