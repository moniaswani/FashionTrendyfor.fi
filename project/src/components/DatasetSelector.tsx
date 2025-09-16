import React from 'react';
import { ChevronDown } from 'lucide-react';

interface Dataset {
  id: string;
  name: string;
  description: string;
  s3Bucket: string;
  apiEndpoint: string;
}

interface DatasetSelectorProps {
  datasets: Dataset[];
  currentDataset: string;
  onDatasetChange: (datasetId: string) => void;
}

export function DatasetSelector({ datasets, currentDataset, onDatasetChange }: DatasetSelectorProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const currentDatasetInfo = datasets.find(d => d.id === currentDataset);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full max-w-md bg-white border border-gray-200 rounded-lg px-4 py-3 text-left shadow-sm hover:shadow-md transition-shadow"
      >
        <div>
          <div className="font-medium text-gray-900">{currentDatasetInfo?.name}</div>
          <div className="text-sm text-gray-500">{currentDatasetInfo?.description}</div>
        </div>
        <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
          {datasets.map((dataset) => (
            <button
              key={dataset.id}
              onClick={() => {
                onDatasetChange(dataset.id);
                setIsOpen(false);
              }}
              className={`w-full text-left px-4 py-3 hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg ${
                dataset.id === currentDataset ? 'bg-green-50 border-l-4 border-green-500' : ''
              }`}
            >
              <div className="font-medium text-gray-900">{dataset.name}</div>
              <div className="text-sm text-gray-500">{dataset.description}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}