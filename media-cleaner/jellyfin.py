import logging

import requests

log = logging.getLogger(__name__)


class JellyfinClient:
    def __init__(self, url: str, api_key: str):
        self.base = url.rstrip("/")
        self.session = requests.Session()
        # Jellyfin prefers the Authorization header; X-Emby-Token is kept for compatibility
        self.session.headers["Authorization"] = (
            f'MediaBrowser Token="{api_key}", Client="media-cleaner", '
            f'Device="docker", DeviceId="media-cleaner", Version="1.0"'
        )
        self.session.headers["X-Emby-Token"] = api_key
        self.session.headers["Accept"] = "application/json"

    def _get(self, path: str, **params) -> dict | list:
        url = f"{self.base}{path}"
        r = self.session.get(url, params=params or None)
        if not r.ok:
            log.error(
                "Jellyfin GET %s — status=%d body=%r",
                url, r.status_code, r.text[:500],
            )
            r.raise_for_status()
        if not r.content:
            log.error("Jellyfin GET %s — empty body (status=%d)", url, r.status_code)
            raise ValueError(f"Empty response from Jellyfin: GET {url}")
        try:
            return r.json()
        except Exception:
            log.error(
                "Jellyfin GET %s — non-JSON body (status=%d) body=%r",
                url, r.status_code, r.text[:500],
            )
            raise

    def get_users(self) -> list[dict]:
        return self._get("/Users")

    def find_series(self, title: str) -> dict | None:
        data = self._get(
            "/Items",
            searchTerm=title,
            IncludeItemTypes="Series",
            Recursive="true",
            Limit=10,
        )
        for item in data.get("Items", []):
            if item["Name"].lower() == title.lower():
                return item
        return None

    def find_movie(self, title: str) -> dict | None:
        data = self._get(
            "/Items",
            searchTerm=title,
            IncludeItemTypes="Movie",
            Recursive="true",
            Limit=10,
        )
        for item in data.get("Items", []):
            if item["Name"].lower() == title.lower():
                return item
        return None

    def get_user_episodes(self, user_id: str, series_id: str) -> list[dict]:
        data = self._get(
            f"/Users/{user_id}/Items",
            ParentId=series_id,
            IncludeItemTypes="Episode",
            Recursive="true",
            Fields="UserData,ProviderIds",
            Limit=500,
        )
        return data.get("Items", [])

    def get_user_item(self, user_id: str, item_id: str) -> dict:
        return self._get(f"/Users/{user_id}/Items/{item_id}")

    def aggregate_episode_status(
        self, series_id: str, users: list[dict]
    ) -> dict[tuple, dict]:
        """Returns {(season, episode): {'watched': bool, 'protected': bool}} across all users."""
        status: dict[tuple, dict] = {}
        series_favorited = False
        for user in users:
            uid = user["Id"]
            try:
                series_item = self.get_user_item(uid, series_id)
                if series_item.get("UserData", {}).get("IsFavorite"):
                    series_favorited = True
            except Exception as e:
                log.warning("Failed to get series item for user %s: %s", user.get("Name"), e)
            try:
                episodes = self.get_user_episodes(uid, series_id)
            except Exception as e:
                log.warning("Failed to get episodes for user %s: %s", user.get("Name"), e)
                continue
            for ep in episodes:
                key = (ep.get("ParentIndexNumber", 0), ep.get("IndexNumber", 0))
                ud = ep.get("UserData", {})
                s = status.setdefault(key, {"watched": False, "protected": False})
                if ud.get("Played"):
                    s["watched"] = True
                if ud.get("IsFavorite"):
                    s["protected"] = True
        if series_favorited:
            for s in status.values():
                s["protected"] = True
        return status

    def get_movie_status(self, item_id: str, users: list[dict]) -> dict:
        """Returns {'watched': bool, 'protected': bool} across all users."""
        status = {"watched": False, "protected": False}
        for user in users:
            uid = user["Id"]
            try:
                item = self.get_user_item(uid, item_id)
            except Exception as e:
                log.warning("Failed to get movie data for user %s: %s", user.get("Name"), e)
                continue
            ud = item.get("UserData", {})
            if ud.get("Played"):
                status["watched"] = True
            if ud.get("IsFavorite"):
                status["protected"] = True
        return status
