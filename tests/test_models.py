"""Unit tests for media_player models."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "channels"))

from media_player.models import MediaServerSettings, Settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.servers == []
        assert s.backend == "plex"
        assert s.server_url == ""
        assert s.api_token == ""
        assert s.username == ""
        assert s.verify_ssl is False
        assert s.fit_mode == "crop"
        assert s.show_info is True
        assert s.theme == "dark"

    def test_to_public_dict_masks_api_token(self):
        s = Settings(servers=[MediaServerSettings(api_token="super-secret-token-abc123")])
        pub = s.to_public_dict()
        assert pub["servers"][0]["api_token"] != "super-secret-token-abc123"
        assert "super-secret-token-abc123" not in pub["servers"][0]["api_token"]

    def test_to_public_dict_does_not_mask_other_fields(self):
        s = Settings(servers=[MediaServerSettings(server_url="http://192.168.1.10:32400", username="ryan")])
        pub = s.to_public_dict()
        assert pub["servers"][0]["server_url"] == "http://192.168.1.10:32400"
        assert pub["servers"][0]["username"] == "ryan"

    def test_from_dict_ignores_unknown_keys(self):
        s = Settings.from_dict({"servers": [{"backend": "jellyfin", "does_not_exist": "value"}]})
        assert s.backend == "jellyfin"
        assert not hasattr(s.servers[0], "does_not_exist")

    def test_from_dict_partial(self):
        s = Settings.from_dict({"server_url": "http://10.0.0.5:8096", "backend": "emby"})
        assert len(s.servers) == 1
        assert s.server_url == "http://10.0.0.5:8096"
        assert s.backend == "emby"
        assert s.api_token == ""   # default

    def test_to_dict_round_trips(self):
        s = Settings(
            servers=[MediaServerSettings(backend="jellyfin", server_url="http://host:8096", api_token="key123")],
            fit_mode="letterbox",
            show_info=False,
            theme="light",
        )
        s2 = Settings.from_dict(s.to_dict())
        assert len(s2.servers) == 1
        assert s2.backend == "jellyfin"
        assert s2.server_url == "http://host:8096"
        assert s2.api_token == "key123"
        assert s2.fit_mode == "letterbox"
        assert s2.show_info is False
        assert s2.theme == "light"

    def test_configured_flag(self):
        empty = Settings()
        assert empty.configured_servers() == []
        configured = Settings(servers=[MediaServerSettings(server_url="http://host:32400", api_token="tok")])
        assert configured.configured_servers() == configured.servers

    def test_merge_via_from_dict(self):
        base = Settings(servers=[MediaServerSettings(backend="plex", server_url="http://old:32400")])
        data = base.to_dict()
        data["servers"][0]["server_url"] = "http://new:32400"
        merged = Settings.from_dict(data)
        assert merged.server_url == "http://new:32400"
        assert merged.backend == "plex"

    def test_multiple_servers_round_trip(self):
        s = Settings.from_dict({
            "servers": [
                {"name": "Plex", "backend": "plex", "server_url": "http://plex:32400", "api_token": "plex-token"},
                {"name": "Jellyfin", "backend": "jellyfin", "server_url": "http://jellyfin:8096", "api_token": "jf-token"},
            ]
        })
        assert [server.backend for server in s.configured_servers()] == ["plex", "jellyfin"]
        assert s.servers[0].id
        assert s.servers[1].id
        assert Settings.from_dict(s.to_dict()).servers[1].server_url == "http://jellyfin:8096"
