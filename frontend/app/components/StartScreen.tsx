'use client';

import React, { useState, useEffect } from 'react';

interface StartScreenProps {
  onStart: () => void;
}

// Placeholder data for regions and activity types
const regions = [
  'North Atlantic',
  'South Atlantic',
  'Mediterranean Sea',
  'Indian Ocean',
  'North Pacific',
  'South Pacific',
  'Arctic Ocean',
  'Southern Ocean',
];

const activityTypes = ['Surveying', 'Illegal Fishing', 'Sanction Evasion'];

const StartScreen: React.FC<StartScreenProps> = ({ onStart }) => {
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [isAllRegionsSelected, setIsAllRegionsSelected] = useState<boolean>(false);
  const [selectedActivities, setSelectedActivities] = useState<string[]>([]);
  const [isAllActivitiesSelected, setIsAllActivitiesSelected] = useState<boolean>(false);
  const [additionalText, setAdditionalText] = useState<string>('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  useEffect(() => {
    setIsAllRegionsSelected(selectedRegions.length === regions.length);
  }, [selectedRegions]);

  useEffect(() => {
    setIsAllActivitiesSelected(selectedActivities.length === activityTypes.length);
  }, [selectedActivities]);

  const handleRegionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const region = event.target.value;
    const isChecked = event.target.checked;

    setSelectedRegions((prev) =>
      isChecked ? [...prev, region] : prev.filter((r) => r !== region)
    );
  };

  const handleSelectAllRegionsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const isChecked = event.target.checked;
    setIsAllRegionsSelected(isChecked);
    setSelectedRegions(isChecked ? [...regions] : []);
  };

  const handleActivityChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const activity = event.target.value;
    const isChecked = event.target.checked;

    setSelectedActivities((prev) =>
      isChecked ? [...prev, activity] : prev.filter((a) => a !== activity)
    );
  };

  const handleSelectAllActivitiesChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const isChecked = event.target.checked;
    setIsAllActivitiesSelected(isChecked);
    setSelectedActivities(isChecked ? [...activityTypes] : []);
  };

  const handleTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setAdditionalText(event.target.value);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setUploadedFile(event.target.files[0]);
    } else {
      setUploadedFile(null);
    }
  };

  const handleReset = () => {
    setSelectedRegions([]);
    setIsAllRegionsSelected(false);
    setSelectedActivities([]);
    setIsAllActivitiesSelected(false);
    setAdditionalText('');
    setUploadedFile(null);
    // Reset file input visually if needed
    const fileInput = document.getElementById('file-upload') as HTMLInputElement | null;
    if (fileInput) fileInput.value = '';
  };

  const handleSubmit = () => {
    // Here you could potentially pass the collected data back via onStart
    // e.g., onStart({ regions: selectedRegions, activities: selectedActivities, text: additionalText, file: uploadedFile });
    console.log('Start button clicked. Options:', {
      regions: selectedRegions,
      activities: selectedActivities,
      text: additionalText,
      fileName: uploadedFile?.name,
    });
    onStart(); // Trigger the transition to the main view
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <div className="w-full max-w-2xl p-6 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-semibold mb-6 text-center text-gray-700">
          Welcome to Dark Fleet Monitoring
        </h1>

        {/* Region Selection with Select All */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Select Maritime Region(s):
            </label>
            <div className="flex items-center">
              <input
                id="select-all-regions"
                type="checkbox"
                checked={isAllRegionsSelected}
                onChange={handleSelectAllRegionsChange}
                className="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label
                htmlFor="select-all-regions"
                className="ml-2 block text-sm text-gray-900"
              >
                Select All
              </label>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {regions.map((region) => (
              <div key={region} className="flex items-center">
                <input
                  id={`region-${region}`}
                  name="region"
                  type="checkbox"
                  value={region}
                  checked={selectedRegions.includes(region)}
                  onChange={handleRegionChange}
                  className="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                />
                <label
                  htmlFor={`region-${region}`}
                  className="ml-2 block text-sm text-gray-900"
                >
                  {region}
                </label>
              </div>
            ))}
          </div>
        </div>

        {/* Activity Type Selection with Select All */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Select Activity Type(s):
            </label>
            <div className="flex items-center">
              <input
                id="select-all-activities"
                type="checkbox"
                checked={isAllActivitiesSelected}
                onChange={handleSelectAllActivitiesChange}
                className="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label
                htmlFor="select-all-activities"
                className="ml-2 block text-sm text-gray-900"
              >
                Select All
              </label>
            </div>
          </div>
          <div className="flex flex-col space-y-1">
            {activityTypes.map((activity) => (
              <div key={activity} className="flex items-center">
                <input
                  id={`activity-${activity}`}
                  name="activityType"
                  type="checkbox"
                  value={activity}
                  checked={selectedActivities.includes(activity)}
                  onChange={handleActivityChange}
                  className="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                />
                <label
                  htmlFor={`activity-${activity}`}
                  className="ml-2 block text-sm text-gray-900"
                >
                  {activity}
                </label>
              </div>
            ))}
          </div>
        </div>

        {/* Additional Text Input */}
        <div className="mb-4">
          <label
            htmlFor="additional-text"
            className="block text-sm font-medium text-gray-700"
          >
            Additional Notes:
          </label>
          <textarea
            id="additional-text"
            name="additional-text"
            rows={3}
            value={additionalText}
            onChange={handleTextChange}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900"
            placeholder="Enter any additional details or context..."
          ></textarea>
        </div>

        {/* File Upload */}
        <div className="mb-6">
          <label
            htmlFor="file-upload"
            className="block text-sm font-medium text-gray-700"
          >
            Upload Supporting Document (Optional):
          </label>
          <input
            id="file-upload"
            name="file-upload"
            type="file"
            onChange={handleFileChange}
            className="mt-1 block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-md file:border-0
              file:text-sm file:font-semibold
              file:bg-indigo-50 file:text-indigo-700
              hover:file:bg-indigo-100"
          />
          {uploadedFile && (
            <p className="mt-1 text-xs text-gray-500">
              Selected: {uploadedFile.name}
            </p>
          )}
        </div>

        {/* Buttons */}
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={handleReset}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Start Monitoring
          </button>
        </div>
      </div>
    </div>
  );
};

export default StartScreen;
