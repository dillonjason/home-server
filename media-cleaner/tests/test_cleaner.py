from unittest.mock import MagicMock

import pytest

from cleaner import MediaCleaner


def _make_cleaner(config: dict, dry_run: bool = False):
    jellyfin = MagicMock()
    sonarr = MagicMock()
    radarr = MagicMock()
    cleaner = MediaCleaner(config, jellyfin, sonarr, radarr, dry_run=dry_run)
    return cleaner, jellyfin, sonarr, radarr


def _ep_file(id: int, date: str) -> dict:
    return {"id": id, "dateAdded": date}


def _episode(id: int, file_id: int, season: int, ep: int, air_date: str) -> dict:
    return {
        "id": id,
        "episodeFileId": file_id,
        "seasonNumber": season,
        "episodeNumber": ep,
        "airDateUtc": air_date,
        "hasFile": True,
    }


# --- max_episodes ---

class TestMaxEpisodes:
    def _setup(self, episode_count: int, limit: int, protected_keys: set = None):
        config = {"shows": [{"title": "Test Show", "max_episodes": limit}]}
        cleaner, jellyfin, sonarr, _ = _make_cleaner(config)

        sonarr.find_series.return_value = {"id": 1, "title": "Test Show"}
        jellyfin.find_series.return_value = {"Id": "jf-1", "Name": "Test Show"}
        jellyfin.get_users.return_value = [{"Id": "u1", "Name": "User"}]

        episodes = [_episode(i, i, 1, i, f"2024-01-{i:02d}T00:00:00Z") for i in range(1, episode_count + 1)]
        ep_files = [_ep_file(i, f"2024-01-{i:02d}T00:00:00Z") for i in range(1, episode_count + 1)]

        sonarr.get_episodes.return_value = episodes
        sonarr.get_episode_files.return_value = ep_files

        protected_keys = protected_keys or set()
        ep_status = {
            (1, i): {"watched": True, "protected": (1, i) in protected_keys}
            for i in range(1, episode_count + 1)
        }
        jellyfin.aggregate_episode_status.return_value = ep_status

        return cleaner, sonarr

    def test_under_limit_does_nothing(self):
        cleaner, sonarr = self._setup(episode_count=3, limit=5)
        cleaner.run()
        sonarr.delete_file.assert_not_called()
        sonarr.unmonitor_episode.assert_not_called()

    def test_at_limit_does_nothing(self):
        cleaner, sonarr = self._setup(episode_count=5, limit=5)
        cleaner.run()
        sonarr.delete_file.assert_not_called()

    def test_over_limit_deletes_oldest(self):
        cleaner, sonarr = self._setup(episode_count=7, limit=5)
        cleaner.run()
        assert sonarr.delete_file.call_count == 2
        # Episodes 1 and 2 are oldest and should be deleted
        deleted_file_ids = {call.args[0] for call in sonarr.delete_file.call_args_list}
        assert deleted_file_ids == {1, 2}

    def test_favorited_episodes_are_skipped(self):
        # Episodes 1 and 2 are oldest but episode 1 is favorited
        cleaner, sonarr = self._setup(episode_count=6, limit=5, protected_keys={(1, 1)})
        cleaner.run()
        # Should delete only 1 episode (episode 2, since episode 1 is protected)
        assert sonarr.delete_file.call_count == 1
        deleted_file_id = sonarr.delete_file.call_args.args[0]
        assert deleted_file_id == 2

    def test_dry_run_does_not_delete(self):
        config = {"shows": [{"title": "Test Show", "max_episodes": 2}]}
        cleaner, jellyfin, sonarr, _ = _make_cleaner(config, dry_run=True)
        sonarr.find_series.return_value = {"id": 1, "title": "Test Show"}
        jellyfin.find_series.return_value = {"Id": "jf-1", "Name": "Test Show"}
        jellyfin.get_users.return_value = [{"Id": "u1", "Name": "User"}]
        sonarr.get_episodes.return_value = [_episode(1, 1, 1, 1, "2024-01-01T00:00:00Z"),
                                             _episode(2, 2, 1, 2, "2024-01-02T00:00:00Z"),
                                             _episode(3, 3, 1, 3, "2024-01-03T00:00:00Z")]
        sonarr.get_episode_files.return_value = [_ep_file(1, "2024-01-01T00:00:00Z"),
                                                  _ep_file(2, "2024-01-02T00:00:00Z"),
                                                  _ep_file(3, "2024-01-03T00:00:00Z")]
        jellyfin.aggregate_episode_status.return_value = {
            (1, 1): {"watched": True, "protected": False},
            (1, 2): {"watched": True, "protected": False},
            (1, 3): {"watched": False, "protected": False},
        }
        cleaner.run()
        # dry_run=True means delete_file is called with dry_run=True — the sonarr mock
        # records the call but the real method would no-op
        sonarr.delete_file.assert_called_with(1, True)


# --- delete_after_watched (shows) ---

class TestDeleteAfterWatched:
    def _setup(self, ep_status: dict):
        config = {"shows": [{"title": "Test Show", "delete_after_watched": True}]}
        cleaner, jellyfin, sonarr, _ = _make_cleaner(config)

        sonarr.find_series.return_value = {"id": 1, "title": "Test Show"}
        jellyfin.find_series.return_value = {"Id": "jf-1", "Name": "Test Show"}
        jellyfin.get_users.return_value = [{"Id": "u1", "Name": "User"}]

        episodes = [_episode(1, 1, 1, 1, "2024-01-01T00:00:00Z"),
                    _episode(2, 2, 1, 2, "2024-01-02T00:00:00Z")]
        sonarr.get_episodes.return_value = episodes
        sonarr.get_episode_files.return_value = [_ep_file(1, "2024-01-01T00:00:00Z"),
                                                  _ep_file(2, "2024-01-02T00:00:00Z")]
        jellyfin.aggregate_episode_status.return_value = ep_status
        return cleaner, sonarr

    def test_watched_unwatched_mix(self):
        ep_status = {
            (1, 1): {"watched": True, "protected": False},
            (1, 2): {"watched": False, "protected": False},
        }
        cleaner, sonarr = self._setup(ep_status)
        cleaner.run()
        assert sonarr.delete_file.call_count == 1
        assert sonarr.delete_file.call_args.args[0] == 1

    def test_all_watched_deletes_all(self):
        ep_status = {
            (1, 1): {"watched": True, "protected": False},
            (1, 2): {"watched": True, "protected": False},
        }
        cleaner, sonarr = self._setup(ep_status)
        cleaner.run()
        assert sonarr.delete_file.call_count == 2

    def test_watched_but_favorited_is_kept(self):
        ep_status = {
            (1, 1): {"watched": True, "protected": True},
            (1, 2): {"watched": True, "protected": False},
        }
        cleaner, sonarr = self._setup(ep_status)
        cleaner.run()
        assert sonarr.delete_file.call_count == 1
        assert sonarr.delete_file.call_args.args[0] == 2

    def test_nothing_watched_does_nothing(self):
        ep_status = {
            (1, 1): {"watched": False, "protected": False},
            (1, 2): {"watched": False, "protected": False},
        }
        cleaner, sonarr = self._setup(ep_status)
        cleaner.run()
        sonarr.delete_file.assert_not_called()


# --- movies ---

class TestMovies:
    def _setup(self, watched: bool, protected: bool, has_file: bool = True):
        config = {"movies": [{"title": "Test Movie", "delete_after_watched": True}]}
        cleaner, jellyfin, _, radarr = _make_cleaner(config)

        jellyfin.get_users.return_value = [{"Id": "u1", "Name": "User"}]
        radarr.find_movie.return_value = {"id": 10, "title": "Test Movie", "hasFile": has_file}
        jellyfin.find_movie.return_value = {"Id": "jf-m1", "Name": "Test Movie"}
        jellyfin.get_movie_status.return_value = {"watched": watched, "protected": protected}
        radarr.get_movie_files.return_value = [{"id": 99}]

        return cleaner, radarr

    def test_watched_movie_is_deleted(self):
        cleaner, radarr = self._setup(watched=True, protected=False)
        cleaner.run()
        radarr.delete_file.assert_called_once_with(99, False)
        radarr.unmonitor_movie.assert_called_once()

    def test_unwatched_movie_is_kept(self):
        cleaner, radarr = self._setup(watched=False, protected=False)
        cleaner.run()
        radarr.delete_file.assert_not_called()

    def test_watched_but_favorited_movie_is_kept(self):
        cleaner, radarr = self._setup(watched=True, protected=True)
        cleaner.run()
        radarr.delete_file.assert_not_called()

    def test_movie_with_no_file_is_skipped(self):
        cleaner, radarr = self._setup(watched=True, protected=False, has_file=False)
        cleaner.run()
        radarr.delete_file.assert_not_called()


# --- error resilience ---

class TestErrorResilience:
    def test_show_not_in_sonarr_skips_gracefully(self):
        config = {"shows": [{"title": "Missing Show", "delete_after_watched": True}]}
        cleaner, jellyfin, sonarr, _ = _make_cleaner(config)
        jellyfin.get_users.return_value = [{"Id": "u1", "Name": "User"}]
        sonarr.find_series.return_value = None
        cleaner.run()
        sonarr.delete_file.assert_not_called()

    def test_null_shows_key_does_not_crash(self):
        # YAML `shows:` with only comments parses as None, not []
        cleaner, jellyfin, sonarr, _ = _make_cleaner({"shows": None, "movies": []})
        jellyfin.get_users.return_value = [{"Id": "u1", "Name": "User"}]
        cleaner.run()
        sonarr.delete_file.assert_not_called()

    def test_null_movies_key_does_not_crash(self):
        cleaner, jellyfin, _, radarr = _make_cleaner({"shows": [], "movies": None})
        jellyfin.get_users.return_value = [{"Id": "u1", "Name": "User"}]
        cleaner.run()
        radarr.delete_file.assert_not_called()

    def test_jellyfin_user_failure_continues(self):
        config = {"shows": [{"title": "Test Show", "delete_after_watched": True}]}
        cleaner, jellyfin, sonarr, _ = _make_cleaner(config)
        sonarr.find_series.return_value = {"id": 1, "title": "Test Show"}
        jellyfin.find_series.return_value = {"Id": "jf-1", "Name": "Test Show"}
        jellyfin.get_users.return_value = [{"Id": "u1", "Name": "User"}]
        sonarr.get_episodes.return_value = [_episode(1, 1, 1, 1, "2024-01-01T00:00:00Z")]
        sonarr.get_episode_files.return_value = [_ep_file(1, "2024-01-01T00:00:00Z")]
        # Simulate one user failing — aggregate_episode_status handles this internally
        jellyfin.aggregate_episode_status.return_value = {}
        # No watched status → no deletions
        cleaner.run()
        sonarr.delete_file.assert_not_called()
