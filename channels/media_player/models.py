"""Settings model for the Media Player now-playing channel."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

from .mimir_utils import SettingsMixin

BACKENDS = ("plex", "jellyfin", "emby")
FIT_MODES = ("crop", "letterbox")


@dataclass
class MediaServerSettings(SettingsMixin):
    _secret_fields: ClassVar[set] = {"api_token", "token", "secret", "password", "access_token"}

    id: str = ""
    name: str = ""
    backend: str = "plex"        # plex | jellyfin | emby
    server_url: str = ""         # e.g. http://192.168.1.10:32400
    api_token: str = ""          # Plex token / Jellyfin-Emby API key  (masked in to_public_dict)
    username: str = ""           # optional: only track sessions from this user
    verify_ssl: bool = False     # set False for self-signed certs on LAN servers
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MediaServerSettings":
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        server = cls(**{k: v for k, v in data.items() if k in known})
        server.backend = (server.backend or "plex").lower()
        if server.backend not in BACKENDS:
            server.backend = "plex"
        if not server.id:
            server.id = make_server_id(server.backend, server.server_url, server.username)
        if not server.name:
            server.name = server.backend.capitalize()
        return server

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.server_url and self.api_token)


def make_server_id(backend: str, server_url: str, username: str = "") -> str:
    source = f"{backend.lower()}|{server_url.strip().rstrip('/')}|{username.strip().lower()}"
    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]


@dataclass
class Settings(SettingsMixin):
    _secret_fields: ClassVar[set] = {"api_token", "token", "secret", "password", "access_token"}

    # Connections
    servers: list[MediaServerSettings] = field(default_factory=list)

    # Display
    fit_mode: str = "crop"       # crop | letterbox
    show_info: bool = True       # overlay title/year/series on the poster
    theme: str = "dark"          # dark | light info overlay

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        if not isinstance(data, dict):
            return cls()

        servers_data = data.get("servers")
        servers: list[MediaServerSettings] = []
        if isinstance(servers_data, list):
            servers = [MediaServerSettings.from_dict(item) for item in servers_data if isinstance(item, dict)]

        legacy_has_connection = any(data.get(key) for key in ("server_url", "api_token", "backend", "username"))
        if not servers and legacy_has_connection:
            servers = [MediaServerSettings.from_dict({
                "backend": data.get("backend", "plex"),
                "server_url": data.get("server_url", ""),
                "api_token": data.get("api_token", ""),
                "username": data.get("username", ""),
                "verify_ssl": data.get("verify_ssl", False),
            })]

        return cls(
            servers=servers,
            fit_mode=data.get("fit_mode", "crop") if data.get("fit_mode") in FIT_MODES else "crop",
            show_info=data.get("show_info", True) is not False,
            theme=data.get("theme", "dark") if data.get("theme") in ("dark", "light") else "dark",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "servers": [asdict(server) for server in self.servers],
            "fit_mode": self.fit_mode,
            "show_info": self.show_info,
            "theme": self.theme,
        }

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "servers": [server.to_public_dict() for server in self.servers],
            "fit_mode": self.fit_mode,
            "show_info": self.show_info,
            "theme": self.theme,
        }

    def configured_servers(self) -> list[MediaServerSettings]:
        return [server for server in self.servers if server.configured]

    def get_server(self, server_id: str | None) -> MediaServerSettings | None:
        if server_id:
            for server in self.servers:
                if server.id == server_id:
                    return server
        return self.servers[0] if self.servers else None

    def first_server(self, backend: str | None = None) -> MediaServerSettings | None:
        for server in self.servers:
            if backend is None or server.backend == backend:
                return server
        return None

    @property
    def backend(self) -> str:
        server = self.first_server()
        return server.backend if server else "plex"

    @property
    def server_url(self) -> str:
        server = self.first_server()
        return server.server_url if server else ""

    @property
    def api_token(self) -> str:
        server = self.first_server()
        return server.api_token if server else ""

    @property
    def username(self) -> str:
        server = self.first_server()
        return server.username if server else ""

    @property
    def verify_ssl(self) -> bool:
        server = self.first_server()
        return server.verify_ssl if server else False
