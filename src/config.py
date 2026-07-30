import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

LOCATIONS = [
    {"id": 1, "name": "Bogota", "lat": 4.7110, "lon": -74.0721},
    {"id": 2, "name": "Duitama", "lat": 5.8236, "lon": -73.0322},
    {"id": 3, "name": "Medellín", "lat": 6.2442, "lon": -75.5812},
    {"id": 4, "name": "Cali", "lat": 3.4516, "lon": -76.5320},
    {"id": 5, "name": "Villavicencio", "lat": 4.1420, "lon": -73.6266},
]

START_DATE = "2020-01-01"
END_DATE = "2026-07-28"