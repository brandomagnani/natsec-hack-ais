'use client';

import React, { useRef, useEffect } from 'react';
import RawMap from './components/RawMap';
import ShipDetail from './components/ShipDetail';
import StartScreen from './components/StartScreen';
import RecentActivities from './components/RecentActivities';
import ActivityPopup from './components/ActivityPopup';
import { ShipLatestData } from './types';
import { useAppContext } from './context/AppContext'; // Import the hook

export default function Home() {
  // Use the context hook to get state and setters
  const { appState, setAppState } = useAppContext();
  const { selectedShip, isStarted } = appState;
  const analysisTimerRef = useRef<NodeJS.Timeout | null>(null); // <-- Ref for timer

  // Update state using the context setter
  const handleShipSelect = (shipData: ShipLatestData) => {
    console.log('Ship selected:', shipData.mmsi, '(Setting isAnalyzing = true)');

    // Clear any existing timer before setting a new one (Safety check, primary control moves to handleAutoplayStep)
    if (analysisTimerRef.current) {
      clearTimeout(analysisTimerRef.current);
      analysisTimerRef.current = null;
    }

    // Only set the selected ship and turn ON the analysis flag
    setAppState(prev => ({
      ...prev,
      selectedShip: shipData,
      isAnalyzing: true,
    }));

    // --- Timer to turn OFF isAnalyzing is now handled by handleAutoplayStep ---
    /*
    // Set timer to turn off analyzing flag
    analysisTimerRef.current = setTimeout(() => {
        console.log('Analysis timer ended for:', shipData.MMSI, '(Setting isAnalyzing = false)');
        setAppState(prev => ({
            ...prev,
            isAnalyzing: false, // <-- Reset analyzing flag
        }));
        analysisTimerRef.current = null;
    }, 4800); // Match the duration in ShipDetail (or slightly less than 5s)
    */
  };

  // --- Handler for when RawMap reports the duration of the next step ---
  const handleAutoplayStep = (durationMs: number) => {
    // Clear any previous analysis timer
    if (analysisTimerRef.current) {
      clearTimeout(analysisTimerRef.current);
    }

    // Set a new timer to turn off the 'isAnalyzing' flag
    // Use duration - 200ms buffer to hide overlay slightly before map moves
    const overlayDuration = Math.max(100, durationMs - 200); // Ensure minimum duration
    console.log(`Setting analysis overlay timer for ${overlayDuration.toFixed(0)}ms (based on step duration ${durationMs.toFixed(0)}ms)`);

    analysisTimerRef.current = setTimeout(() => {
      console.log('Analysis overlay timer ended.');
      setAppState(prev => ({
        ...prev,
        isAnalyzing: false, // <-- Reset analyzing flag
      }));
      analysisTimerRef.current = null;
    }, overlayDuration);
  };

  const handleStart = () => {
    console.log('Starting main view...');
    setAppState(prev => ({ ...prev, isStarted: true }));
  };

  // Dummy handler for ShipDetail prop
  const handleAnalysisComplete = () => {
    // Currently does nothing, might be used later
    console.log('ShipDetail analysis complete reported.');
  };

  // You can customize the map options here
  const mapOptions = {
    // center: [-74.5, 40] as [number, number],
    // zoom: 9,
    // style: 'mapbox://styles/mapbox/satellite-v9' // Example of a different style
  };

  // --- Add Effect for Cleanup ---
  useEffect(() => {
    // Cleanup function to clear the timer if the component unmounts
    return () => {
      if (analysisTimerRef.current) {
        clearTimeout(analysisTimerRef.current);
        console.log('Cleared analysis timer on page unmount.');
      }
    };
  }, []); // Empty dependency array ensures this runs only on mount and unmount

  // Render StartScreen if not started, otherwise render the main map view
  if (!isStarted) {
    // Make sure StartScreen exists or remove/replace the import
    return <StartScreen onStart={handleStart} />;
  }

  return (
    <main className="flex min-h-screen flex-col items-center p-4">
      {/* Removed h1 title for brevity, adjust as needed */}
      {/* <h1 className="text-4xl font-bold my-4">Mapbox GL JS Map</h1> */}

      {/* Render the popup - it will only show when needed due to its internal logic */}
      <ActivityPopup />

      {/* Top Box - Ship Detail */}
      <div className="w-full border border-gray-300 rounded mb-4 flex items-stretch justify-center min-h-[110px]">
        {/* Pass selectedShip from context and the required handler */}
        <ShipDetail
          shipData={selectedShip}
          onAnalysisComplete={handleAnalysisComplete}
        />
      </div>

      <div className="flex w-full">
        {/* Map Container */}
        <div className="flex-grow h-[600px] border border-gray-300 rounded mr-4">
          {/* Pass handleShipSelect from context */}
          {/* Pass handleAutoplayStep handler */}
          <RawMap
            initialOptions={mapOptions}
            onShipSelect={handleShipSelect}
            onAutoplayStep={handleAutoplayStep} // <-- Pass the new handler
          />
        </div>

        {/* Right Box - Now uses RecentActivities */}
        <div className="w-64 h-[600px]">
          <RecentActivities />
        </div>
      </div>

      {/* <p className="mt-4">Map container using raw mapbox-gl library.</p> */}
    </main>
  );
}
