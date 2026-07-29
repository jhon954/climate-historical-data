CREATE OR REPLACE VIEW vw_weather_anomaly AS
WITH historical_avg AS (
    SELECT
        location_id,
        EXTRACT(MONTH FROM date) AS month,
        EXTRACT(DAY FROM date) AS day,
        AVG(temp_mean) AS historical_avg_temp
    FROM daily_weather
    GROUP BY location_id, EXTRACT(MONTH FROM date), EXTRACT(DAY FROM date)
)
SELECT
    dw.location_id,
    l.name AS location_name,
    dw.date,
    dw.temp_mean,
    ROUND(ha.historical_avg_temp::numeric, 2) AS historical_avg_temp,
    ROUND((dw.temp_mean - ha.historical_avg_temp)::numeric, 2) AS temp_anomaly
FROM daily_weather dw
JOIN locations l ON l.id = dw.location_id
JOIN historical_avg ha
    ON ha.location_id = dw.location_id
    AND ha.month = EXTRACT(MONTH FROM dw.date)
    AND ha.day = EXTRACT(DAY FROM dw.date)
ORDER BY dw.location_id, dw.date;

CREATE OR REPLACE VIEW vw_weather_yoy_monthly AS
SELECT
    dw.location_id,
    l.name AS location_name,
    EXTRACT(YEAR FROM dw.date) AS year,
    EXTRACT(MONTH FROM dw.date) AS month,
    ROUND(AVG(dw.temp_mean)::numeric, 2) AS avg_temp,
    ROUND(AVG(dw.temp_max)::numeric, 2) AS avg_temp_max,
    ROUND(AVG(dw.temp_min)::numeric, 2) AS avg_temp_min,
    ROUND(SUM(dw.precipitation)::numeric, 2) AS total_precipitation
FROM daily_weather dw
JOIN locations l ON l.id = dw.location_id
GROUP BY dw.location_id, l.name, EXTRACT(YEAR FROM dw.date), EXTRACT(MONTH FROM dw.date)
ORDER BY dw.location_id, year, month;

CREATE OR REPLACE VIEW vw_weather_moving_avg AS
SELECT
    dw.location_id,
    l.name AS location_name,
    dw.date,
    dw.temp_mean,
    dw.precipitation,
    AVG(dw.temp_mean) OVER (
        PARTITION BY dw.location_id
        ORDER BY dw.date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS temp_mean_7d_avg,
    AVG(dw.temp_mean) OVER (
        PARTITION BY dw.location_id
        ORDER BY dw.date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS temp_mean_30d_avg,
    SUM(dw.precipitation) OVER (
        PARTITION BY dw.location_id
        ORDER BY dw.date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS precipitation_7d_sum
FROM daily_weather dw
JOIN locations l ON l.id = dw.location_id
ORDER BY dw.location_id, dw.date;