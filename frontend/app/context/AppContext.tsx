'use client';

import React, { createContext, useState, useContext, ReactNode, Dispatch, SetStateAction } from 'react';
import { ShipLatestData, ActivityLogEntry } from '@/app/types'; // Assuming types are in app/types

const MAX_LOG_ENTRIES = 50; // Limit the number of log entries

// 1. Define the state shape
interface AppState {
  selectedShip: ShipLatestData | null;
  isStarted: boolean;
  isAnalyzing: boolean;
  activityLog: ActivityLogEntry[]; // Add activity log state
  isAutoplayPaused: boolean;
  popupShipData: ShipLatestData | null;
}

// 2. Define the context type including state and setters
interface AppContextType {
  appState: AppState;
  setAppState: Dispatch<SetStateAction<AppState>>;
  addActivityLog: (entry: ActivityLogEntry) => void; // Add function to add logs
  pauseAutoplay: (shipData: ShipLatestData) => void; // Function to pause and set popup data
  resumeAutoplay: () => void; // Function to resume and clear popup data
}

// 3. Create the context with a default value
const AppContext = createContext<AppContextType | undefined>(undefined);

// 4. Create the Provider component
interface AppProviderProps {
  children: ReactNode;
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  const [appState, setAppState] = useState<AppState>({
    selectedShip: null,
    isStarted: false,
    isAnalyzing: false,
    activityLog: [], // Initialize empty log
    isAutoplayPaused: false,
    popupShipData: null,
  });

  // Function to add a new log entry
  const addActivityLog = (entry: ActivityLogEntry) => {
    setAppState(prevState => ({
      ...prevState,
      activityLog: [entry, ...prevState.activityLog].slice(0, MAX_LOG_ENTRIES), // Add to front and limit size
    }));
  };

  // Function to pause autoplay and show popup
  const pauseAutoplay = (shipData: ShipLatestData) => {
    setAppState(prevState => ({
      ...prevState,
      isAutoplayPaused: true,
      popupShipData: shipData,
    }));
  };

  // Function to resume autoplay and hide popup
  const resumeAutoplay = () => {
    setAppState(prevState => ({
      ...prevState,
      isAutoplayPaused: false,
      popupShipData: null,
    }));
  };

  const contextValue: AppContextType = {
    appState,
    setAppState,
    addActivityLog, // Provide the function
    pauseAutoplay,  // Provide the pause function
    resumeAutoplay, // Provide the resume function
  };

  return <AppContext.Provider value={contextValue}>{children}</AppContext.Provider>;
};

// 5. Create a custom hook for easy consumption
export const useAppContext = (): AppContextType => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
