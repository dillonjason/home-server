import logging
import os
import time

import yaml

from cleaner import MediaCleaner
from jellyfin import JellyfinClient
from radarr import RadarrClient
from sonarr import SonarrClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger(__name__)

CONFIG_PATH = os.getenv("CONFIG_PATH", "/config/config.yml")
INTERVAL_SECONDS = int(os.getenv("RUN_INTERVAL_MINUTES", "60")) * 60
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
MIN_FILE_AGE_HOURS = int(os.getenv("MIN_FILE_AGE_HOURS", "24"))


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def build_clients() -> tuple[JellyfinClient, SonarrClient, RadarrClient]:
    return (
        JellyfinClient(url=os.environ["JELLYFIN_URL"], api_key=os.environ["JELLYFIN_API_KEY"]),
        SonarrClient(url=os.environ["SONARR_URL"], api_key=os.environ["SONARR_API_KEY"]),
        RadarrClient(url=os.environ["RADARR_URL"], api_key=os.environ["RADARR_API_KEY"]),
    )


def main():
    if DRY_RUN:
        log.info("DRY RUN mode enabled — no files will be deleted")
    log.info("Media cleaner starting, interval=%dm", INTERVAL_SECONDS // 60)

    while True:
        log.info("Starting cleanup run")
        try:
            config = load_config()
            jellyfin, sonarr, radarr = build_clients()
            MediaCleaner(config, jellyfin, sonarr, radarr, dry_run=DRY_RUN, min_file_age_hours=MIN_FILE_AGE_HOURS).run()
            log.info("Cleanup run complete")
        except Exception as e:
            log.error("Run failed: %s", e, exc_info=True)
        log.info("Next run in %d minutes", INTERVAL_SECONDS // 60)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
