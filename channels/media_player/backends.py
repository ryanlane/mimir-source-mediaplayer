"""Backend clients for Plex, Jellyfin, and Emby.

Each backend exposes a single method:
    get_current_session(settings, session) -> dict | None

Returns a normalized session dict or None if nothing is playing.

Normalized session dict:
    {
        "title":        str,           # movie title or episode name
        "year":         int | None,
        "media_type":   str,           # "movie" | "episode" | "unknown"
        "series_title": str | None,    # set for episodes
        "season_num":   int | None,
        "episode_num":  int | None,
        "is_playing":   bool,          # False if paused
        "poster_url":   str | None,    # full URL ready to GET with no extra headers
        "session_key":  str,           # stable key for fingerprinting (item id + playback session)
    }
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("mimir.channels.media_player.backends")


# ── Plex ─────────────────────────────────────────────────────────────────────

def _plex_session(settings, http_session) -> dict[str, Any] | None:
    """Fetch the current playing session from Plex Media Server."""
    url = settings.server_url.rstrip("/") + "/sessions"
    try:
        resp = http_session.get(
            url,
            headers={"Accept": "application/json", "X-Plex-Token": settings.api_token},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.debug("[plex] sessions fetch failed: %s", exc)
        return None

    items = data.get("MediaContainer", {}).get("Metadata") or []
    if not isinstance(items, list):
        items = [items]

    for item in items:
        player = item.get("Player") or {}
        user = item.get("User") or {}

        # Username filter
        if settings.username and user.get("title", "").lower() != settings.username.lower():
            continue

        is_playing = player.get("state", "").lower() == "playing"
        media_type = item.get("type", "unknown")
        title = item.get("title", "")
        year = item.get("year")
        rating_key = str(item.get("ratingKey", ""))

        series_title = None
        season_num = None
        episode_num = None
        poster_path = item.get("thumb", "")

        if media_type == "episode":
            series_title = item.get("grandparentTitle")
            season_num = item.get("parentIndex")
            episode_num = item.get("index")
            # Prefer the series poster over the episode thumbnail
            grandparent_thumb = item.get("grandparentThumb")
            if grandparent_thumb:
                poster_path = grandparent_thumb

        token = settings.api_token
        poster_url = (
            f"{settings.server_url.rstrip('/')}{poster_path}?X-Plex-Token={token}"
            if poster_path and token
            else None
        )

        return {
            "title":        title,
            "year":         int(year) if year else None,
            "media_type":   media_type,
            "series_title": series_title,
            "season_num":   int(season_num) if season_num else None,
            "episode_num":  int(episode_num) if episode_num else None,
            "is_playing":   is_playing,
            "poster_url":   poster_url,
            "session_key":  rating_key,
        }

    return None


# ── Jellyfin / Emby ───────────────────────────────────────────────────────────
# The APIs are nearly identical (Emby was forked into Jellyfin).
# Both accept X-Emby-Token for simple API-key auth.

def _jellyfin_session(settings, http_session) -> dict[str, Any] | None:
    """Fetch the current playing session from Jellyfin or Emby."""
    base = settings.server_url.rstrip("/")
    token = settings.api_token
    try:
        resp = http_session.get(
            f"{base}/Sessions",
            headers={"X-Emby-Token": token},
            timeout=8,
        )
        resp.raise_for_status()
        sessions = resp.json()
    except Exception as exc:
        logger.debug("[jellyfin] sessions fetch failed: %s", exc)
        return None

    if not isinstance(sessions, list):
        return None

    for session in sessions:
        now_playing = session.get("NowPlayingItem")
        if not now_playing:
            continue

        user_name = session.get("UserName", "")
        if settings.username and user_name.lower() != settings.username.lower():
            continue

        play_state = session.get("PlayState") or {}
        is_playing = not play_state.get("IsPaused", True)

        item_id = now_playing.get("Id", "")
        media_type_raw = now_playing.get("Type", "Unknown").lower()
        media_type = "episode" if media_type_raw == "episode" else "movie" if media_type_raw == "movie" else "unknown"

        title = now_playing.get("Name", "")
        year = now_playing.get("ProductionYear")

        series_title = None
        season_num = None
        episode_num = None
        poster_item_id = item_id

        if media_type == "episode":
            series_title = now_playing.get("SeriesName")
            season_num = now_playing.get("ParentIndexNumber")
            episode_num = now_playing.get("IndexNumber")
            series_id = now_playing.get("SeriesId")
            if series_id:
                poster_item_id = series_id

        poster_url = (
            f"{base}/Items/{poster_item_id}/Images/Primary?api_key={token}&fillHeight=800"
            if poster_item_id and token
            else None
        )
        session_id = session.get("Id", item_id)

        return {
            "title":        title,
            "year":         int(year) if year else None,
            "media_type":   media_type,
            "series_title": series_title,
            "season_num":   int(season_num) if season_num else None,
            "episode_num":  int(episode_num) if episode_num else None,
            "is_playing":   is_playing,
            "poster_url":   poster_url,
            "session_key":  session_id,
        }

    return None


# ── Dispatch ─────────────────────────────────────────────────────────────────

def get_current_session(settings, http_session) -> dict[str, Any] | None:
    """Dispatch to the appropriate backend and return a normalized session dict."""
    backend = (settings.backend or "plex").lower()
    if backend == "plex":
        return _plex_session(settings, http_session)
    elif backend in ("jellyfin", "emby"):
        return _jellyfin_session(settings, http_session)
    else:
        logger.warning("[media_player] unknown backend '%s'", backend)
        return None
