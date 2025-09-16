import React, { useState, useEffect } from 'react';
import { DatasetSelector } from '../components/DatasetSelector';
import { FashionDashboard } from '../components/FashionDashboard';

// Auto-detect datasets from API data
const API_ENDPOINT = 'https://tr6nsuekii.execute-api.eu-west-2.amazonaws.com/default/fetchFashionAnalysis';

export function Data() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [currentDataset, setCurrentDataset] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAndDetectDatasets = async () => {
      try {
        setLoading(true);
        const response = await fetch(API_ENDPOINT);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Auto-detect datasets based on designer and season from DynamoDB
        const datasetMap = new Map();
        
        data.forEach((item: any) => {
          const designer = (item.designer || 'Unknown Designer').trim();
          const season = (item.season || 'Unknown Season').trim();
          const collection = item.collection || 'Ready To Wear';
          const datasetId = `${designer.toLowerCase().replace(/\s+/g, '-')}-${season.toLowerCase().replace(/\s+/g, '-')}`;
          
          if (!datasetMap.has(datasetId)) {
            datasetMap.set(datasetId, {
              id: datasetId,
              name: `${designer} - ${season}`,
              description: `${collection} collection from ${season}`,
              designer: designer,
              season: season,
              collection: collection,
              s3Bucket: 'runwayimages',
              apiEndpoint: API_ENDPOINT
            });
          }
        });
        
        const detectedDatasets = Array.from(datasetMap.values());
        
        // Sort datasets by designer, then by season
        detectedDatasets.sort((a, b) => {
          if (a.designer !== b.designer) {
            return a.designer.localeCompare(b.designer);
          }
          return a.season.localeCompare(b.season);
        });
        
        setDatasets(detectedDatasets);
        
        // Set first dataset as default
        if (detectedDatasets.length > 0) {
          setCurrentDataset(detectedDatasets[0].id);
        }
      } catch (err) {
        console.error('Error detecting datasets:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAndDetectDatasets();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="w-8 h-8 animate-spin mx-auto mb-4 border-4 border-green-600 border-t-transparent rounded-full" />
          <p className="text-gray-600">Loading datasets...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Fashion data analysis</h2>
        <p className="text-gray-600 mb-6">
          Explore detailed analysis of fashion collections and runway shows.
        </p>
        
        {datasets.length > 0 && (
          <DatasetSelector
            datasets={datasets}
            currentDataset={currentDataset}
            onDatasetChange={setCurrentDataset}
          />
        )}
      </div>

      {currentDataset && datasets.length > 0 && (
        <FashionDashboard dataset={datasets.find(d => d.id === currentDataset)} />
      )}
    </div>
  );
}