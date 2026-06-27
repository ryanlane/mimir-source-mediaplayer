"""Settings model for the Media Player now-playing channel."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from .mimir_utils import SettingsMixin

BACKENDS = ("plex", "jellyfin", "emby")
FIT_MODES = ("crop", "letterbox")


@dataclass
class Settings(SettingsMixin):
    _secret_fields: ClassVar[set] = {"api_token", "token", "secret", "password", "access_token"}

    # Connection
    backend: str = "plex"        # plex | jellyfin | emby
    server_url: str = ""         # e.g. http://192.168.1.10:32400
    api_token: str = ""          # Plex token / Jellyfin-Emby API key  (masked in to_public_dict)
    username: str = ""           # optional: only track sessions from this user
    verify_ssl: bool = False     # set False for self-signed certs on LAN servers

    # Display
    fit_mode: str = "crop"       # crop | letterbox
    show_info: bool = True       # overlay title/year/series on the poster
    theme: str = "dark"          # dark | light info overlay
