"""Unit tests for media_player channel behavior."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "channels"))

from media_player.channel import MediaPlayerChannel
from media_player.models import MediaServerSettings, Settings


def test_fetch_session_prefers_playing_session_across_servers(tmp_path, monkeypatch):
    channel = MediaPlayerChannel(str(tmp_path))
    plex = MediaServerSettings(
        id="plex-1",
        name="Plex",
        backend="plex",
        server_url="http://plex:32400",
        api_token="plex-token",
    )
    jellyfin = MediaServerSettings(
        id="jellyfin-1",
        name="Jellyfin",
        backend="jellyfin",
        server_url="http://jellyfin:8096",
        api_token="jf-token",
    )
    channel.settings = Settings(servers=[plex, jellyfin])

    def fake_get_current_session(server, _http):
        if server.id == "plex-1":
            return {
                "title": "Paused Movie",
                "year": 2001,
                "media_type": "movie",
                "series_title": None,
                "season_num": None,
                "episode_num": None,
                "is_playing": False,
                "poster_url": "http://plex/poster.jpg",
                "session_key": "paused",
            }
        return {
            "title": "Playing Movie",
            "year": 2002,
            "media_type": "movie",
            "series_title": None,
            "season_num": None,
            "episode_num": None,
            "is_playing": True,
            "poster_url": "http://jellyfin/poster.jpg",
            "session_key": "playing",
        }

    monkeypatch.setattr("media_player.channel.backends.get_current_session", fake_get_current_session)

    session, status = channel._fetch_session()

    assert status == "ok"
    assert session["title"] == "Playing Movie"
    assert session["_server_id"] == "jellyfin-1"
    assert session["server_name"] == "Jellyfin"
    assert session["backend"] == "jellyfin"
