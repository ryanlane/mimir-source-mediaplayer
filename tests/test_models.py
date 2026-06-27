"""Unit tests for media_player models."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "channels"))

from media_player.models import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.backend == "plex"
        assert s.server_url == ""
        assert s.api_token == ""
        assert s.username == ""
        assert s.verify_ssl is False
        assert s.fit_mode == "crop"
        assert s.show_info is True
        assert s.theme == "dark"

    def test_to_public_dict_masks_api_token(self):
        s = Settings(api_token="super-secret-token-abc123")
        pub = s.to_public_dict()
        assert pub["api_token"] != "super-secret-token-abc123"
        assert "super-secret-token-abc123" not in pub["api_token"]

    def test_to_public_dict_does_not_mask_other_fields(self):
        s = Settings(server_url="http://192.168.1.10:32400", username="ryan")
        pub = s.to_public_dict()
        assert pub["server_url"] == "http://192.168.1.10:32400"
        assert pub["username"] == "ryan"

    def test_from_dict_ignores_unknown_keys(self):
        s = Settings.from_dict({"backend": "jellyfin", "does_not_exist": "value"})
        assert s.backend == "jellyfin"
        assert not hasattr(s, "does_not_exist")

    def test_from_dict_partial(self):
        s = Settings.from_dict({"server_url": "http://10.0.0.5:8096", "backend": "emby"})
        assert s.server_url == "http://10.0.0.5:8096"
        assert s.backend == "emby"
        assert s.api_token == ""   # default

    def test_to_dict_round_trips(self):
        s = Settings(backend="jellyfin", server_url="http://host:8096", api_token="key123",
                     fit_mode="letterbox", show_info=False, theme="light")
        s2 = Settings.from_dict(s.to_dict())
        assert s2.backend == "jellyfin"
        assert s2.server_url == "http://host:8096"
        assert s2.api_token == "key123"
        assert s2.fit_mode == "letterbox"
        assert s2.show_info is False
        assert s2.theme == "light"

    def test_configured_flag(self):
        empty = Settings()
        assert not (empty.server_url and empty.api_token)
        configured = Settings(server_url="http://host:32400", api_token="tok")
        assert configured.server_url and configured.api_token

    def test_merge_via_from_dict(self):
        base = Settings(backend="plex", server_url="http://old:32400")
        merged = Settings.from_dict({**base.to_dict(), "server_url": "http://new:32400"})
        assert merged.server_url == "http://new:32400"
        assert merged.backend == "plex"
