import logging

import requests

log = logging.getLogger(__name__)


class JellyfinClient:
    def __init__(self, url: str, api_key: str):
        self.base = url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["X-Emby-Token"] = api_key

    def _get(self, path: str, **params) -> dict | list:
        r = self.session.get(f"{self.base}{path}", params=params or None)
        r.raise_for_status()
        return r.json()

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
        for user in users:
            uid = user["Id"]
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
