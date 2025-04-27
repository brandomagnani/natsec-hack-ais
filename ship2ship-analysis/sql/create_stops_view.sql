-- Create the materialized view
CREATE MATERIALIZED VIEW vessel_stops as WITH preprocessed AS (
  SELECT 
    mmsi,
    timestamp,
    lat,
    lon,
    sog,
    -- Bucket lat/lon (~100m precision)
    FLOOR(lat * 1110)::INTEGER AS lat_bucket,
    FLOOR(lon * 1110)::INTEGER AS lon_bucket,
    -- Define if vessel is stopped
    CASE WHEN sog <= 0.2 THEN 1 ELSE 0 END AS is_stopped
  FROM 
    ais_updates
), grouped AS (
  SELECT 
    *,
    -- Row number gap trick to group consecutive points
    ROW_NUMBER() OVER (PARTITION BY mmsi ORDER BY timestamp) -
    ROW_NUMBER() OVER (PARTITION BY mmsi, lat_bucket, lon_bucket, is_stopped ORDER BY timestamp)
    AS stop_group
  FROM 
    preprocessed
), stops AS (
  SELECT 
    mmsi,
    lat_bucket,
    lon_bucket,
    MIN(timestamp) AS start_time,
    MAX(timestamp) AS end_time,
    MAX(timestamp) - MIN(timestamp) AS duration
  FROM 
    grouped
  WHERE 
    is_stopped = 1
  GROUP BY 
    mmsi, lat_bucket, lon_bucket, stop_group
  HAVING 
    MAX(timestamp) - MIN(timestamp) BETWEEN INTERVAL '2 hours' AND INTERVAL '8 hours'
) SELECT 
  mmsi,
  lat_bucket,
  lon_bucket,
  start_time,
  end_time,
  duration
FROM 
  stops
ORDER BY 
  start_time;