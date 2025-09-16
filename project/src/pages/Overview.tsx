import React, { useState, useEffect } from 'react';
import { BarChart3, Database, TrendingUp, Users } from 'lucide-react';
import { PieChart } from '../components/PieChart';

interface FashionItem {
  original_image_name: string;
  item_name: string;
  color_name: string;
  materials: string;
  color_hex: string;
}

export function Overview() {
  const [allData, setAllData] = useState<FashionItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAllData = async () => {
      try {
        setLoading(true);
        // Fetch data from main API endpoint
        const apiEndpoint = 'https://tr6nsuekii.execute-api.eu-west-2.amazonaws.com/default/fetchFashionAnalysis';
        
        const response = await fetch(apiEndpoint);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        setAllData(result);
      } catch (err) {
        console.error('Error fetching data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, []);

  // Calculate distributions from all datasets
  const calculateColorDistribution = () => {
    const colorCounts: { [key: string]: number } = {};
    allData.forEach(item => {
      const colorName = item.color_name.charAt(0).toUpperCase() + item.color_name.slice(1);
      colorCounts[colorName] = (colorCounts[colorName] || 0) + 1;
    });
    return Object.entries(colorCounts)
      .sort(([,a], [,b]) => b - a)
      .map(([name, value]) => ({ name, value }));
  };

  const calculateItemDistribution = () => {
    const itemCounts: { [key: string]: number } = {};
    allData.forEach(item => {
      const itemName = item.item_name.charAt(0).toUpperCase() + item.item_name.slice(1);
      itemCounts[itemName] = (itemCounts[itemName] || 0) + 1;
    });
    return Object.entries(itemCounts)
      .sort(([,a], [,b]) => b - a)
      .map(([name, value]) => ({ name, value }));
  };

  const calculateMaterialDistribution = () => {
    const materialCounts: { [key: string]: number } = {};
    allData.forEach(item => {
      const material = item.materials.charAt(0).toUpperCase() + item.materials.slice(1);
      materialCounts[material] = (materialCounts[material] || 0) + 1;
    });
    return Object.entries(materialCounts)
      .sort(([,a], [,b]) => b - a)
      .map(([name, value]) => ({ name, value }));
  };

  const stats = [
    {
      name: 'Total datasets',
      value: '1',
      icon: Database,
      color: 'bg-blue-500',
    },
    {
      name: 'Fashion items analyzed',
      value: allData.length.toString(),
      icon: BarChart3,
      color: 'bg-green-500',
    },
    {
      name: 'Active models',
      value: '3',
      icon: TrendingUp,
      color: 'bg-purple-500',
    },
    {
      name: 'Collections tracked',
      value: '1',
      icon: Users,
      color: 'bg-orange-500',
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Dashboard overview</h2>
        <p className="text-gray-600">
          Welcome to the Fashion Intelligence Dashboard. Monitor your fashion analysis data and forecasting models across all collections.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center">
                <div className={`${stat.color} p-3 rounded-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Combined Distribution Charts */}
      {!loading && allData.length > 0 && (
        <div>
          <h3 className="text-2xl font-semibold text-gray-800 mb-6 text-center">Combined fashion analysis</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-center mb-4">
                <div className="w-5 h-5 bg-green-600 rounded mr-2" />
                <h4 className="text-lg font-semibold text-gray-800">Color distribution</h4>
              </div>
              <div className="flex justify-center">
                <PieChart 
                  data={calculateColorDistribution()} 
                  type="item"
                  size={240}
                />
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-center mb-4">
                <div className="w-5 h-5 bg-green-600 rounded mr-2" />
                <h4 className="text-lg font-semibold text-gray-800">Clothing items</h4>
              </div>
              <div className="flex justify-center">
                <PieChart 
                  data={calculateItemDistribution()} 
                  type="item"
                  size={240}
                />
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-center mb-4">
                <div className="w-5 h-5 bg-green-600 rounded mr-2" />
                <h4 className="text-lg font-semibold text-gray-800">Materials</h4>
              </div>
              <div className="flex justify-center">
                <PieChart 
                  data={calculateMaterialDistribution()} 
                  type="material"
                  size={240}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent activity</h3>
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Balenciaga RTW Fall 2024 dataset updated</p>
                <p className="text-xs text-gray-500">2 hours ago</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">New fashion analysis completed</p>
                <p className="text-xs text-gray-500">5 hours ago</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Forecasting model trained</p>
                <p className="text-xs text-gray-500">1 day ago</p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick actions</h3>
          <div className="space-y-3">
            <button className="w-full text-left p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">
              <div className="font-medium text-gray-900">Analyze new collection</div>
              <div className="text-sm text-gray-500">Upload and analyze fashion images</div>
            </button>
            <button className="w-full text-left p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">
              <div className="font-medium text-gray-900">View data insights</div>
              <div className="text-sm text-gray-500">Explore fashion analysis results</div>
            </button>
            <button className="w-full text-left p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">
              <div className="font-medium text-gray-900">Generate forecast</div>
              <div className="text-sm text-gray-500">Create trend predictions</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}