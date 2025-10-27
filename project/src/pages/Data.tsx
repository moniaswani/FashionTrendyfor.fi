import React, { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { FashionDashboard } from '../components/FashionDashboard';

// Auto-detect datasets from API data
const API_ENDPOINT = 'https://tr6nsuekii.execute-api.eu-west-2.amazonaws.com/default/fetchFashionAnalysis';

export function Data() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [currentDataset, setCurrentDataset] = useState('');
  const [allData, setAllData] = useState<any[]>([]);
  const [filteredData, setFilteredData] = useState<any[]>([]);
  const [filters, setFilters] = useState({
    brand: '',
    season: '',
    color: '',
    item: '',
    material: ''
  });
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
        setAllData(data);
        
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

  // Apply filters to data
  useEffect(() => {
    let filtered = allData;
    
    // Helper function to normalize season names for comparison
    const normalizeSeason = (season: string) => {
      if (!season) return '';
      return season.toLowerCase()
        .replace(/[-_]/g, ' ')  // Replace hyphens and underscores with spaces
        .replace(/\s+/g, ' ')   // Replace multiple spaces with single space
        .trim();
    };
    
    if (filters.brand) {
      filtered = filtered.filter(item => 
        (item.designer || item.brand || '').toLowerCase().includes(filters.brand.toLowerCase())
      );
    }
    
    if (filters.season) {
      filtered = filtered.filter(item => 
        normalizeSeason(item.season || '').includes(normalizeSeason(filters.season))
      );
    }
    
    if (filters.color) {
      filtered = filtered.filter(item => 
        (item.color_name || '').toLowerCase().includes(filters.color.toLowerCase())
      );
    }
    
    if (filters.item) {
      filtered = filtered.filter(item => 
        (item.item_name || '').toLowerCase().includes(filters.item.toLowerCase())
      );
    }
    
    if (filters.material) {
      filtered = filtered.filter(item => 
        (item.materials || '').toLowerCase().includes(filters.material.toLowerCase())
      );
    }
    
    setFilteredData(filtered);
  }, [allData, filters]);

  // Get unique values for filter dropdowns
  const getUniqueValues = (key: string) => {
    const values = new Set<string>();
  
    // Instead of using allData, use filteredData to get *remaining possible options*
    const sourceData = filteredData.length > 0 ? filteredData : allData;
  
    const formatSeasonForDisplay = (season: string) => {
      if (!season) return '';
      const normalized = season.toLowerCase()
        .replace(/[-_]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
      return normalized
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join('-');
    };
  
    sourceData.forEach(item => {
      let value = '';
      switch (key) {
        case 'brand':
          value = item.designer || item.brand || '';
          break;
        case 'season':
          value = formatSeasonForDisplay(item.season || '');
          break;
        case 'color':
          value = item.color_name || '';
          break;
        case 'item':
          value = item.item_name || '';
          break;
        case 'material':
          value = item.materials || '';
          break;
      }
      if (value.trim()) {
        if (key === 'season') {
          values.add(value);
        } else {
          values.add(value.charAt(0).toUpperCase() + value.slice(1));
        }
      }
    });
  
    return Array.from(values).sort();
  };
  
  const handleFilterChange = (filterType: string, value: string) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
  };

  const clearFilters = () => {
    setFilters({
      brand: '',
      season: '',
      color: '',
      item: '',
      material: ''
    });
  };

  const activeFiltersCount = Object.values(filters).filter(Boolean).length;

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

        {/* Filter Section */}
        {allData.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
              {activeFiltersCount > 0 && (
                <button
                  onClick={clearFilters}
                  className="text-sm text-red-600 hover:text-red-800 font-medium"
                >
                  Clear all filters ({activeFiltersCount})
                </button>
              )}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* Brand Filter */}
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">Brand</label>
                <div className="relative">
                  <select
                    value={filters.brand}
                    onChange={(e) => handleFilterChange('brand', e.target.value)}
                    className="w-full appearance-none bg-white border border-gray-300 rounded-md px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    <option value="">All Brands</option>
                    {getUniqueValues('brand').map(brand => (
                      <option key={brand} value={brand}>{brand}</option>
                    ))}
                  </select>
                  <ChevronDown className="w-4 h-4 absolute right-2 top-3 text-gray-400 pointer-events-none" />
                </div>
              </div>

              {/* Season Filter */}
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">Season</label>
                <div className="relative">
                  <select
                    value={filters.season}
                    onChange={(e) => handleFilterChange('season', e.target.value)}
                    className="w-full appearance-none bg-white border border-gray-300 rounded-md px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    <option value="">All Seasons</option>
                    {getUniqueValues('season').map(season => (
                      <option key={season} value={season}>{season}</option>
                    ))}
                  </select>
                  <ChevronDown className="w-4 h-4 absolute right-2 top-3 text-gray-400 pointer-events-none" />
                </div>
              </div>

              {/* Color Filter */}
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">Color</label>
                <div className="relative">
                  <select
                    value={filters.color}
                    onChange={(e) => handleFilterChange('color', e.target.value)}
                    className="w-full appearance-none bg-white border border-gray-300 rounded-md px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    <option value="">All Colors</option>
                    {getUniqueValues('color').map(color => (
                      <option key={color} value={color}>{color}</option>
                    ))}
                  </select>
                  <ChevronDown className="w-4 h-4 absolute right-2 top-3 text-gray-400 pointer-events-none" />
                </div>
              </div>

              {/* Clothing Item Filter */}
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">Clothing Item</label>
                <div className="relative">
                  <select
                    value={filters.item}
                    onChange={(e) => handleFilterChange('item', e.target.value)}
                    className="w-full appearance-none bg-white border border-gray-300 rounded-md px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    <option value="">All Items</option>
                    {getUniqueValues('item').map(item => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                  <ChevronDown className="w-4 h-4 absolute right-2 top-3 text-gray-400 pointer-events-none" />
                </div>
              </div>

              {/* Material Filter */}
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">Material</label>
                <div className="relative">
                  <select
                    value={filters.material}
                    onChange={(e) => handleFilterChange('material', e.target.value)}
                    className="w-full appearance-none bg-white border border-gray-300 rounded-md px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    <option value="">All Materials</option>
                    {getUniqueValues('material').map(material => (
                      <option key={material} value={material}>{material}</option>
                    ))}
                  </select>
                  <ChevronDown className="w-4 h-4 absolute right-2 top-3 text-gray-400 pointer-events-none" />
                </div>
              </div>
            </div>

            {/* Results Summary */}
            {activeFiltersCount > 0 && (
              <div className="mt-4 p-3 bg-green-50 rounded-md">
                <p className="text-sm text-green-800">
                  Showing {filteredData.length} items matching your filters
                  {filteredData.length !== allData.length && ` (out of ${allData.length} total)`}
                </p>
              </div>
            )}
          </div>
        )}
        

      </div>

      {currentDataset && datasets.length > 0 && (
        <FashionDashboard 
          dataset={datasets.find(d => d.id === currentDataset)} 
          filteredData={activeFiltersCount > 0 ? filteredData : undefined}
        />
      )}
    </div>
  );
}