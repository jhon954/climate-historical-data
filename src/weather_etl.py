import logging
import requests
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "relative_humidity_2m_mean",
    "wind_speed_10m_max",
]

logger = logging.getLogger(__name__)


def fetch_weather_data(location: dict, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch daily weather data for one location within a date range.

    Raises:
        requests.exceptions.RequestException: if the API call fails.
        KeyError: if the expected 'daily' field is missing from the response.
    """
    params = {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "start_date": start_date,
        "end_date": end_date,
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


def process_location(location: dict, start_date: str, end_date: str, engine) -> dict:
    """Run the full fetch + upsert flow for one location.

    Returns a result dict so the caller can build a final summary
    instead of letting one failure stop the whole run.
    """
    try:
        logger.info(f"Fetching data for {location['name']}...")
        df = fetch_weather_data(location, start_date, end_date)

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
        logger.error(f"Unexpected error for {location['name']}: {e}")
        return {"location": location["name"], "status": "failed", "error": f"Unexpected: {e}"}