import logging
from datetime import date, timedelta
from config import LOCATIONS
from db import get_engine
from weather_etl import process_location

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 3


def get_date_range():
    """Return start and end date strings covering the last LOOKBACK_DAYS days."""
    end_date = date.today() - timedelta(days=1)  # yesterday
    start_date = end_date - timedelta(days=LOOKBACK_DAYS - 1)
    return start_date.isoformat(), end_date.isoformat()


def main():
    start_date, end_date = get_date_range()
    logger.info(f"Running incremental update for {start_date} to {end_date}")

    engine = get_engine()
    results = []

    for location in LOCATIONS:
        result = process_location(location, start_date, end_date, engine)
        results.append(result)

    successes = [r for r in results if r["status"] == "success"]
    failures = [r for r in results if r["status"] == "failed"]

    logger.info("=" * 50)
    logger.info(f"Run complete: {len(successes)} succeeded, {len(failures)} failed")

    if failures:
        logger.warning("Failed locations:")
        for f in failures:
            logger.warning(f"  - {f['location']}: {f['error']}")
        exit(1)


if __name__ == "__main__":
    main()