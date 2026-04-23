import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jellyfin import JellyfinClient


def _make_client() -> JellyfinClient:
    client = JellyfinClient(url="http://jellyfin:8096", api_key="testkey")
    return client


def _ep(season: int, ep_num: int, played: bool = False, favorite: bool = False) -> dict:
    return {
        "ParentIndexNumber": season,
        "IndexNumber": ep_num,
        "UserData": {"Played": played, "IsFavorite": favorite},
    }


def _series_item(favorited: bool) -> dict:
    return {"UserData": {"IsFavorite": favorited}}


class TestAggregateEpisodeStatus:
    def test_series_favorited_protects_all_episodes(self):
        client = _make_client()
        client.get_user_item = MagicMock(return_value=_series_item(favorited=True))
        client.get_user_episodes = MagicMock(return_value=[
            _ep(1, 1, played=True, favorite=False),
            _ep(1, 2, played=False, favorite=False),
        ])

        status = client.aggregate_episode_status("s1", [{"Id": "u1", "Name": "User"}])

        assert status[(1, 1)]["protected"] is True
        assert status[(1, 2)]["protected"] is True

    def test_series_not_favorited_leaves_episode_flags_unchanged(self):
        client = _make_client()
        client.get_user_item = MagicMock(return_value=_series_item(favorited=False))
        client.get_user_episodes = MagicMock(return_value=[
            _ep(1, 1, played=True, favorite=True),
            _ep(1, 2, played=True, favorite=False),
        ])

        status = client.aggregate_episode_status("s1", [{"Id": "u1", "Name": "User"}])

        assert status[(1, 1)]["protected"] is True   # episode-level favorite
        assert status[(1, 2)]["protected"] is False

    def test_any_user_series_favorite_protects_all(self):
        client = _make_client()
        client.get_user_item = MagicMock(side_effect=lambda uid, _: _series_item(uid == "u2"))
        client.get_user_episodes = MagicMock(return_value=[
            _ep(1, 1, played=True, favorite=False),
        ])

        users = [{"Id": "u1", "Name": "User1"}, {"Id": "u2", "Name": "User2"}]
        status = client.aggregate_episode_status("s1", users)

        assert status[(1, 1)]["protected"] is True

    def test_series_item_failure_does_not_crash(self):
        client = _make_client()
        client.get_user_item = MagicMock(side_effect=Exception("network error"))
        client.get_user_episodes = MagicMock(return_value=[
            _ep(1, 1, played=True, favorite=False),
        ])

        status = client.aggregate_episode_status("s1", [{"Id": "u1", "Name": "User"}])

        # Series item failure is non-fatal; episode-level data still returned
        assert (1, 1) in status
        assert status[(1, 1)]["protected"] is False
