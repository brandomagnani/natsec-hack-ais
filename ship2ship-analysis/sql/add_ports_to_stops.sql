DROP MATERIALIZED VIEW IF EXISTS vessel_stops_with_ports;

CREATE MATERIALIZED VIEW vessel_stops_with_ports as WITH joined AS (
  SELECT 
    vs.mmsi,
    vs.lat_bucket,
    vs.lon_bucket,
    vs.start_time,
    vs.end_time,
    vs.duration,
    p.name AS port_name,
    p.country_code AS port_country_code,
    p.lat AS port_lat,
    p.lon AS port_lon,
    p.uid AS port_uid,
    -- Construct a POINT geometry from bucketed lat/lon
    ST_SetSRID(
      ST_MakePoint(
        vs.lon_bucket / 1110.0,
        vs.lat_bucket / 1110.0
      ),
      4326
    ) AS geom
  FROM 
    vessel_stops vs
  LEFT JOIN 
    ports p
  ON 
    ABS(FLOOR(p.lat * 1110)::INTEGER - vs.lat_bucket) <= 5
    AND ABS(FLOOR(p.lon * 1110)::INTEGER - vs.lon_bucket) <= 5
) SELECT
  *
FROM
  joined
WHERE
  port_country_code IS NULL OR port_country_code != 'United States'
ORDER BY
  start_time;