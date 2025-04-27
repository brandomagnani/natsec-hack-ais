'use client';

import React, { useRef, useEffect, useState, useMemo } from 'react';
import mapboxgl, { Map, Marker, Popup } from 'mapbox-gl'; // Import Marker and Popup
import { ShipLatestData, ActivityLogEntry, ActivityStatus } from '../types'; // Import Activity types
import { useAppContext } from '../context/AppContext'; // Import context hook
// Ensure Mapbox CSS is loaded globally in layout.tsx

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
const SHIPS_API_URL = 'http://localhost:8000/api/v1/ships';
const CABLES_API_URL = 'http://localhost:8000/cables'; // <-- Add cables endpoint

/* REMOVE THIS LOCAL DEFINITION
interface ShipLatestData {
  MMSI: string;
  BaseDateTime: string;
  LAT: number;
  LON: number;
  SOG: number;
  COG: number;
  Heading: number;
  VesselName: string;
  IMO: string | null;
  CallSign: string;
  VesselType: number;
  Status: number | null;
  Length: number | null;
  Width: number | null;
  Draft: number | null;
  Cargo: number | null;
  TransceiverClass: string;
}
*/

// --- Updated: Define the structure of the API response ---
type ShipApiResponse = ShipLatestData[];

// Define the structure for ship position history
interface ShipPositionHistory {
  timestamp: string;
  lon: number;
  lat: number;
  sog?: number;
  cog?: number;
}

// Define the structure for the detailed ship API response
interface ShipDetailResponse {
  ship_metadata: Record<string, any>; // Define more specific type if needed
  movement: ShipPositionHistory[];
}

// --- Define type for Cable data ---
type CableCoordinates = [number, number][][]; // <-- Update type to array of arrays

interface RawMapProps {
  initialOptions?: Omit<mapboxgl.MapOptions, 'container'>;
  onShipSelect?: (shipData: ShipLatestData) => void; // Add prop for selection callback
  onAutoplayStep?: (durationMs: number) => void; // <-- Add prop to report autoplay step duration
}

export default function RawMap({ initialOptions, onShipSelect, onAutoplayStep }: RawMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const markersRef = useRef<Marker[]>([]);
  const currentHistoryLineIdRef = useRef<{ sourceId: string; layerId: string } | null>(null); // Ref to store current line source/layer ID
  const cableLineIdRef = useRef<{ sourceId: string; layerId: string }[]>([]); // <-- Ref for multiple cable lines
  // --- State for Autoplay ---
  const [allShipsData, setAllShipsData] = useState<ShipApiResponse | null>(null);
  const [currentAutoplayIndex, setCurrentAutoplayIndex] = useState<number>(0);
  const autoplayTimerIdRef = useRef<NodeJS.Timeout | null>(null); // Use ref to store timer ID

  // --- Get addActivityLog from context ---
  const { addActivityLog, pauseAutoplay, appState } = useAppContext();
  const { isAutoplayPaused } = appState; // <-- Destructure for easier access
  const wasPausedPreviouslyRef = useRef(isAutoplayPaused); // <-- Ref to track previous pause state

  // --- Updated Function Signature to accept ship data ---
  const handleMarkerClick = async (shipId: string, coordinates: [number, number], shipData: ShipLatestData) => {
    if (!mapRef.current) return;
    const map = mapRef.current;

    // --- Call the selection callback ---
    if (onShipSelect) {
      onShipSelect(shipData);
    }

    // --- Add to Activity Log ---
    let activityStatus: ActivityStatus = 'normal'; // Default
    if (shipData.activity === 'malicious') {
      activityStatus = 'suspicious';
    } else if (shipData.activity === 'surveying') { // Assuming 'surveying' is a possible value
      activityStatus = 'surveying';
    }

    const logEntry: ActivityLogEntry = {
      timestamp: Date.now(),
      shipName: shipData.vesselname || 'N/A',
      mmsi: shipData.mmsi,
      status: activityStatus,
    };
    addActivityLog(logEntry);
    console.log('Added activity log entry:', logEntry);
    // --- End Activity Log Update ---

    // --- Pause Autoplay if activity is not normal ---
    if (shipData.activity && shipData.activity !== 'normal') {
      console.log(`Activity [${shipData.activity}] detected for ${shipData.mmsi}. Pausing autoplay.`);
      pauseAutoplay(shipData);
    }

    // --- Center map on the clicked ship ---
    console.log('Centering map on ship:', coordinates);
    map.flyTo({
      center: coordinates,
      zoom: Math.max(map.getZoom(), 13), // Zoom in if needed, but don't zoom out too far
      speed: 2 // Adjust speed as desired
    });

    const detailUrl = `http://localhost:8000/api/v1/ship-detail/${shipId}`;
    console.log(`Fetching history for ship ${shipId} from ${detailUrl}`);

    // --- Clear previous line if exists ---
    if (currentHistoryLineIdRef.current) {
      const { sourceId, layerId } = currentHistoryLineIdRef.current;
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
        console.log(`Removed layer: ${layerId}`);
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
        console.log(`Removed source: ${sourceId}`);
      }
      currentHistoryLineIdRef.current = null;
    }

    try {
      console.log(`Making request to: ${detailUrl}`);
      const response = await fetch(detailUrl);
      console.log(`Response status: ${response.status}`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // --- Updated parsing ---
      const responseData: ShipDetailResponse = await response.json();
      console.log('Ship detail response:', responseData);

      const historyData = responseData.movement; // Extract the movement array
      console.log(`Fetched ${historyData?.length || 0} history points for ship ${shipId}.`);

      if (!historyData || historyData.length < 2) {
        console.warn(`Not enough data points to draw a line for ship ${shipId}`);
        return; // Need at least two points for a line
      }

      // Ensure we have both long and lat values for each history point
      const validCoordinates = historyData
        .filter(p => typeof p.lat === 'number' && typeof p.lon === 'number') // Corrected: Use p.lon
        .map(p => [p.lon, p.lat]); // Corrected: Use p.lon

      console.log(`${validCoordinates.length} valid coordinates found for history line`);

      if (validCoordinates.length < 2) {
        console.warn(`Not enough valid data points to draw a line for ship ${shipId}`);
        return;
      }

      // --- Add new line source and layer ---
      const sourceId = `history-line-source-${shipId}`;
      const layerId = `history-line-layer-${shipId}`;

      // Add the source if it doesn't exist
      if (!map.getSource(sourceId)) {
        map.addSource(sourceId, {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: {},
            geometry: {
              type: 'LineString',
              coordinates: validCoordinates,
            },
          },
        });
        console.log(`Added source: ${sourceId}`);
      }

      // Add the layer if it doesn't exist
      if (!map.getLayer(layerId)) {
        map.addLayer({
          id: layerId,
          type: 'line',
          source: sourceId,
          layout: {
            'line-join': 'round',
            'line-cap': 'round',
          },
          paint: {
            'line-color': '#facc15', // Tailwind yellow-400
            'line-width': 0.5,
            'line-opacity': 0.8
          },
        });
        console.log(`Added layer: ${layerId}`);
      }

      // Store the ID of the newly added line
      currentHistoryLineIdRef.current = { sourceId, layerId };

    } catch (error) {
      console.error(`Failed to fetch or draw ship history for ${shipId}:`, error);
      // Optionally, display an error to the user
    } finally {
      // --- Logic to trigger next step in autoplay resides in the useEffect ---
    }
  };

  // Effect for initializing the map
  useEffect(() => {
    if (!MAPBOX_TOKEN) {
      console.error("Mapbox token is not configured.");
      return;
    }
    if (mapRef.current || !mapContainerRef.current) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;

    console.log('Re-initializing map with options:', initialOptions);
    mapRef.current = new mapboxgl.Map({
      container: mapContainerRef.current!,
      ...initialOptions,
      style: initialOptions?.style || 'mapbox://styles/mapbox/dark-v11',
      center: [119.93, 24.81],
      zoom: 6,
    });

    console.log('Map instance created:', mapRef.current); // Debug log

    mapRef.current.on('load', () => {
      setIsMapLoaded(true);
      console.log('Map loaded and ready for markers');
    });

    return () => {
      // --- Enhanced Cleanup ---
      // Remove history line
      if (mapRef.current && currentHistoryLineIdRef.current) {
        const { sourceId, layerId } = currentHistoryLineIdRef.current;
        // Check if map still exists before removing
        if (mapRef.current.getLayer(layerId)) {
          mapRef.current.removeLayer(layerId);
        }
        if (mapRef.current.getSource(sourceId)) {
          mapRef.current.removeSource(sourceId);
        }
        currentHistoryLineIdRef.current = null;
        console.log('Cleaned up history line.');
      }
      // --- Cleanup existing cable lines ---
      if (mapRef.current && cableLineIdRef.current.length > 0) {
        cableLineIdRef.current.forEach(({ sourceId, layerId }) => {
          if (mapRef.current?.getLayer(layerId)) {
            mapRef.current.removeLayer(layerId);
          }
          if (mapRef.current?.getSource(sourceId)) {
            mapRef.current.removeSource(sourceId);
          }
        });
        cableLineIdRef.current = [];
        console.log('Cleaned up cable lines.');
      }
      // Clean up markers
      markersRef.current.forEach(marker => marker.remove());
      markersRef.current = [];
      // Then clean up map
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        setIsMapLoaded(false);
        console.log('Map removed');
      }
      // --- Clear autoplay timer on unmount ---
      if (autoplayTimerIdRef.current) {
        clearTimeout(autoplayTimerIdRef.current);
        autoplayTimerIdRef.current = null;
        console.log('Cleared autoplay timer on unmount.');
      }
    };
  }, []);

  // --- Effect for fetching Cable data and drawing it ---
  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      console.log('Map not ready, skipping cable line drawing');
      return;
    }
    const map = mapRef.current;

    const fetchAndDrawCables = async () => {
      // --- Clear previous cable lines if they exist ---
      if (cableLineIdRef.current.length > 0) {
        cableLineIdRef.current.forEach(({ sourceId, layerId }) => {
          // Check if map and methods exist before calling
          if (map?.getLayer(layerId)) {
            map.removeLayer(layerId);
          }
          if (map?.getSource(sourceId)) {
            map.removeSource(sourceId);
          }
        });
        cableLineIdRef.current = []; // Clear the ref array
      }

      try {
        console.log(`Fetching cables from ${CABLES_API_URL}`);
        const response = await fetch(CABLES_API_URL);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const cableSegments: CableCoordinates = await response.json(); // Now an array of segments
        console.log(`Fetched ${cableSegments.length} cable segments.`);

        const addedIds: { sourceId: string; layerId: string }[] = [];

        cableSegments.forEach((segment, index) => {
          if (!segment || segment.length < 2) {
            console.warn(`Segment ${index}: Not enough data points to draw cable line.`);
            return; // Skip this segment
          }

          const sourceId = `cable-line-source-${index}`;
          const layerId = `cable-line-layer-${index}`;

          // Add the source for this segment
          if (!map.getSource(sourceId)) {
            map.addSource(sourceId, {
              type: 'geojson',
              data: {
                type: 'Feature',
                properties: {},
                geometry: {
                  type: 'LineString',
                  coordinates: segment, // Use the segment coordinates
                },
              },
            });
            console.log(`Added cable source: ${sourceId}`);
          }

          // Add the layer for this segment
          if (!map.getLayer(layerId)) {
            map.addLayer({
              id: layerId,
              type: 'line',
              source: sourceId,
              layout: {
                'line-join': 'round',
                'line-cap': 'round',
              },
              paint: {
                'line-color': '#ef4444', // Tailwind red-500
                'line-width': 1.5,
                'line-opacity': 0.9,
              },
            });
            console.log(`Added cable layer: ${layerId}`);
          }
          addedIds.push({ sourceId, layerId });
        });

        // Store the IDs of all added cable lines
        cableLineIdRef.current = addedIds;

      } catch (error) {
        console.error('Failed to fetch or draw cable lines:', error);
      }
    };

    fetchAndDrawCables();

  }, [isMapLoaded]); // Re-run only when the map is loaded

  // Effect for fetching ship data and adding/updating markers
  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      console.log('Map not ready yet (isMapLoaded=false), skipping marker creation');
      return;
    }

    const map = mapRef.current; // Capture map instance
    console.log('Marker useEffect running because isMapLoaded is true.');

    const fetchShipsAndAddMarkers = async () => {
      console.log('[fetchShipsAndAddMarkers] Starting fetch...'); // Specific log
      try {
        const response = await fetch(SHIPS_API_URL);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const shipsData: ShipApiResponse = await response.json();
        console.log(`[fetchShipsAndAddMarkers] Fetched data for ${shipsData.length} ships.`);

        // Log the structure of the first ship data object
        if (shipsData.length > 0) {
          console.log('[fetchShipsAndAddMarkers] First ship data structure:', JSON.stringify(shipsData[0], null, 2));
          console.log('[fetchShipsAndAddMarkers] Data types:', {
            mmsi: typeof shipsData[0].mmsi,
            lat: typeof shipsData[0].lat,
            lon: typeof shipsData[0].lon,
            activity: typeof shipsData[0].activity
          });
        }

        // --- Store fetched data for autoplay ---
        setAllShipsData(shipsData);
        // --- Reset autoplay index when new data is fetched ---
        setCurrentAutoplayIndex(0);
        // --- Clear any existing autoplay timer ---
        if (autoplayTimerIdRef.current) {
          clearTimeout(autoplayTimerIdRef.current);
          autoplayTimerIdRef.current = null;
        }

        // --- Clear existing markers ---
        markersRef.current.forEach(marker => marker.remove());
        markersRef.current = [];
        // --- Clear existing history line ---
        if (currentHistoryLineIdRef.current) {
          const { sourceId, layerId } = currentHistoryLineIdRef.current;
          if (map.getLayer(layerId)) map.removeLayer(layerId);
          if (map.getSource(sourceId)) map.removeSource(sourceId);
          currentHistoryLineIdRef.current = null;
          console.log('[fetchShipsAndAddMarkers] Cleared history line on data refresh.');
        }

        console.log('[fetchShipsAndAddMarkers] Processing ships for markers...');
        // Process data for each ship
        shipsData.forEach((shipData) => {
          // --- Updated: Get ship ID from mmsi field ---
          const shipId = shipData.mmsi;

          // console.log(`Processing ship ${shipId}:`, shipData); // Keep this commented for now to reduce noise

          if (!shipData || typeof shipData.lat !== 'number' || typeof shipData.lon !== 'number') {
            console.warn(`[fetchShipsAndAddMarkers] Invalid or missing coordinates for ship ID: ${shipId}`);
            return;
          }

          const coords: [number, number] = [shipData.lon, shipData.lat]; // Use lon, lat
          // console.log(`Ship ${shipId} coords:`, coords); // Keep commented

          // Determine marker color based on activity status
          // const markerColor = shipData.activity === 'malicious' ? '#ef4444' : '#3b82f6'; // red for malicious, blue for others
          const markerColor = '#3b82f6'; // Always blue for now

          /* Temporarily disable custom marker element
          // Create custom element for marker
          const el = document.createElement('div');
          el.style.width = '16px';
          el.style.height = '16px';
          el.style.borderRadius = '50%';
          el.style.backgroundColor = markerColor;
          el.style.border = '2px solid white';
          el.style.boxShadow = '0 0 4px rgba(0, 0, 0, 0.5)';
          */

          console.log(`[fetchShipsAndAddMarkers] Attempting to add marker for ship ${shipId} at coords:`, coords);

          // Use default marker for debugging
          const marker = new mapboxgl.Marker({ color: markerColor })
            .setLngLat(coords)
            .setPopup(new mapboxgl.Popup({ offset: 25 })
              // --- Updated: Popup content using new lowercase fields ---
              .setHTML(`
                <strong>Name:</strong> ${shipData.vesselname || 'N/A'}<br>
                <strong>MMSI:</strong> ${shipData.mmsi}<br>
                <strong>Type:</strong> ${shipData.vesseltype || 'N/A'}<br>
                <strong>Status:</strong> ${shipData.status ?? 'N/A'}<br>
                <strong>Activity:</strong> ${shipData.activity || 'normal'}<br>
                <strong>Coords:</strong> ${shipData.lat.toFixed(5)}, ${shipData.lon.toFixed(5)}
              `))
            .addTo(map);

          // console.log(`Marker added to map for ship ${shipId}`); // Keep commented

          // --- Add Click Listener to Marker ---
          const markerElement = marker.getElement();
          markerElement.addEventListener('click', (e) => {
            const clickedLngLat = marker.getLngLat();
            const currentCoords: [number, number] = [clickedLngLat.lng, clickedLngLat.lat];
            handleMarkerClick(shipId, currentCoords, shipData);
          });
          markerElement.style.cursor = 'pointer';

          markersRef.current.push(marker);
        });

        console.log(`[fetchShipsAndAddMarkers] Finished processing. Added/Updated ${markersRef.current.length} markers.`);

      } catch (error) {
        console.error("[fetchShipsAndAddMarkers] Error fetching/processing:", error);
      }
    };

    // Directly call fetchShipsAndAddMarkers when isMapLoaded is true
    fetchShipsAndAddMarkers();

    // Optional: Set up an interval to fetch data periodically
    // const intervalId = setInterval(fetchShipsAndAddMarkers, 30000); // Fetch every 30 seconds
    // return () => clearInterval(intervalId); // Clear interval on unmount

  }, [isMapLoaded]); // Re-run if isMapLoaded changes

  // --- Effect for Autoplay Logic ---
  useEffect(() => {
    // Clear any previous timer when dependencies change
    if (autoplayTimerIdRef.current) {
      clearTimeout(autoplayTimerIdRef.current);
      autoplayTimerIdRef.current = null;
    }

    // --- Check if we JUST resumed from a paused state ---
    const justResumed = !isAutoplayPaused && wasPausedPreviouslyRef.current;
    wasPausedPreviouslyRef.current = isAutoplayPaused; // Update ref for next render

    if (justResumed) {
      console.log('Autoplay just resumed, scheduling next ship immediately.');
      const randomDelay = Math.random() * 4000 + 2000; // Use same delay logic
      autoplayTimerIdRef.current = setTimeout(() => {
        setCurrentAutoplayIndex((prevIndex) => {
          // Ensure allShipsData exists before calculating length
          const nextIndex = allShipsData ? (prevIndex + 1) % allShipsData.length : 0;
          console.log(`Resumed: Advancing index from ${prevIndex} to ${nextIndex}`);
          return nextIndex;
        });
        autoplayTimerIdRef.current = null;
      }, randomDelay);
      return; // Skip the rest of the effect for this render
    }

    // --- Check if autoplay is paused (standard check) ---
    if (isAutoplayPaused) {
      console.log('Autoplay is paused.');
      return; // Don't proceed if paused
    }

    if (!isMapLoaded || !mapRef.current || !allShipsData) {
      console.log('Autoplay waiting: Map not loaded or no ship data.');
      return; // Don't run if map isn't ready or no data
    }

    if (allShipsData.length === 0) {
      console.log('Autoplay: No ships to display.');
      return; // No ships to cycle through
    }

    // Ensure index is valid (might be needed if data changes drastically)
    const validIndex = currentAutoplayIndex % allShipsData.length;
    const currentShipData = allShipsData[validIndex];
    const currentShipId = currentShipData.mmsi;

    if (!currentShipData || typeof currentShipData.lon !== 'number' || typeof currentShipData.lat !== 'number') {
      console.warn(`Autoplay: Invalid data for ship ID ${currentShipId} at index ${validIndex}. Skipping.`);
      // Schedule the next ship immediately if current one is invalid
      autoplayTimerIdRef.current = setTimeout(() => {
        setCurrentAutoplayIndex((prevIndex) => (prevIndex + 1) % allShipsData.length);
      }, 100); // Short delay before trying next
      return;
    }

    const coords: [number, number] = [currentShipData.lon, currentShipData.lat];

    console.log(`Autoplay: Focusing on ship ${currentShipId} (${currentShipData.vesselname || 'N/A'}) at index ${validIndex}`);

    // Trigger the selection and history display
    // No need to await here, let it run asynchronously
    handleMarkerClick(currentShipId, coords, currentShipData);

    // Calculate random delay (2000ms to 6000ms)
    const randomDelay = Math.random() * 4000 + 2000;
    console.log(`Autoplay: Next step in ${randomDelay.toFixed(0)}ms`);

    // --- Inform parent about the duration for this step ---
    if (onAutoplayStep) {
      onAutoplayStep(randomDelay);
    }

    // Schedule the next ship focus using the random delay
    autoplayTimerIdRef.current = setTimeout(() => {
      setCurrentAutoplayIndex((prevIndex) => {
        // Ensure allShipsData exists before calculating length
        const nextIndex = allShipsData ? (prevIndex + 1) % allShipsData.length : 0;
        console.log(`Normal: Advancing index from ${prevIndex} to ${nextIndex}`);
        return nextIndex;
      });
      autoplayTimerIdRef.current = null; // Clear ref after timeout executes
    }, randomDelay); // Use randomized delay

    // Cleanup function for this effect instance
    return () => {
      if (autoplayTimerIdRef.current) {
        clearTimeout(autoplayTimerIdRef.current);
        autoplayTimerIdRef.current = null;
        console.log('Cleared autoplay timer due to effect re-run or unmount.');
      }
    };
  }, [isMapLoaded, allShipsData, currentAutoplayIndex, isAutoplayPaused]); // Dependencies: run when map loads, data arrives, index changes, OR pause state changes

  return (
    <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} data-testid="map-container">
      {!MAPBOX_TOKEN && <div>Error: Mapbox token missing.</div>}
    </div>
  );
}
