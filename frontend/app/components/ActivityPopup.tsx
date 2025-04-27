'use client';

import React from 'react';
import { useAppContext } from '../context/AppContext';

export default function ActivityPopup() {
  const { appState, resumeAutoplay } = useAppContext();
  const { isAutoplayPaused, popupShipData } = appState;

  if (!isAutoplayPaused || !popupShipData) {
    return null; // Don't render if not paused or no data
  }

  const handleResume = () => {
    console.log('Resuming autoplay...');
    resumeAutoplay();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg max-w-sm w-full mx-4">
        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">Unusual Activity Detected</h2>
        <div className="mb-4 space-y-2 text-gray-700 dark:text-gray-300">
          <p>
            <strong>Ship:</strong> {popupShipData.vesselname || 'N/A'} ({popupShipData.mmsi})
          </p>
          <p>
            <strong>Detected Activity:</strong>
            <span className="font-medium capitalize ml-1">{popupShipData.activity || 'Unknown'}</span>
          </p>
        </div>
        <button
          onClick={handleResume}
          className="w-full bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:ring-2 focus:ring-green-400 dark:focus:ring-green-600"
        >
          Verified
        </button>
        {/* Action Buttons */}
        <div className="mt-4 space-y-2">
          <button
            onClick={handleResume}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:ring-2 focus:ring-blue-400 dark:focus:ring-blue-600"
          >
            Send the message to the vessel
          </button>
          <button
            onClick={handleResume}
            className="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:ring-2 focus:ring-yellow-400 dark:focus:ring-yellow-600"
          >
            Broadcast AIS safety-message
          </button>
          <button
            onClick={handleResume}
            className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:ring-2 focus:ring-orange-400 dark:focus:ring-orange-600"
          >
            Broadcast navigation warning
          </button>
          <button
            onClick={handleResume}
            className="w-full bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:ring-2 focus:ring-red-400 dark:focus:ring-red-600"
          >
            Dispatch police
          </button>
        </div>
      </div>
    </div>
  );
}
