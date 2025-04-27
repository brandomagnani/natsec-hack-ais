export interface ShipLatestData {
  mmsi: string;
  basedatetime: string;
  lat: number;
  lon: number;
  sog: number;
  cog: number;
  heading: number | null;
  vesselname: string;
  imo: string | null;
  callsign: string;
  vesseltype: number;
  status: number | null;
  length: number | null;
  width: number | null;
  draft: number | null;
  cargo: number | null;
  transceiverclass: string;
  activity?: string; // New field for malicious activity detection
}

export type ActivityStatus = "normal" | "suspicious" | "surveying";

export interface ActivityLogEntry {
  timestamp: number; // Use Unix timestamp for easy sorting
  shipName: string;
  mmsi: string;
  status: ActivityStatus;
}
