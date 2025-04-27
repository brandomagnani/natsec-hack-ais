'use client';

import React from 'react';
import { useAppContext } from '../context/AppContext';
import { ActivityLogEntry, ActivityStatus } from '../types';

const statusColors: Record<ActivityStatus, string> = {
  normal: 'text-green-600',
  suspicious: 'text-red-600',
  surveying: 'text-yellow-600',
};

const statusLabels: Record<ActivityStatus, string> = {
  normal: 'Normal',
  suspicious: 'Suspicious',
  surveying: 'Surveying',
};

const RecentActivities: React.FC = () => {
  const { appState } = useAppContext();
  const { activityLog } = appState;

  const formatTimestamp = (timestamp: number): string => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className="w-full h-full p-2 bg-gray-50 border border-gray-200 rounded flex flex-col">
      <h3 className="text-md font-semibold text-gray-700 mb-2 border-b pb-1">Recent Activity</h3>
      {activityLog.length === 0 ? (
        <p className="text-sm text-gray-500 text-center mt-4">No activity recorded yet.</p>
      ) : (
        <ul className="space-y-1 overflow-y-auto flex-grow">
          {activityLog.map((entry, index) => (
            <li key={index} className="text-xs p-1 border-b border-gray-100 last:border-b-0">
              <div className="flex justify-between items-center">
                <span className="font-medium truncate pr-1" title={entry.shipName || entry.mmsi}>
                  {entry.shipName || entry.mmsi}
                </span>
                <span className={`font-bold ${statusColors[entry.status]}`}>
                  {statusLabels[entry.status]}
                </span>
              </div>
              <div className="text-gray-500 text-right">
                {formatTimestamp(entry.timestamp)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default RecentActivities;
