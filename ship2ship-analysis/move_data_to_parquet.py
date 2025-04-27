import datetime
import json
from dataclasses import dataclass

import polars as pl
from sqlalchemy import Engine, text
from tqdm import tqdm


@dataclass
class Port:
    uid: str
    name: str
    lat: float
    lon: float


@dataclass
class AISEntry:
    timestamp: datetime.datetime
    mmsi: str
    lat: float
    lon: float
    heading: str
    vessel_name: str


@dataclass
class LandingPoint:
    uid: str
    name: str | None
    is_tbd: bool
    lat: float
    lon: float


@dataclass
class CablePoint:
    uid: str
    name: str
    cable_id: str
    section_id: str
    index: int
    lat: float
    lon: float


def parse_cable_data() -> tuple[pl.DataFrame, pl.DataFrame]:
    res_cable_points = []
    res_landing_points = []

    with open("/Users/felixknispel/Developer/natsec/data/cable-geo.json") as f:
        cable_data = json.load(f)
    cable_data = cable_data["features"]
    for cable in cable_data:
        cable_id = cable["properties"]["id"]
        cable_name = cable["properties"]["name"]
        for section_idx, cable_section in enumerate(cable["geometry"]["coordinates"]):
            for point_idx, point in enumerate(cable_section):
                cable_point = dict(
                    uid=f"{cable_id}_{section_idx}_{point_idx}",
                    name=cable_name,
                    cable_id=cable_id,
                    section_id=section_idx,
                    index=point_idx,
                    lat=point[0],
                    lon=point[1],
                )
                res_cable_points.append(cable_point)

    with open("/Users/felixknispel/Developer/natsec/data/landing-point-geo.json") as f:
        port_data = json.load(f)
    for port in port_data["features"]:
        port_id = port["properties"]["id"]
        port_name = port["properties"]["name"]
        port_is_tbd = port["properties"]["is_tbd"]
        port_lat = port["geometry"]["coordinates"][0]
        port_lon = port["geometry"]["coordinates"][1]
        landing_point = dict(
            uid=port_id,
            name=port_name,
            is_tbd=port_is_tbd,
            lat=port_lat,
            lon=port_lon,
        )
        res_landing_points.append(landing_point)
    return pl.DataFrame(res_landing_points), pl.DataFrame(res_cable_points)


def parse_port_data() -> pl.DataFrame:
    df_ports = pl.read_csv(
        "/Users/felixknispel/Developer/natsec/data/UpdatedPub150.csv",
        infer_schema_length=10000,
    )
    ports = []
    for port in df_ports.iter_rows(named=True):
        lat = port["Latitude"]
        lon = port["Longitude"]
        uid = port["World Port Index Number"]
        name = port["Main Port Name"]
        region_name = port["Region Name"]
        country_code = port["Country Code"]
        world_water_body = port["World Water Body"]
        ports.append(
            dict(
                uid=uid,
                name=name,
                lat=lat,
                lon=lon,
                region_name=region_name,
                country_code=country_code,
                world_water_body=world_water_body,
            )
        )
    return pl.DataFrame(ports)


def parse_ais_data(file: str) -> tuple[pl.DataFrame, dict[str, dict[str, any]]]:
    df_ais = pl.read_csv(file)
    vessel_entries: dict[str, dict[str, any]] = {}
    ais_updates = []
    i = 0
    for ais in tqdm(df_ais.iter_rows(named=True)):
        timestamp = datetime.datetime.fromisoformat(ais["BaseDateTime"])
        ais_updates.append(
            dict(
                timestamp=timestamp,
                mmsi=ais["MMSI"],
                lat=ais["LAT"],
                lon=ais["LON"],
                heading=ais["Heading"],
                sog=ais["SOG"],
                cog=ais["COG"],
                status=ais["Status"],
                draft=ais["Draft"],
                cargo=ais["Cargo"],
            )
        )
        if ais["MMSI"] not in vessel_entries:
            vessel_entries[ais["MMSI"]] = {
                "mmsi": ais["MMSI"],
                "name": ais["VesselName"],
                "imo": ais["IMO"],
                "call_sign": ais["CallSign"],
                "vessel_type": ais["VesselType"],
                "length": ais["Length"],
                "width": ais["Width"],
                "transceiver_class": ais["TransceiverClass"],
            }

        i += 1
        # if i > 10000:
        #     break
    return pl.DataFrame(ais_updates), vessel_entries


if __name__ == "__main__":
    import polars as pl

    df_landing_points, df_cable_points = parse_cable_data()
    df_ports = parse_port_data()

    # push the data to the database
    df_landing_points.write_parquet("./data/parquet/landing_points.parquet")
    df_cable_points.write_parquet("./data/parquet/cable_points.parquet")
    df_ports.write_parquet("./data/parquet/ports.parquet")

    all_vessel_entries = {}
    ais_files = [
        "/Users/felixknispel/Developer/natsec/data/AIS_2024_01_01.csv",
        "/Users/felixknispel/Developer/natsec/data/AIS_2024_01_02.csv",
        "/Users/felixknispel/Developer/natsec/data/AIS_2024_01_03.csv",
        "/Users/felixknispel/Developer/natsec/data/AIS_2024_01_04.csv",
        "/Users/felixknispel/Developer/natsec/data/AIS_2024_01_05.csv",
    ]
    for file in tqdm(ais_files, total=len(ais_files)):
        df_ais, vessel_entries = parse_ais_data(file)
        # store ais data as parquet
        fn = f"./data/parquet/{file.split('/')[-1]}"
        fn = fn.replace(".csv", ".parquet")
        df_ais.write_parquet(fn)
        all_vessel_entries.update(vessel_entries)

    df_vessel_entries = pl.DataFrame(list(all_vessel_entries.values()))
    df_vessel_entries.write_parquet("./data/parquet/vessel_entries.parquet")
