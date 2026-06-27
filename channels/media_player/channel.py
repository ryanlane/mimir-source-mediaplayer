"""Media Player now-playing channel for Mimir.

Supports Plex, Jellyfin, and Emby.  Polls the configured server for active
playback sessions and:
  - Fires push events with is_playing=True when a video starts / changes.
  - Fires is_playing=False when playback stops (so the now-playing interrupt
    service can revert the scene to its base content).
  - Renders the current video's poster at the requested resolution on
    request_image() calls.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .models import Settings
from .mimir_utils import http_session as _make_session
from . import backends
from . import renderer as _renderer

logger = logging.getLogger("mimir.channels.media_player")

_POLL_INTERVAL         = 15   # seconds between polls (no webhook activity)
_POLL_INTERVAL_WEBHOOK = 120  # seconds between polls when webhooks are active
_USER_AGENT = "MimirMediaPlayer/1.0 (https://github.com/ryanlane/mimir)"
_PLUGIN_ID = "com.mimir.mediaplayer"


class MediaPlayerChannel:
    def __init__(self, channel_dir: str, config: Optional[Dict[str, Any]] = None):
        self.channel_dir = Path(channel_dir)
        self.data_dir = self.channel_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self._settings_path = self.data_dir / "settings.json"
        self._meta = self._load_plugin_json()
        self.id = self._meta.get("id", _PLUGIN_ID)
        self.settings = self._load_settings()
        if config:
            self.settings = Settings.from_dict({**self.settings.to_dict(), **config})
            self._save_settings()

        # HTTP session (shared across requests; updated when settings change)
        self._http = self._make_http()

        # Cached state
        self._cached_session: Optional[Dict[str, Any]] = None
        self._cached_status: str = "not_started"
        self._cached_poster: Optional[bytes] = None    # bytes for the last poster URL
        self._cached_poster_url: Optional[str] = None  # URL those bytes came from
        self._image_cache: Dict[str, Dict[str, Any]] = {}

        # Push support
        self.supports_push = True
        self._push_listener: Optional[Callable] = None
        self._was_playing: bool = False
        self._last_session_fp: Optional[str] = None
        self._poller_task: Optional[asyncio.Task] = None

        # Webhook state (Plex only)
        self._webhook_last_event: float = 0.0  # epoch time of last received webhook

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _load_plugin_json(self) -> Dict[str, Any]:
        try:
            with open(self.channel_dir / "plugin.json") as f:
                return json.load(f)
        except Exception:
            return {}

    def _make_http(self):
        sess = _make_session(_USER_AGENT)
        sess.verify = self.settings.verify_ssl
        return sess

    # ── Settings ──────────────────────────────────────────────────────────────

    def _load_settings(self) -> Settings:
        try:
            return Settings.from_dict(json.loads(self._settings_path.read_text()))
        except FileNotFoundError:
            return Settings()
        except Exception as exc:
            logger.warning("[media_player] could not load settings: %s", exc)
            return Settings()

    def _save_settings(self) -> None:
        try:
            self._settings_path.write_text(json.dumps(self.settings.to_dict(), indent=2))
        except Exception as exc:
            logger.warning("[media_player] could not save settings: %s", exc)

    def _masked_settings(self) -> Dict[str, Any]:
        return {
            **self.settings.to_public_dict(),
            "configured": bool(self.settings.server_url and self.settings.api_token),
        }

    # ── Push support ──────────────────────────────────────────────────────────

    def register_listener(self, callback: Callable) -> None:
        self._push_listener = callback
        logger.info("[media_player] push listener registered")

    def _session_fp(self, session: Dict[str, Any]) -> str:
        return f"{session['session_key']}|{session['is_playing']}"

    def _fire_push(self, session: Dict[str, Any]) -> None:
        if not self._push_listener:
            return
        fp = self._session_fp(session)
        payload = {
            "is_playing":   session["is_playing"],
            "title":        session.get("title"),
            "year":         session.get("year"),
            "media_type":   session.get("media_type"),
            "series_title": session.get("series_title"),
            "season_num":   session.get("season_num"),
            "episode_num":  session.get("episode_num"),
            "session_key":  session.get("session_key"),
        }
        try:
            self._push_listener({
                "channel_id": self.id,
                "event_type": "update",
                "payload":    payload,
                "ts":         time.time(),
                "hash":       hashlib.md5(fp.encode()).hexdigest(),
            })
        except Exception as exc:
            logger.warning("[media_player] push fire failed: %s", exc)

    def _fire_stop(self) -> None:
        if not self._push_listener:
            return
        try:
            self._push_listener({
                "channel_id": self.id,
                "event_type": "update",
                "payload":    {"is_playing": False},
                "ts":         time.time(),
                "hash":       hashlib.md5(b"stopped").hexdigest(),
            })
        except Exception as exc:
            logger.warning("[media_player] stop-event fire failed: %s", exc)

    # ── Webhook (Plex only) ───────────────────────────────────────────────────

    def _normalize_webhook_metadata(self, metadata: Dict[str, Any], is_playing: bool) -> Dict[str, Any]:
        """Build a session dict from a Plex webhook Metadata block."""
        media_type = metadata.get("type", "movie")  # "movie" | "episode" | "track"
        if media_type == "episode":
            thumb_path   = metadata.get("grandparentThumb") or metadata.get("thumb", "")
            series_title = metadata.get("grandparentTitle")
            season_num   = metadata.get("parentIndex")
            episode_num  = metadata.get("index")
        else:
            thumb_path   = metadata.get("thumb", "")
            series_title = None
            season_num   = None
            episode_num  = None

        poster_url = None
        if thumb_path and self.settings.server_url and self.settings.api_token:
            base = self.settings.server_url.rstrip("/")
            poster_url = f"{base}{thumb_path}?X-Plex-Token={self.settings.api_token}"

        return {
            "title":        metadata.get("title", "Unknown"),
            "year":         metadata.get("year"),
            "media_type":   media_type,
            "series_title": series_title,
            "season_num":   season_num,
            "episode_num":  episode_num,
            "is_playing":   is_playing,
            "poster_url":   poster_url,
            "session_key":  str(metadata.get("ratingKey", f"wh-{time.time()}")),
        }

    def process_plex_webhook(self, data: Dict[str, Any]) -> None:
        """Handle a parsed Plex webhook payload dict. Called from the POST /webhook endpoint."""
        event = data.get("event", "")

        # Honour username filter
        if self.settings.username:
            account = data.get("Account", {}).get("title", "")
            if account.lower() != self.settings.username.lower():
                logger.debug("[media_player] webhook ignored — account %r != filter %r", account, self.settings.username)
                return

        metadata = data.get("Metadata", {})
        self._webhook_last_event = time.time()

        if event in ("media.play", "media.resume"):
            session = self._normalize_webhook_metadata(metadata, is_playing=True)
            fp = self._session_fp(session)
            self._cached_session = session
            self._cached_status = "ok"
            self._was_playing = True
            if fp != self._last_session_fp:
                self._last_session_fp = fp
                self._image_cache.clear()
                self._cached_poster = None
                self._cached_poster_url = None
                self._fire_push(session)
                logger.info("[media_player] webhook %s — %s: %s", event, session.get("media_type"), session.get("title"))

        elif event == "media.pause":
            if self._cached_session:
                session = {**self._cached_session, "is_playing": False}
                self._cached_session = session
                fp = self._session_fp(session)
                if fp != self._last_session_fp:
                    self._last_session_fp = fp
                    self._fire_push(session)
            self._was_playing = False
            logger.info("[media_player] webhook pause")

        elif event == "media.stop":
            self._cached_session = None
            self._cached_status = "no_session"
            if self._was_playing:
                self._was_playing = False
                self._last_session_fp = None
                self._fire_stop()
            logger.info("[media_player] webhook stop")

    # ── Polling ───────────────────────────────────────────────────────────────

    def _fetch_session(self) -> tuple[Optional[Dict[str, Any]], str]:
        if not self.settings.server_url or not self.settings.api_token:
            return None, "not_configured"
        try:
            session = backends.get_current_session(self.settings, self._http)
            return session, "ok" if session is not None else "no_session"
        except Exception as exc:
            logger.warning("[media_player] poll error: %s", exc)
            return None, "error"

    async def _poll_loop(self) -> None:
        while True:
            try:
                loop = asyncio.get_event_loop()
                session, status = await loop.run_in_executor(None, self._fetch_session)
                self._cached_session = session
                self._cached_status = status

                if session:
                    fp = self._session_fp(session)
                    if fp != self._last_session_fp:
                        self._last_session_fp = fp
                        self._fire_push(session)
                        logger.info(
                            "[media_player] session change — %s: %s (%s)",
                            session.get("media_type"), session.get("title"), "playing" if session["is_playing"] else "paused",
                        )
                    self._was_playing = bool(session.get("is_playing"))
                elif self._was_playing:
                    self._was_playing = False
                    self._last_session_fp = None
                    self._fire_stop()
                    logger.info("[media_player] playback stopped, stop event fired")
            except Exception as exc:
                logger.warning("[media_player] poller loop error: %s", exc)
            # Back off if Plex webhooks are actively delivering events
            webhook_age = time.time() - self._webhook_last_event
            interval = _POLL_INTERVAL_WEBHOOK if webhook_age < 300 else _POLL_INTERVAL
            await asyncio.sleep(interval)

    def _ensure_poller(self) -> None:
        if self._poller_task is None or self._poller_task.done():
            try:
                self._poller_task = asyncio.get_event_loop().create_task(self._poll_loop())
            except RuntimeError:
                pass

    async def _warm_cache(self) -> None:
        loop = asyncio.get_event_loop()
        self._cached_session, self._cached_status = await loop.run_in_executor(None, self._fetch_session)

    # ── Poster fetch & render ─────────────────────────────────────────────────

    def _fetch_poster(self, poster_url: str) -> Optional[bytes]:
        """Download poster bytes; returns None on failure."""
        if self._cached_poster_url == poster_url and self._cached_poster:
            return self._cached_poster
        try:
            resp = self._http.get(poster_url, timeout=15, stream=False)
            resp.raise_for_status()
            self._cached_poster = resp.content
            self._cached_poster_url = poster_url
            return self._cached_poster
        except Exception as exc:
            logger.warning("[media_player] poster fetch failed: %s", exc)
            return None

    def _render(self, poster_bytes: bytes, session: Dict[str, Any], width: int, height: int) -> bytes:
        return _renderer.render_poster(
            poster_bytes,
            session,
            width,
            height,
            fit_mode=self.settings.fit_mode,
            show_info=self.settings.show_info,
            theme=self.settings.theme,
        )

    # ── request_image ─────────────────────────────────────────────────────────

    async def request_image(self, request_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        rd = request_data or {}
        settings_block = rd.get("settings", {})
        width  = int(settings_block.get("resolution", [800, 480])[0])
        height = int(settings_block.get("resolution", [800, 480])[1])

        self._ensure_poller()
        if self._cached_status == "not_started":
            await self._warm_cache()

        if self._cached_status == "not_configured":
            return {"success": False, "error": "not_configured"}

        session = self._cached_session
        if not session:
            return {"success": False, "error": "no_session"}

        poster_url = session.get("poster_url")
        if not poster_url:
            return {"success": False, "error": "no_poster_url"}

        # Cache key: session fingerprint + dimensions + display settings
        fp = self._session_fp(session)
        cache_key = f"{fp}|{width}x{height}|{self.settings.fit_mode}|{self.settings.show_info}|{self.settings.theme}"
        cached = self._image_cache.get(cache_key)
        if cached:
            return self._build_response(cached, session, width, height, hit=True)

        loop = asyncio.get_event_loop()
        poster_bytes = await loop.run_in_executor(None, self._fetch_poster, poster_url)
        if not poster_bytes:
            return {"success": False, "error": "poster_fetch_failed"}

        img_bytes = await loop.run_in_executor(None, self._render, poster_bytes, session, width, height)

        sha = hashlib.sha256(img_bytes).hexdigest()
        entry = {
            "bytes":        img_bytes,
            "content_type": "image/jpeg",
            "format":       "jpeg",
            "sha256":       sha,
            "description":  self._description(session),
        }
        self._image_cache[cache_key] = entry
        return self._build_response(entry, session, width, height, hit=False)

    def _description(self, session: Dict[str, Any]) -> str:
        title = session.get("title", "Unknown")
        if session.get("media_type") == "episode" and session.get("series_title"):
            return f"Now playing: {session['series_title']} — {title}"
        return f"Now playing: {title}"

    def _build_response(self, entry: Dict[str, Any], session: Dict[str, Any], width: int, height: int, hit: bool) -> Dict[str, Any]:
        return {
            "success":             True,
            "bytes":               entry["bytes"],
            "content_type":        entry["content_type"],
            "format":              entry["format"],
            "sha256":              entry["sha256"],
            "preferred_transport": "bytes",
            "width":               width,
            "height":              height,
            "description":         entry["description"],
            "cache_hit":           hit,
            "metadata": {
                "title":        session.get("title"),
                "year":         session.get("year"),
                "media_type":   session.get("media_type"),
                "series_title": session.get("series_title"),
                "season_num":   session.get("season_num"),
                "episode_num":  session.get("episode_num"),
                "is_playing":   session.get("is_playing"),
            },
        }

    # ── Manifest ──────────────────────────────────────────────────────────────

    def get_manifest(self) -> Dict[str, Any]:
        return {
            "id":          self.id,
            "name":        self._meta.get("name", "Media Player Now Playing"),
            "version":     self._meta.get("version", "1.0.0"),
            "description": self._meta.get("description", ""),
            "icon":        self._meta.get("icon", "tv"),
            "capabilities": {
                "supports_upload":      False,
                "supports_subchannels": False,
                "supports_push":        True,
                "supports_now_playing": True,
            },
            "ui": {
                "components": {"manager": f"/api/channels/{self.id}/ui/manage.esm.js"},
                "elements":   {"manager": "x-mediaplayer-manager"},
            },
            "healthy":    True,
            "configured": bool(self.settings.server_url and self.settings.api_token),
            "backend":    self.settings.backend,
        }

    # ── FastAPI router ────────────────────────────────────────────────────────

    def get_router(self) -> APIRouter:
        router = APIRouter()
        _ui_dir = self.channel_dir / "ui"

        @router.get("/ui/{filename:path}")
        async def serve_ui(filename: str):
            from fastapi.responses import FileResponse
            from fastapi import HTTPException
            file_path = (_ui_dir / filename).resolve()
            try:
                file_path.relative_to(_ui_dir.resolve())
            except ValueError:
                raise HTTPException(403)
            if not file_path.exists():
                raise HTTPException(404)
            return FileResponse(str(file_path))

        @router.get("/manifest")
        async def manifest():
            return JSONResponse(self.get_manifest())

        @router.get("/status")
        async def status():
            self._ensure_poller()
            return JSONResponse({
                "status":  self._cached_status,
                "session": self._cached_session,
            })

        @router.get("/settings")
        async def get_settings():
            return JSONResponse({"success": True, "settings": self._masked_settings()})

        @router.put("/settings")
        async def put_settings(request: Request):
            try:
                body = await request.json()
            except Exception:
                return JSONResponse({"success": False, "error": "invalid JSON"}, status_code=400)

            allowed = {"backend", "server_url", "api_token", "username", "verify_ssl",
                       "fit_mode", "show_info", "theme"}
            self.settings = Settings.from_dict({
                **self.settings.to_dict(),
                **{k: body[k] for k in allowed if k in body},
            })
            self._save_settings()
            self._http = self._make_http()  # rebuild session in case verify_ssl changed
            self._image_cache.clear()       # invalidate render cache
            self._cached_poster = None
            self._cached_poster_url = None
            return JSONResponse({"success": True, "settings": self._masked_settings()})

        @router.post("/webhook")
        async def plex_webhook(request: Request):
            """Receive Plex webhook events (Plex Pass required).
            Configure this URL in Plex: Settings → Webhooks → Add Webhook.
            """
            if self.settings.backend != "plex":
                return JSONResponse({"ok": False, "error": "webhook only supported for plex backend"}, status_code=400)
            try:
                form = await request.form()
                payload_str = form.get("payload", "")
                if not payload_str:
                    return JSONResponse({"ok": False, "error": "missing payload field"}, status_code=400)
                data = json.loads(payload_str)
            except Exception as exc:
                logger.warning("[media_player] webhook parse error: %s", exc)
                return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
            self.process_plex_webhook(data)
            return JSONResponse({"ok": True})

        @router.post("/request-image")
        async def request_image(request: Request):
            try:
                body = await request.json()
            except Exception:
                body = {}
            result = await self.request_image(body)
            if result.get("preferred_transport") == "bytes" and result.get("bytes"):
                from fastapi.responses import Response
                return Response(content=result["bytes"], media_type=result.get("content_type", "image/jpeg"))
            return JSONResponse(result)

        return router
