import logging

import requests

log = logging.getLogger(__name__)


class SonarrClient:
    def __init__(self, url: str, api_key: str):
        self.base = url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["X-Api-Key"] = api_key

    def _get(self, path: str, **params) -> dict | list:
        url = f"{self.base}{path}"
        r = self.session.get(url, params=params or None)
        if not r.ok or not r.content:
            log.error("Sonarr request failed: GET %s — status=%d body=%r", url, r.status_code, r.text[:300])
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, data: dict) -> dict:
        r = self.session.put(f"{self.base}{path}", json=data)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> None:
        r = self.session.delete(f"{self.base}{path}")
        r.raise_for_status()

    def find_series(self, title: str) -> dict | None:
        all_series = self._get("/api/v3/series")
        for s in all_series:
            if s["title"].lower() == title.lower():
                return s
        return None

    def get_episodes(self, series_id: int) -> list[dict]:
        return self._get("/api/v3/episode", seriesId=series_id)

    def get_episode_files(self, series_id: int) -> list[dict]:
        return self._get("/api/v3/episodefile", seriesId=series_id)

    def unmonitor_episode(self, episode_id: int, dry_run: bool = False) -> None:
        if dry_run:
            log.info("[DRY RUN] Would unmonitor episode %d", episode_id)
            return
        episode = self._get(f"/api/v3/episode/{episode_id}")
        episode["monitored"] = False
        self._put(f"/api/v3/episode/{episode_id}", episode)
        log.debug("Unmonitored episode %d", episode_id)

    def delete_file(self, file_id: int, dry_run: bool = False) -> None:
        if dry_run:
            log.info("[DRY RUN] Would delete episode file %d", file_id)
            return
        self._delete(f"/api/v3/episodefile/{file_id}")
        log.debug("Deleted episode file %d", file_id)
