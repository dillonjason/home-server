import logging

from jellyfin import JellyfinClient
from radarr import RadarrClient
from sonarr import SonarrClient

log = logging.getLogger(__name__)


class MediaCleaner:
    def __init__(
        self,
        config: dict,
        jellyfin: JellyfinClient,
        sonarr: SonarrClient,
        radarr: RadarrClient,
        dry_run: bool = False,
    ):
        self.config = config
        self.jellyfin = jellyfin
        self.sonarr = sonarr
        self.radarr = radarr
        self.dry_run = dry_run

    def run(self):
        users = self.jellyfin.get_users()
        log.info("Found %d Jellyfin user(s)", len(users))

        for show_cfg in self.config.get("shows", []):
            try:
                self._process_show(show_cfg, users)
            except Exception as e:
                log.error("Error processing show '%s': %s", show_cfg.get("title"), e, exc_info=True)

        for movie_cfg in self.config.get("movies", []):
            try:
                self._process_movie(movie_cfg, users)
            except Exception as e:
                log.error("Error processing movie '%s': %s", movie_cfg.get("title"), e, exc_info=True)

    def _process_show(self, cfg: dict, users: list[dict]):
        title = cfg["title"]
        log.info("Processing show: %s", title)

        sonarr_series = self.sonarr.find_series(title)
        if not sonarr_series:
            log.warning("Show '%s' not found in Sonarr — skipping", title)
            return

        jf_series = self.jellyfin.find_series(title)
        if not jf_series:
            log.warning("Show '%s' not found in Jellyfin — watched/favorite status unavailable", title)
            ep_status: dict[tuple, dict] = {}
        else:
            ep_status = self.jellyfin.aggregate_episode_status(jf_series["Id"], users)

        episodes = self.sonarr.get_episodes(sonarr_series["id"])
        ep_files = self.sonarr.get_episode_files(sonarr_series["id"])
        ep_by_file_id = {ep["episodeFileId"]: ep for ep in episodes if ep.get("hasFile")}

        if "max_episodes" in cfg:
            self._apply_max_episodes(cfg["max_episodes"], ep_files, ep_by_file_id, ep_status)
        elif cfg.get("delete_after_watched"):
            self._apply_delete_after_watched_show(ep_files, ep_by_file_id, ep_status)

    def _apply_max_episodes(
        self,
        limit: int,
        ep_files: list[dict],
        ep_by_file_id: dict[int, dict],
        ep_status: dict[tuple, dict],
    ):
        if len(ep_files) <= limit:
            log.info("Episode count %d is within limit %d — nothing to do", len(ep_files), limit)
            return

        def sort_key(ef: dict) -> str:
            ep = ep_by_file_id.get(ef["id"])
            if ep:
                return ep.get("airDateUtc") or ef.get("dateAdded", "")
            return ef.get("dateAdded", "")

        sorted_files = sorted(ep_files, key=sort_key)
        to_delete = len(ep_files) - limit
        deleted = 0

        for ef in sorted_files:
            if deleted >= to_delete:
                break
            ep = ep_by_file_id.get(ef["id"])
            if not ep:
                log.warning("Episode file %d has no matching episode record", ef["id"])
                continue
            key = (ep.get("seasonNumber", 0), ep.get("episodeNumber", 0))
            if ep_status.get(key, {}).get("protected"):
                log.info("Skipping favorited S%02dE%02d", key[0], key[1])
                continue
            log.info("Deleting S%02dE%02d (file %d) — over max limit of %d", key[0], key[1], ef["id"], limit)
            self.sonarr.unmonitor_episode(ep["id"], self.dry_run)
            self.sonarr.delete_file(ef["id"], self.dry_run)
            deleted += 1

        if deleted < to_delete:
            log.warning(
                "Deleted %d of %d excess episodes — remainder may be favorited", deleted, to_delete
            )

    def _apply_delete_after_watched_show(
        self,
        ep_files: list[dict],
        ep_by_file_id: dict[int, dict],
        ep_status: dict[tuple, dict],
    ):
        for ef in ep_files:
            ep = ep_by_file_id.get(ef["id"])
            if not ep:
                continue
            key = (ep.get("seasonNumber", 0), ep.get("episodeNumber", 0))
            status = ep_status.get(key, {})
            if status.get("protected"):
                log.info("Skipping favorited S%02dE%02d", key[0], key[1])
                continue
            if status.get("watched"):
                log.info("Deleting watched S%02dE%02d (file %d)", key[0], key[1], ef["id"])
                self.sonarr.unmonitor_episode(ep["id"], self.dry_run)
                self.sonarr.delete_file(ef["id"], self.dry_run)

    def _process_movie(self, cfg: dict, users: list[dict]):
        title = cfg["title"]
        log.info("Processing movie: %s", title)

        if not cfg.get("delete_after_watched"):
            log.warning("Movie '%s' has no supported rule — skipping", title)
            return

        radarr_movie = self.radarr.find_movie(title)
        if not radarr_movie:
            log.warning("Movie '%s' not found in Radarr — skipping", title)
            return

        if not radarr_movie.get("hasFile"):
            log.info("Movie '%s' has no file — nothing to delete", title)
            return

        jf_movie = self.jellyfin.find_movie(title)
        if not jf_movie:
            log.warning("Movie '%s' not found in Jellyfin — skipping", title)
            return

        status = self.jellyfin.get_movie_status(jf_movie["Id"], users)

        if status["protected"]:
            log.info("Movie '%s' is favorited — skipping", title)
            return

        if status["watched"]:
            log.info("Deleting watched movie '%s'", title)
            for mf in self.radarr.get_movie_files(radarr_movie["id"]):
                self.radarr.unmonitor_movie(radarr_movie["id"], self.dry_run)
                self.radarr.delete_file(mf["id"], self.dry_run)
