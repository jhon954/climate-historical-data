import logging
import requests
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from config import LOCATIONS, START_DATE, END_DATE
from db import get_engine

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "relative_humidity_2m_mean",
    "wind_speed_10m_max",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_weather_data(location: dict) -> pd.DataFrame:
    """Fetch historical daily weather data for one location.

    Raises:
        requests.exceptions.RequestException: if the API call fails.
        KeyError: if the expected 'daily' field is missing from the response.
    """
    params = {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": ",".join(DAILY_VARS),
        "timezone": "America/Bogota",
    }

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "daily" not in data:
        raise KeyError(f"'daily' field missing in API response: {data}")

    df = pd.DataFrame(data["daily"])
    df["location_id"] = location["id"]

    df = df.rename(columns={
        "time": "date",
        "temperature_2m_max": "temp_max",
        "temperature_2m_min": "temp_min",
        "temperature_2m_mean": "temp_mean",
        "precipitation_sum": "precipitation",
        "relative_humidity_2m_mean": "humidity",
        "wind_speed_10m_max": "wind_speed",
    })

    return df


def upsert_weather_data(df: pd.DataFrame, engine):
    """Insert or update weather records using ON CONFLICT.

    Raises:
        SQLAlchemyError: if the database operation fails.
    """
    records = df.to_dict(orient="records")

    upsert_query = text("""
        INSERT INTO daily_weather
            (location_id, date, temp_max, temp_min, temp_mean, precipitation, humidity, wind_speed)
        VALUES
            (:location_id, :date, :temp_max, :temp_min, :temp_mean, :precipitation, :humidity, :wind_speed)
        ON CONFLICT (location_id, date)
        DO UPDATE SET
            temp_max = EXCLUDED.temp_max,
            temp_min = EXCLUDED.temp_min,
            temp_mean = EXCLUDED.temp_mean,
            precipitation = EXCLUDED.precipitation,
            humidity = EXCLUDED.humidity,
            wind_speed = EXCLUDED.wind_speed
    """)

    with engine.begin() as conn:
        conn.execute(upsert_query, records)


def process_location(location: dict, engine) -> dict:
    """Run the full fetch + upsert flow for one location.

    Returns a result dict so main() can build a final summary
    instead of letting one failure stop the whole run.
    """
    try:
        logger.info(f"Fetching data for {location['name']}...")
        df = fetch_weather_data(location)

        logger.info(f"Loading {len(df)} records for {location['name']}...")
        upsert_weather_data(df, engine)

        logger.info(f"Success: {location['name']} ({len(df)} records)")
        return {"location": location["name"], "status": "success", "records": len(df)}

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for {location['name']}: {e}")
        return {"location": location["name"], "status": "failed", "error": f"API error: {e}"}

    except KeyError as e:
        logger.error(f"Unexpected API response for {location['name']}: {e}")
        return {"location": location["name"], "status": "failed", "error": f"Data error: {e}"}

    except SQLAlchemyError as e:
        logger.error(f"Database error for {location['name']}: {e}")
        return {"location": location["name"], "status": "failed", "error": f"DB error: {e}"}

    except Exception as e:
        # Catch-all so one unexpected error never kills the whole run
        logger.error(f"Unexpected error for {location['name']}: {e}")
        return {"location": location["name"], "status": "failed", "error": f"Unexpected: {e}"}


def main():
    engine = get_engine()
    results = []

    for location in LOCATIONS:
        result = process_location(location, engine)
        results.append(result)

    # Final summary
    successes = [r for r in results if r["status"] == "success"]
    failures = [r for r in results if r["status"] == "failed"]

    logger.info("=" * 50)
    logger.info(f"Run complete: {len(successes)} succeeded, {len(failures)} failed")

    if failures:
        logger.warning("Failed locations:")
        for f in failures:
            logger.warning(f"  - {f['location']}: {f['error']}")

    if failures:
        exit(1)  # non-zero exit code, useful for GitHub Actions later


if __name__ == "__main__":
    main()