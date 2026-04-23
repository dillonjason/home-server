import logging

import requests

log = logging.getLogger(__name__)


class RadarrClient:
    def __init__(self, url: str, api_key: str):
        self.base = url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["X-Api-Key"] = api_key

    def _get(self, path: str, **params) -> dict | list:
        url = f"{self.base}{path}"
        r = self.session.get(url, params=params or None)
        if not r.ok or not r.content:
            log.error("Radarr request failed: GET %s — status=%d body=%r", url, r.status_code, r.text[:300])
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, data: dict) -> dict:
        r = self.session.put(f"{self.base}{path}", json=data)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> None:
        r = self.session.delete(f"{self.base}{path}")
        r.raise_for_status()

    def find_movie(self, title: str) -> dict | None:
        all_movies = self._get("/api/v3/movie")
        for m in all_movies:
            if m["title"].lower() == title.lower():
                return m
        return None

    def get_movie_files(self, movie_id: int) -> list[dict]:
        return self._get("/api/v3/moviefile", movieId=movie_id)

    def unmonitor_movie(self, movie_id: int, dry_run: bool = False) -> None:
        if dry_run:
            log.info("[DRY RUN] Would unmonitor movie %d", movie_id)
            return
        movie = self._get(f"/api/v3/movie/{movie_id}")
        movie["monitored"] = False
        self._put(f"/api/v3/movie/{movie_id}", movie)
        log.debug("Unmonitored movie %d", movie_id)

    def delete_file(self, file_id: int, dry_run: bool = False) -> None:
        if dry_run:
            log.info("[DRY RUN] Would delete movie file %d", file_id)
            return
        self._delete(f"/api/v3/moviefile/{file_id}")
        log.debug("Deleted movie file %d", file_id)
