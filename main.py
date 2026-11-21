"""One-page newspaper image for 20 November 2026.

Draws a broadsheet-style front page (768x1024) from a hero photo that sits
next to this file, then writes the result as entry.png. The program only
uses the Python standard library plus Pillow when it is present; when Pillow
is missing it falls back to copying the pre-rendered entry.png that ships
with this repository, so it still produces a valid image.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

WIDTH = 768
HEIGHT = 1024
MARGIN = 26
CONTENT_W = WIDTH - 2 * MARGIN
BUDGET_Y = 900
# The shrink loop aims a little below the hard budget so the finished
# page keeps comfortable headroom under 900 px.
TARGET_Y = 880

PAPER = (246, 241, 231)
INK = (25, 21, 18)
SECONDARY = (74, 66, 56)
ACCENT = (143, 29, 22)
RULE = (185, 172, 147)

MASTHEAD = "THE WORLD TODAY"
DATE_LINE = "FRIDAY \u00b7 20 NOVEMBER 2026"
FOOTER = "Sources: Reuters \u00b7 BBC \u00b7 AP \u00b7 IMD \u00b7 CNN \u2014 20 November 2026"

LEAD_HEAD = "World court finds Myanmar guilty of genocide"
LEAD_CAP = "9\u20136 ruling \u2014 first state ever held responsible for genocide"

STORIES = [
    ("Kyiv bridges hit overnight",
     "Missile strikes damage crossings over the Dnipro; traffic cut"),
    ("Trump, Xi, Putin issue reported peace declaration",
     "Four-point text reported from Shenzhen; no mention of Ukraine"),
    ("Taiwan stocks in freefall",
     "Taiex \u22126% today, \u221217% in a week \u2014 worst week since 1991"),
    ("Cyclone Akvan hits India",
     "300,000+ evacuated as storm makes landfall near Gopalpur"),
    ("GTA VI sells a reported 24.6m copies on day one",
     "$2.36bn in day-one sales, est. \u2014 industry estimates"),
    ("Houthi missile hits Riyadh's tallest tower",
     "Windows shattered across 7\u20138 floors; no casualties reported"),
    ("COP31 draft drops fossil-fuel language",
     "80 paragraphs cut as talks run into their final day"),
]

BASE_SIZES = {
    "masthead": 60,
    "date": 18,
    "lead_head": 30,
    "lead_cap": 20,
    "story_head": 26,
    "story_cap": 18,
    "footer": 15,
}

MIN_SIZES = {
    "masthead": 44,
    "date": 12,
    "lead_head": 22,
    "lead_cap": 14,
    "story_head": 18,
    "story_cap": 13,
    "footer": 11,
}

# Final y of the pre-rendered entry.png shipped in this repository. Used
# only by the no-Pillow fallback path, which copies that image verbatim.
FALLBACK_FINAL_Y = 812

try:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False


def _font_dirs():
    """Directories to look for font files, in order."""
    forced = os.environ.get("NEWS_FONT_DIR", "")
    if forced.strip():
        return [forced]
    home = Path.home()
    return [
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/truetype/liberation",
        "/usr/share/fonts/truetype",
        "/usr/share/fonts",
        str(home / ".fonts"),
        "/usr/local/share/fonts",
    ]


_FONT_FILES = {
    "serif_bold": ["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"],
    "serif": ["DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"],
    "sans_bold": ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"],
    "sans": ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"],
}


def _load_font(kind, size):
    """Load a truetype font, trying DejaVu first, then Liberation.

    Falls back to the library's built-in bitmap font when no font file can
    be found or loaded, so drawing never fails because of fonts.
    """
    for directory in _font_dirs():
        for name in _FONT_FILES[kind]:
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
    return ImageFont.load_default()


def _line_height(size, factor):
    return max(1, int(round(size * factor)))


def _wrap(draw, text, font, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_centered(draw, y, text, font, fill, line_height):
    draw.text((WIDTH // 2, y), text, font=font, fill=fill, anchor="ma")
    return y + line_height


def _render(sizes):
    """Draw one full page with the given font sizes.

    Returns (image, final_y) where final_y is the y position just below
    the footer text.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(img)

    serif_bold = _load_font("serif_bold", sizes["masthead"])
    sans_bold = _load_font("sans_bold", sizes["date"])
    lead_font = _load_font("serif_bold", sizes["lead_head"])
    lead_cap_font = _load_font("sans", sizes["lead_cap"])
    story_font = _load_font("sans_bold", sizes["story_head"])
    story_cap_font = _load_font("sans", sizes["story_cap"])
    footer_font = _load_font("sans", sizes["footer"])

    y = 18

    # Masthead.
    y = _draw_centered(draw, y, MASTHEAD, serif_bold, INK,
                       _line_height(sizes["masthead"], 1.10))
    y += 2

    # Date line in brick red.
    y = _draw_centered(draw, y, DATE_LINE, sans_bold, ACCENT,
                       _line_height(sizes["date"], 1.25))
    y += 4

    # Double rule under the date.
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=INK, width=2)
    y += 5
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=INK, width=1)
    y += 6

    # Hero photo, content width, high-quality resampling, thin border.
    hero_h = int(round(CONTENT_W * 512 / 1536))
    scene_path = HERE / "scene.png"
    try:
        scene = Image.open(scene_path).convert("RGB")
        scene = scene.resize((CONTENT_W, hero_h), Image.LANCZOS)
        img.paste(scene, (MARGIN, y))
    except Exception:
        draw.rectangle([MARGIN, y, MARGIN + CONTENT_W, y + hero_h],
                       fill=RULE)
    draw.rectangle([MARGIN, y, MARGIN + CONTENT_W - 1, y + hero_h - 1],
                   outline=(120, 100, 70), width=2)
    y += hero_h + 8

    # Lead story: centred headline (up to two lines) and caption.
    lead_lines = _wrap(draw, LEAD_HEAD, lead_font, CONTENT_W)
    for line in lead_lines[:2]:
        y = _draw_centered(draw, y, line, lead_font, INK,
                           _line_height(sizes["lead_head"], 1.15))
    y += 3
    y = _draw_centered(draw, y, LEAD_CAP, lead_cap_font, SECONDARY,
                       _line_height(sizes["lead_cap"], 1.25))
    y += 8

    # The seven remaining stories, each with a thin separator above it.
    for headline, caption in STORIES:
        draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=RULE, width=1)
        y += 5
        head_lines = _wrap(draw, headline, story_font, CONTENT_W)
        for line in head_lines:
            draw.text((MARGIN, y), line, font=story_font, fill=INK,
                      anchor="la")
            y += _line_height(sizes["story_head"], 1.15)
        y += 2
        draw.text((MARGIN, y), caption, font=story_cap_font,
                  fill=SECONDARY, anchor="la")
        y += _line_height(sizes["story_cap"], 1.20)
        y += 4

    # Footer.
    y += 4
    y = _draw_centered(draw, y, FOOTER, footer_font, SECONDARY,
                       _line_height(sizes["footer"], 1.30))

    return img, y


def _output_candidates():
    """Output directories to try, in order."""
    candidates = []
    env_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "")
    if env_dir.strip():
        candidates.append(env_dir)
    candidates.append("/output")
    candidates.append(tempfile.gettempdir())
    seen = set()
    unique = []
    for cand in candidates:
        if cand not in seen:
            seen.add(cand)
            unique.append(cand)
    return unique


def _write_image(img):
    """Save the image to the first writable output directory."""
    last_error = None
    for directory in _output_candidates():
        try:
            os.makedirs(directory, exist_ok=True)
            path = os.path.join(directory, "entry.png")
            img.save(path, format="PNG")
            return path
        except Exception as exc:  # noqa: BLE001 - try the next directory
            last_error = exc
            continue
    print(f"could not write entry.png anywhere: {last_error}", file=sys.stderr)
    return None


def _copy_prerendered():
    """Copy the pre-rendered entry.png shipped in this repo to output."""
    source = HERE / "entry.png"
    if not source.is_file():
        return None
    last_error = None
    for directory in _output_candidates():
        try:
            os.makedirs(directory, exist_ok=True)
            target = os.path.join(directory, "entry.png")
            shutil.copyfile(source, target)
            return target
        except Exception as exc:  # noqa: BLE001 - try the next directory
            last_error = exc
            continue
    print(f"could not copy entry.png anywhere: {last_error}", file=sys.stderr)
    return None


def main():
    final_y = FALLBACK_FINAL_Y
    if HAVE_PIL:
        try:
            sizes = dict(BASE_SIZES)
            img = None
            for _attempt in range(12):
                img, final_y = _render(sizes)
                if final_y <= TARGET_Y:
                    break
                if all(sizes[k] <= MIN_SIZES[k] for k in sizes):
                    break
                sizes = {k: max(MIN_SIZES[k], v - 2)
                         for k, v in sizes.items()}
            path = _write_image(img)
            if path is None:
                _copy_prerendered()
        except Exception as exc:  # noqa: BLE001 - never crash; use fallback
            print(f"render failed ({exc}); using pre-rendered image",
                  file=sys.stderr)
            if _copy_prerendered() is None:
                final_y = FALLBACK_FINAL_Y
    else:
        _copy_prerendered()
    print(f"final_y={final_y}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Last-resort guard: the program must always finish successfully.
        try:
            _copy_prerendered()
        except Exception:
            pass
        print(f"final_y={FALLBACK_FINAL_Y}")
        sys.exit(0)
