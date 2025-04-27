import React, { useState, useEffect, useRef } from 'react';
import { ShipLatestData, ActivityStatus } from '../types'; // Import ActivityStatus
import { useAppContext } from '../context/AppContext'; // <-- Import context hook

// Define types for analysis results
type ConfidenceLevel = 'High' | 'Medium' | 'Low';
type YesNo = 'Yes' | 'No';

// Update props to use the imported type
interface ShipDetailProps {
  shipData: ShipLatestData | null; // Allow null if no ship is selected
  onAnalysisComplete: () => void; // Callback when results are shown and delay passes
}

const ShipDetail: React.FC<ShipDetailProps> = ({ shipData, onAnalysisComplete }) => {
  // --- Get isAnalyzing from context ---
  const { appState } = useAppContext();
  const { isAnalyzing } = appState;

  // --- State for Analysis Results ---
  const [suspiciousActivity, setSuspiciousActivity] = useState<YesNo | null>(null);
  const [confidenceLevel, setConfidenceLevel] = useState<ConfidenceLevel | null>(null);
  const [humanInputNeeded, setHumanInputNeeded] = useState<YesNo | null>(null);
  const [showAnalysisResultOverlay, setShowAnalysisResultOverlay] = useState<boolean>(false); // State for showing results in overlay

  // --- Ref to track previous analysis state ---
  const wasAnalyzingRef = useRef(false);

  // --- Effect to generate results when analysis finishes and manage overlay ---
  useEffect(() => {
    let timerId: NodeJS.Timeout | null = null;

    // Check if analysis just finished (was true, now false) AND we have shipData
    if (wasAnalyzingRef.current && !isAnalyzing && shipData) { // Added check for shipData

      // --- Derive results from shipData.activity ---
      let derivedSuspicious: YesNo = 'No';
      let derivedConfidence: ConfidenceLevel = 'High';
      const activity = shipData.activity?.toLowerCase() as ActivityStatus | undefined;

      if (activity === 'suspicious') {
        derivedSuspicious = 'Yes';
        derivedConfidence = 'High';
      } else if (activity === 'surveying') {
        derivedSuspicious = 'Yes';
        derivedConfidence = 'Medium';
      } else { // normal or undefined/null
        derivedSuspicious = 'No';
        derivedConfidence = 'High'; // Default confidence for normal
      }
      // --- End Derivation ---

      // --- Keep Human Input random ---
      const randomHumanInput: YesNo = Math.random() < 0.2 ? 'Yes' : 'No';

      setSuspiciousActivity(derivedSuspicious);
      setConfidenceLevel(derivedConfidence);
      setHumanInputNeeded(randomHumanInput);
      setShowAnalysisResultOverlay(true); // Show results overlay

      // Set timer to hide results overlay and call completion callback
      timerId = setTimeout(() => {
        setShowAnalysisResultOverlay(false);
        onAnalysisComplete(); // Signal to move to the next ship
      }, 2000); // 2-second delay

    } else if (!wasAnalyzingRef.current && isAnalyzing) {
      // Reset results and hide result overlay when analysis starts
      setSuspiciousActivity(null);
      setConfidenceLevel(null);
      setHumanInputNeeded(null);
      setShowAnalysisResultOverlay(false);
    }

    // Update the ref to the current analysis state for the next render
    wasAnalyzingRef.current = isAnalyzing;

    // Cleanup timer on unmount or if isAnalyzing changes again before timer fires
    return () => {
      if (timerId) {
        clearTimeout(timerId);
      }
    };
  }, [isAnalyzing, onAnalysisComplete, shipData]); // Add shipData to dependencies

  if (!shipData) {
    return (
      <div className="w-full p-4 text-center text-gray-500">
        No ship selected.
      </div>
    );
  }

  // Helper to display N/A for null or undefined values
  const displayValue = (value: string | number | null | undefined, unit: string = '', label?: string) => {
    if (value === null || value === undefined) return 'N/A';
    // Special handling for Heading 511
    if (label === 'Heading' && value === 511) return 'N/A';
    return `${value}${unit}`;
  };

  // Helper to render each data item within a grid cell
  const renderDetailItem = (label: string, value: string | number | null | undefined, unit: string = '') => (
    <div className="py-1">
      <span className="text-xs text-gray-500 block">{label}</span>
      <span className="text-sm font-medium text-gray-800">
        {displayValue(value, unit, label) /* Pass label for context */}
      </span>
    </div>
  );

  // Overload for specific ReactNode values (like the formatted date)
  const renderDetailItemNode = (label: string, node: React.ReactNode) => (
    <div className="py-1">
      <span className="text-xs text-gray-500 block">{label}</span>
      <span className="text-sm font-medium text-gray-800">
        {node}
      </span>
    </div>
  );

  // Helper to render analysis result items (modified for overlay)
  const renderAnalysisResultItemOverlay = (label: string, value: string | null, colorClass?: string) => (
    <div className=""> {/* Removed text-center, parent handles alignment */}
      <span className="text-lg text-gray-200">{label}: </span> {/* Increased label size further */}
      <span className={`text-2xl font-semibold ${colorClass || 'text-white'}`}> {/* Increased value size to match Analyzing */}
        {value ?? 'N/A'}
      </span>
    </div>
  );

  return (
    <div className="relative w-full"> {/* Add relative positioning */}
      {/* The actual detail content */}
      <div className="w-full p-1 bg-gray-50 border border-gray-200 rounded">
        {/* Header Row - Removed mb-1 and pb-1 for less vertical space */}
        <div className="flex justify-between items-center border-b">
          <h2 className="text-md font-semibold text-gray-700 truncate pr-2 py-0.5">
            Vessel: {shipData.vesselname || 'N/A'}
          </h2>
          <div className="text-xs text-gray-500 text-right whitespace-nowrap py-0.5">
            Last Update:
            <span className="font-medium ml-1 text-gray-700">
              {new Date(shipData.basedatetime).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Data Grid - Kept minimal vertical gap */}
        <div className="grid grid-cols-8 gap-x-2 gap-y-0.5 pt-0.5">
          {/* Row 1 */}
          {renderDetailItem('MMSI', shipData.mmsi)}
          {renderDetailItem('IMO', shipData.imo)}
          {renderDetailItem('Call Sign', shipData.callsign)}
          {renderDetailItem('AIS Class', shipData.transceiverclass)}
          {renderDetailItem('Latitude', shipData.lat, '°')}
          {renderDetailItem('Longitude', shipData.lon, '°')}
          {renderDetailItem('SOG', shipData.sog, ' kts')}
          {renderDetailItem('COG', shipData.cog, '°')}

          {/* Row 2 */}
          {renderDetailItem('Heading', shipData.heading, '°')}
          {renderDetailItem('Nav Status', shipData.status) /* TODO: Map Status */}
          {renderDetailItem('Length', shipData.length, ' m')}
          {renderDetailItem('Width', shipData.width, ' m')}
          {renderDetailItem('Draft', shipData.draft, ' m')}
          {renderDetailItem('Vessel Type', shipData.vesseltype) /* TODO: Map Type */}
          {renderDetailItem('Cargo Type', shipData.cargo) /* TODO: Map Cargo */}
          {renderDetailItem('Activity', shipData.activity || 'normal')}
        </div>
      </div>

      {/* Analysis Overlay - Now shows "Analyzing..." or Results */}
      {(isAnalyzing || showAnalysisResultOverlay) && (
        <div className="absolute inset-0 bg-gray-900 bg-opacity-50 flex flex-col items-center justify-center rounded z-10 p-4">
          {isAnalyzing && (
            <span className="text-white text-2xl font-semibold animate-pulse">
              Analyzing...
            </span>
          )}
          {showAnalysisResultOverlay && suspiciousActivity !== null && (
            /* Use flexbox for horizontal layout */
            <div className="flex items-center justify-center space-x-6"> {/* Adjusted spacing */}
              {renderAnalysisResultItemOverlay(
                'Suspicious Activity',
                suspiciousActivity,
                suspiciousActivity === 'Yes' ? 'text-red-400' : 'text-green-400' // Adjusted colors for overlay
              )}
              {renderAnalysisResultItemOverlay('Confidence', confidenceLevel)}
              {renderAnalysisResultItemOverlay('Human Input', humanInputNeeded)}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ShipDetail;
