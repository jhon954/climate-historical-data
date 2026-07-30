# Historical Climate Data Pipeline

An end-to-end data engineering project that extracts, stores, and analyzes historical weather data for five Colombian cities, culminating in a comparative Power BI dashboard.

## Overview

This project builds a complete ETL pipeline from scratch: pulling historical weather data from a public API, storing it in a cloud PostgreSQL database, automating daily updates, and visualizing trends and anomalies through an interactive dashboard.

**Cities tracked:** Bogotá, Duitama, Medellín, Cali, Villavicencio

## Architecture

Open-Meteo API → Python (ETL) → Supabase (PostgreSQL) → Power BI
↑
GitHub Actions (daily automation)

## Tech Stack

| Layer | Tool |
|---|---|
| Data source | [Open-Meteo Archive API](https://open-meteo.com) |
| ETL language | Python (requests, pandas, SQLAlchemy) |
| Cloud database | Supabase (PostgreSQL) |
| Automation | GitHub Actions (scheduled workflow) |
| Analysis layer | SQL views (window functions, CTEs) |
| Reporting | Power BI |

## Features

- **Historical data extraction**: bulk-loads multiple years of daily weather data per location
- **Incremental updates**: a lightweight script fetches only the most recent days, run automatically every day
- **Idempotent loading**: uses `UPSERT` logic (`ON CONFLICT`) so re-running any script never creates duplicates
- **Error handling & logging**: each location is processed independently — a failure on one doesn't stop the rest, and all runs are logged with timestamps
- **SQL-based analytics layer**: moving averages, year-over-year comparisons, and temperature anomaly detection computed directly in PostgreSQL via views
- **Interactive dashboard**: comparative time series, geographic map, precipitation patterns, and anomaly tracking across all five cities

## Data Model

**`locations`** — city metadata (name, country, coordinates)

**`daily_weather`** — daily weather records per location (temperature, precipitation, humidity, wind speed), with a unique constraint on `(location_id, date)` to support upserts

**Views:**
- `vw_weather_moving_avg` — 7-day and 30-day moving averages
- `vw_weather_yoy_monthly` — monthly aggregates for year-over-year comparison
- `vw_weather_anomaly` — daily temperature deviation vs. historical average for that calendar day

## Project Structure

climate-historical-data/
├── .github/
│ └── workflows/
│ └── daily_weather_update.yml # GitHub Actions automation
├── sql/
│ └── views.sql # Analytics layer (views)
├── src/
│ ├── config.py # Locations, date ranges, env vars
│ ├── db.py # Database connection
│ ├── weather_etl.py # Shared fetch/upsert logic
│ ├── extract_historical.py # Bulk historical load
│ └── extract_incremental.py # Daily incremental update
├── requirements.txt
└── .gitignore

## How It Works

1. **Historical load** (`extract_historical.py`): fetches several years of daily data per city from the Open-Meteo Archive API and loads it into Supabase
2. **Daily automation** (`extract_incremental.py` + GitHub Actions): every day, a scheduled workflow fetches the last 3 days of data (to account for any API reporting delay) and upserts it into the database
3. **Analytics layer**: SQL views compute moving averages, monthly comparisons, and anomalies directly in PostgreSQL, so Power BI consumes pre-calculated metrics instead of recalculating them in DAX
4. **Dashboard**: Power BI connects directly to Supabase and visualizes the data across multiple pages (overview, comparisons, anomalies)

## Dashboard Preview

*(Screenshots coming soon)*

## Key Technical Decisions

- **Supabase over Azure/GCP**: chosen for its permanent free tier with no credit card required, while still providing full PostgreSQL compatibility
- **Session Pooler over Transaction Pooler for BI tools**: Power BI performs significantly better over Supabase's Session Pooler, since it maintains a persistent connection and supports prepared statements — unlike Transaction mode, which is optimized for short-lived serverless connections
- **SQL views over DAX calculations**: moving averages and anomaly detection are computed at the database layer, keeping business logic centralized and making the Power BI model lighter
- **Idempotent upserts**: every load operation is safe to re-run without creating duplicate records, thanks to a unique constraint on `(location_id, date)`

## Setup

1. Clone the repository
2. Create a virtual environment and install dependencies:
```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\Activate.ps1
   pip install -r requirements.txt
```
3. Create a `.env` file with your database connection string
4. Run the SQL scripts in `sql/` against your PostgreSQL instance to create the schema and views
5. Run the historical load:
```bash
   cd src
   python extract_historical.py
```
6. (Optional) Set up the GitHub Actions workflow with your own `DATABASE_URL` secret for daily automation

## Future Improvements

- Add more cities / expand to other countries for broader comparison
- Incorporate weather forecast data alongside historical records
- Add data quality checks / alerting when the daily workflow fails
- Explore Azure Functions or Cloud Functions as an alternative automation trigger
