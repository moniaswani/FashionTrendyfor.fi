import React, { useState, useEffect } from 'react';
import { Shirt, Loader2, AlertCircle, Palette, Package } from 'lucide-react';
import { PieChart } from './PieChart';

interface FashionItem {
  item_name: string;
  color_name: string;
  materials: string;
  color_hex: string;
  brand: string;
  collection: string;
  season: string;
  original_image_name: string;
  record_id: string;
  timestamp: string;
}

interface GroupedData {
  [key: string]: FashionItem[];
}

interface DistributionData {
  [key: string]: number;
}

interface Dataset {
  id: string;
  name: string;
  description: string;
  designer: string;
  season: string;
  collection: string;
  s3Bucket: string;
  apiEndpoint: string;
}

interface FashionDashboardProps {
  dataset: Dataset;
}

export function FashionDashboard({ dataset }: FashionDashboardProps) {
  const [data, setData] = useState<GroupedData>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rawData, setRawData] = useState<FashionItem[]>([]);
  const [showAllColors, setShowAllColors] = useState(false);
  const [showAllItems, setShowAllItems] = useState(false);
  const [showAllMaterials, setShowAllMaterials] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(dataset.apiEndpoint);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Filter data by designer and season to only show items from the selected dataset
        const filteredData = result.filter((item: FashionItem) => {
          const itemDesigner = (item.designer || item.brand || '').trim();
          const itemSeason = (item.season || '').trim();
          const datasetDesigner = dataset.designer.trim();
          const datasetSeason = dataset.season.trim();
          
          // Exact match for both designer and season
          return itemDesigner === datasetDesigner && itemSeason === datasetSeason;
        });
        
        setRawData(filteredData);
        
        // Group data by original_image_name
        const grouped = filteredData.reduce((acc: GroupedData, item: FashionItem) => {
          const imageName = item.original_image_name;
          if (!acc[imageName]) {
            acc[imageName] = [];
          }
          acc[imageName].push(item);
          return acc;
        }, {});
        
        setData(grouped);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [dataset]);

  // Helper function to determine correct S3 folder path for individual items
  const getS3FolderPathForItem = (item: FashionItem): string => {
    const brand = item.brand.toLowerCase();
    const imageName = item.original_image_name.toLowerCase();
    
    if (brand === 'louis vuitton') {
      if (imageName.includes('fall-winter')) {
        return 'louis-vuitton-ready-to-wear-fall-winter-2025-paris';
      } else {
        return 'louis-vuitton-ready-to-wear-spring-summer-2025-paris';
      }
    } else if (brand === 'miu miu') {
      if (imageName.includes('fall-winter')) {
        return 'miu-miu-ready-to-wear-fall-winter-2025-paris';
      } else {
        return 'miu-miu-ready-to-wear-spring-summer-2025-paris';
      }
    } else if (brand === 'chanel') {
      if (imageName.includes('fall-winter')) {
        return 'chanel-ready-to-wear-fall-winter-2025-paris';
      } else {
        return 'chanel-ready-to-wear-spring-summer-2025-paris';
      }
    }
    
    // Default fallback
    return 'fashion-intelligence-input';
  };

  // Calculate real distributions from API data
  const calculateColorDistribution = (): DistributionData => {
    const colorCounts: DistributionData = {};
    rawData.forEach(item => {
      const colorKey = item.color_name.charAt(0).toUpperCase() + item.color_name.slice(1);
      colorCounts[colorKey] = (colorCounts[colorKey] || 0) + 1;
    });
    return colorCounts;
  };

  const calculateItemDistribution = (): DistributionData => {
    const itemCounts: DistributionData = {};
    rawData.forEach(item => {
      const itemName = item.item_name.charAt(0).toUpperCase() + item.item_name.slice(1);
      itemCounts[itemName] = (itemCounts[itemName] || 0) + 1;
    });
    return itemCounts;
  };

  const calculateMaterialDistribution = (): DistributionData => {
    const materialCounts: DistributionData = {};
    rawData.forEach(item => {
      const material = item.materials.charAt(0).toUpperCase() + item.materials.slice(1);
      materialCounts[material] = (materialCounts[material] || 0) + 1;
    });
    return materialCounts;
  };

  const formatDistributionData = (distribution: DistributionData, type: 'color' | 'item' | 'material') => {
    const entries = Object.entries(distribution)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10);
    
    if (type === 'color') {
      // For colors, we need to find the hex value from rawData
      return entries.map(([name, value]) => {
        const colorItem = rawData.find(item => 
          item.color_name.charAt(0).toUpperCase() + item.color_name.slice(1) === name
        );
        return {
          name,
          value,
          color: colorItem?.color_hex || '#808080'
        };
      });
    }
    
    return entries.map(([name, value]) => ({
        name,
        value
      }));
  };

  const getUniqueItems = (items: FashionItem[], key: keyof FashionItem) => {
    const uniqueValues = [...new Set(items.map(item => item[key]))];
    return uniqueValues.map(value => 
      value.charAt(0).toUpperCase() + value.slice(1)
    );
  };

  const getUniqueColors = (items: FashionItem[]) => {
    const uniqueColors = new Map<string, string>();
    items.forEach(item => {
      const colorName = item.color_name.charAt(0).toUpperCase() + item.color_name.slice(1);
      if (!uniqueColors.has(colorName)) {
        uniqueColors.set(colorName, item.color_hex);
      }
    });
    return Array.from(uniqueColors.entries()).map(([name, hex]) => ({ name, hex }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-green-600" />
          <p className="text-gray-600">Loading fashion analysis...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 mx-auto mb-4 text-red-500" />
          <p className="text-red-600 mb-2">Error loading data:</p>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Distribution Section */}
      <div>
        <h3 className="text-2xl font-semibold text-gray-800 mb-6 text-center">Fashion analysis overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-green-50 border border-green-200 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-center mb-4">
              <Palette className="w-5 h-5 text-green-600 mr-2" />
              <h4 className="text-lg font-semibold text-gray-800">Color distribution</h4>
            </div>
            <div className="flex justify-center">
              <PieChart 
                data={formatDistributionData(calculateColorDistribution(), 'color')} 
                type="color"
                size={240}
                showAll={showAllColors}
                onToggleShowAll={() => setShowAllColors(!showAllColors)}
              />
            </div>
          </div>
          
          <div className="bg-green-50 border border-green-200 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-center mb-4">
              <Shirt className="w-5 h-5 text-green-600 mr-2" />
              <h4 className="text-lg font-semibold text-gray-800">Clothing items</h4>
            </div>
            <div className="flex justify-center">
              <PieChart 
                data={formatDistributionData(calculateItemDistribution(), 'item')} 
                type="item"
                size={240}
                showAll={showAllItems}
                onToggleShowAll={() => setShowAllItems(!showAllItems)}
              />
            </div>
          </div>
          
          <div className="bg-green-50 border border-green-200 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-center mb-4">
              <Package className="w-5 h-5 text-green-600 mr-2" />
              <h4 className="text-lg font-semibold text-gray-800">Materials</h4>
            </div>
            <div className="flex justify-center">
              <PieChart 
                data={formatDistributionData(calculateMaterialDistribution(), 'material')} 
                type="material"
                size={240}
                showAll={showAllMaterials}
                onToggleShowAll={() => setShowAllMaterials(!showAllMaterials)}
              />
            </div>
          </div>
        </div>
      </div>

      <h3 className="text-2xl font-semibold text-gray-800">Individual fashion analysis</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {Object.entries(data).map(([imageName, items]) => (
          <FashionCard
            key={items[0].record_id}
            imageName={items[0].original_image_name} // 👈 file from API
            collection={items[0].collection}         // 👈 folder from API
            items={items}
            getUniqueItems={getUniqueItems}
            getUniqueColors={getUniqueColors}
            getS3FolderPathForItem={getS3FolderPathForItem}
            s3Bucket="runwayimages"
          />
        ))}
      </div>
    </div>
  );
}

interface FashionCardProps {
  imageName: string;
  collection: string; // comes directly from API
  items: FashionItem[];
  getUniqueItems: (items: FashionItem[], key: keyof FashionItem) => string[];
  getUniqueColors: (items: FashionItem[]) => { name: string; hex: string }[];
  getS3FolderPathForItem: (item: FashionItem) => string;
  s3Bucket: string;
}

const folderMap: Record<string, Record<string, string>> = {
  'louis vuitton': {
    'fall-winter-2025': 'louis-vuitton-ready-to-wear-fall-winter-2025-paris',
    'spring-summer-2025': 'louis-vuitton-ready-to-wear-spring-winter-2025-paris', // maps to actual folder
  },
  'chanel': {
    'fall-winter-2025': 'chanel-ready-to-wear-fall-winter-2025-paris',
    'spring-summer-2025': 'chanel-ready-to-wear-spring-winter-2025-paris',
  },
  'miu miu': {
    'fall-winter-2025': 'miu-miu-ready-to-wear-fall-winter-2025-paris',
    'spring-summer-2025': 'miu-miu-ready-to-wear-spring-winter-2025-paris',
  },
};

function getFolder(brand: string, season: string) {
  const brandKey = brand.toLowerCase();
  const seasonKey = season.toLowerCase().replace(/\s+/g, '-'); // "spring-summer-2025"
  return folderMap[brandKey]?.[seasonKey] || 'fashion-intelligence-input';
}

function FashionCard({ imageName, items, getUniqueItems, getUniqueColors, s3Bucket }: FashionCardProps) {
  const [imageError, setImageError] = useState(false);

  const item = items[0];
  const folder = getFolder(item.brand, item.season);

  const imageUrl = `https://${s3Bucket}.s3.eu-west-2.amazonaws.com/${folder}/${imageName}`;
  console.log("Resolved image URL:", imageUrl);


  const uniqueClothing = getUniqueItems(items, 'item_name');
  const uniqueColors = getUniqueColors(items);
  const uniqueMaterials = getUniqueItems(items, 'materials');

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300">
      <div className="aspect-square bg-gray-100 relative overflow-hidden">
        {!imageError ? (
          <img
            src={imageUrl}
            alt={`Fashion analysis for ${imageName}`}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={() => {
              console.error("❌ Failed to load:", imageUrl);
              setImageError(true);
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <div className="text-center">
              <Shirt className="w-12 h-12 mx-auto mb-2" />
              <p className="text-sm">Image not available</p>
            </div>
          </div>
        )}
      </div>
      
      <div className="p-4">
        {/* Clothing Items */}
        <div className="mb-4">
          <h5 className="font-medium text-gray-700 mb-2">Clothing items</h5>
          <div className="flex flex-wrap gap-1">
            {uniqueClothing.map((item, index) => (
              <span
                key={index}
                className="bg-gray-100 text-gray-700 px-2 py-1 rounded-full text-xs"
              >
                {item}
              </span>
            ))}
          </div>
        </div>

        {/* Colors */}
        <div className="mb-4">
          <h5 className="font-medium text-gray-700 mb-2">Colors</h5>
          <div className="flex flex-wrap gap-2">
            {uniqueColors.map((color, index) => (
              <div key={index} className="flex items-center gap-2">
                <div
                  className="w-4 h-4 rounded-full border border-gray-300"
                  style={{ backgroundColor: color.hex }}
                  title={`${color.name} (${color.hex})`}
                />
                <span className="text-xs text-gray-600">{color.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Materials */}
        <div>
          <h5 className="font-medium text-gray-700 mb-2">Materials</h5>
          <div className="flex flex-wrap gap-1">
            {uniqueMaterials.map((material, index) => (
              <span
                key={index}
                className="bg-green-100 text-green-700 px-2 py-1 rounded-full text-xs"
              >
                {material}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
