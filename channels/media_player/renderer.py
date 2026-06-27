"""Pillow-based poster renderer for the Media Player channel.

Fetches the poster image from a URL and composes a display-ready JPEG:
  - Resize/crop to target resolution (crop or letterbox)
  - Optional info bar at the bottom with title, series, and year

No Playwright / html_renderer dependency required.
"""
from __future__ import annotations

import io
import logging
from typing import Any

logger = logging.getLogger("mimir.channels.media_player.renderer")

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    _PIL = True
except ImportError:
    _PIL = False
    logger.warning("[media_player] Pillow not installed — image rendering unavailable")


def _get_font(size: int):
    """Return a PIL font at the requested size, falling back gracefully."""
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10
    except TypeError:
        return ImageFont.load_default()


def _apply_fit(img: "Image.Image", tw: int, th: int, fit_mode: str) -> "Image.Image":
    """Resize/crop img to (tw, th) according to fit_mode."""
    iw, ih = img.size
    if fit_mode == "crop":
        scale = max(tw / iw, th / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - tw) // 2
        top = (nh - th) // 2
        img = img.crop((left, top, left + tw, top + th))
    else:  # letterbox
        scale = min(tw / iw, th / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        resized = img.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGB", (tw, th), (0, 0, 0))
        canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
        img = canvas
    return img


def _draw_info_bar(img: "Image.Image", session: dict[str, Any], theme: str) -> "Image.Image":
    """Draw a translucent info bar at the bottom of img with title/series/year."""
    tw, th = img.size
    bar_h = max(60, th // 6)

    # Semi-transparent overlay via alpha composite
    overlay = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    bg_color = (0, 0, 0, 190) if theme == "dark" else (255, 255, 255, 190)
    draw_ov.rectangle([(0, th - bar_h), (tw, th)], fill=bg_color)

    # Apply a very slight blur on the bar region for a frosted-glass feel
    bar_region = img.crop((0, th - bar_h, tw, th)).convert("RGBA")
    blurred = bar_region.filter(ImageFilter.GaussianBlur(radius=6))
    img_rgba = img.convert("RGBA")
    img_rgba.paste(blurred, (0, th - bar_h))
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    img = img_rgba.convert("RGB")

    draw = ImageDraw.Draw(img)
    text_color = (240, 240, 240) if theme == "dark" else (20, 20, 20)
    sub_color  = (180, 180, 180) if theme == "dark" else (80, 80, 80)

    pad = max(12, tw // 40)
    y = th - bar_h + pad

    title_size = max(16, min(28, tw // 28))
    sub_size   = max(12, min(18, tw // 40))

    title_font = _get_font(title_size)
    sub_font   = _get_font(sub_size)

    media_type = session.get("media_type", "")
    title = session.get("title") or ""
    series = session.get("series_title")
    year = session.get("year")
    season_num = session.get("season_num")
    episode_num = session.get("episode_num")

    if media_type == "episode" and series:
        ep_label = f"S{season_num:02d}E{episode_num:02d}" if season_num and episode_num else ""
        sub_line = f"{series}  {ep_label}".strip() if ep_label else series
        draw.text((pad, y), sub_line, font=sub_font, fill=sub_color)
        y += sub_size + 4
        draw.text((pad, y), title, font=title_font, fill=text_color)
    else:
        draw.text((pad, y), title, font=title_font, fill=text_color)
        if year:
            y += title_size + 4
            draw.text((pad, y), str(year), font=sub_font, fill=sub_color)

    return img


def render_poster(
    poster_bytes: bytes,
    session: dict[str, Any],
    width: int,
    height: int,
    fit_mode: str = "crop",
    show_info: bool = True,
    theme: str = "dark",
) -> bytes:
    """Compose a display-ready JPEG from raw poster bytes and session metadata.

    Falls back to the unmodified poster bytes if Pillow is unavailable.
    """
    if not _PIL or not poster_bytes:
        return poster_bytes

    try:
        img = Image.open(io.BytesIO(poster_bytes)).convert("RGB")
        img = _apply_fit(img, width, height, fit_mode)
        if show_info:
            img = _draw_info_bar(img, session, theme)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90, optimize=True)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("[media_player] render failed: %s", exc)
        return poster_bytes
