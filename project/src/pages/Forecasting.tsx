import React, { useState } from 'react';
import { TrendingUp, Palette, Package, Layers, ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface TrendCard {
  type: 'color' | 'material' | 'item';
  name: string;
  confidence: number;
  change: 'up' | 'down' | 'stable';
  changePercent: number;
  color?: string;
  description: string;
}

interface ChartData {
  name: string;
  current: number;
  predicted: number;
  color: string;
}

export function Forecasting() {
  const [selectedCategory, setSelectedCategory] = useState<'colors' | 'materials' | 'items'>('colors');

  // Dummy trend predictions
  const trendingPredictions: TrendCard[] = [
    {
      type: 'color',
      name: 'Sage Green',
      confidence: 87,
      change: 'up',
      changePercent: 34,
      color: '#87A96B',
      description: 'Expected to dominate Spring 2025 collections'
    },
    {
      type: 'material',
      name: 'Recycled Polyester',
      confidence: 92,
      change: 'up',
      changePercent: 28,
      description: 'Sustainable fashion driving material choices'
    },
    {
      type: 'item',
      name: 'Oversized Blazers',
      confidence: 79,
      change: 'up',
      changePercent: 22,
      description: 'Power dressing trend continues to grow'
    },
    {
      type: 'color',
      name: 'Digital Lime',
      confidence: 84,
      change: 'up',
      changePercent: 41,
      color: '#32CD32',
      description: 'Tech-inspired bright colors gaining momentum'
    },
    {
      type: 'material',
      name: 'Organic Cotton',
      confidence: 88,
      change: 'up',
      changePercent: 19,
      description: 'Eco-conscious consumers driving demand'
    },
    {
      type: 'item',
      name: 'Wide-Leg Trousers',
      confidence: 76,
      change: 'up',
      changePercent: 15,
      description: 'Comfort-focused silhouettes trending'
    }
  ];

  // Chart data for different categories
  const chartData = {
    colors: [
      { name: 'Sage Green', current: 12, predicted: 28, color: '#87A96B' },
      { name: 'Digital Lime', current: 8, predicted: 22, color: '#32CD32' },
      { name: 'Warm Beige', current: 15, predicted: 25, color: '#D2B48C' },
      { name: 'Ocean Blue', current: 18, predicted: 20, color: '#006994' },
      { name: 'Sunset Orange', current: 10, predicted: 18, color: '#FF6B35' }
    ],
    materials: [
      { name: 'Recycled Polyester', current: 22, predicted: 35, color: '#10B981' },
      { name: 'Organic Cotton', current: 28, predicted: 38, color: '#059669' },
      { name: 'Tencel', current: 8, predicted: 15, color: '#047857' },
      { name: 'Hemp', current: 5, predicted: 12, color: '#065F46' },
      { name: 'Wool', current: 25, predicted: 22, color: '#064E3B' }
    ],
    items: [
      { name: 'Oversized Blazers', current: 15, predicted: 25, color: '#8B5CF6' },
      { name: 'Wide-Leg Trousers', current: 18, predicted: 28, color: '#7C3AED' },
      { name: 'Midi Skirts', current: 12, predicted: 16, color: '#6D28D9' },
      { name: 'Statement Coats', current: 8, predicted: 18, color: '#5B21B6' },
      { name: 'Crop Tops', current: 22, predicted: 20, color: '#4C1D95' }
    ]
  };

  const getChangeIcon = (change: 'up' | 'down' | 'stable') => {
    switch (change) {
      case 'up':
        return <ArrowUp className="w-4 h-4 text-green-500" />;
      case 'down':
        return <ArrowDown className="w-4 h-4 text-red-500" />;
      default:
        return <Minus className="w-4 h-4 text-gray-500" />;
    }
  };

  const getTypeIcon = (type: 'color' | 'material' | 'item') => {
    switch (type) {
      case 'color':
        return <Palette className="w-5 h-5" />;
      case 'material':
        return <Layers className="w-5 h-5" />;
      case 'item':
        return <Package className="w-5 h-5" />;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent mb-4">
          Fashion Forecasting
        </h2>
        <p className="text-gray-600 text-lg">
          AI-powered predictions for upcoming fashion trends
        </p>
      </div>

      {/* Trending Predictions Cards */}
      <div>
        <h3 className="text-2xl font-semibold text-gray-800 mb-6 flex items-center">
          <TrendingUp className="w-6 h-6 mr-2 text-purple-600" />
          Trending Next Season
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {trendingPredictions.map((trend, index) => (
            <div key={index} className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow border-t-4 border-purple-500">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className="p-2 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg text-white mr-3">
                    {getTypeIcon(trend.type)}
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 flex items-center">
                      {trend.color && (
                        <div 
                          className="w-4 h-4 rounded-full mr-2 border-2 border-gray-300 shadow-sm"
                          style={{ backgroundColor: trend.color }}
                        />
                      )}
                      {trend.name}
                    </h4>
                    <p className="text-sm text-gray-500 capitalize">{trend.type}</p>
                  </div>
                </div>
                <div className="flex items-center">
                  {getChangeIcon(trend.change)}
                  <span className={`ml-1 text-sm font-medium ${
                    trend.change === 'up' ? 'text-green-500' : 
                    trend.change === 'down' ? 'text-red-500' : 'text-gray-500'
                  }`}>
                    {trend.changePercent}%
                  </span>
                </div>
              </div>
              
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Confidence</span>
                  <span className="font-medium">{trend.confidence}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${trend.confidence}%` }}
                  />
                </div>
              </div>
              
              <p className="text-sm text-gray-600">{trend.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Trend Analysis Charts */}
      <div>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-2xl font-semibold text-gray-800">Trend Analysis</h3>
          <div className="flex space-x-2">
            {(['colors', 'materials', 'items'] as const).map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  selectedCategory === category
                    ? 'bg-purple-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {category.charAt(0).toUpperCase() + category.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="mb-6">
            <h4 className="text-lg font-semibold text-gray-800 mb-2">
              Current vs Predicted Popularity
            </h4>
            <p className="text-gray-600 text-sm">
              Comparison of current market share vs predicted next season
            </p>
          </div>

          <div className="space-y-4">
            {chartData[selectedCategory].map((item, index) => (
              <div key={index} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center">
                    <div 
                      className="w-4 h-4 rounded-full mr-3 shadow-sm"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="font-medium text-gray-900">{item.name}</span>
                  </div>
                  <div className="flex items-center space-x-4 text-sm">
                    <span className="text-gray-600">Current: {item.current}%</span>
                    <span className="text-purple-600 font-medium">Predicted: {item.predicted}%</span>
                  </div>
                </div>
                
                <div className="relative">
                  <div className="flex space-x-2">
                    {/* Current bar */}
                    <div className="flex-1">
                      <div className="text-xs text-gray-500 mb-1">Current</div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div 
                          className="bg-gray-400 h-3 rounded-full transition-all duration-500"
                          style={{ width: `${(item.current / 40) * 100}%` }}
                        />
                      </div>
                    </div>
                    
                    {/* Predicted bar */}
                    <div className="flex-1">
                      <div className="text-xs text-purple-600 mb-1">Predicted</div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div 
                          className="bg-gradient-to-r from-purple-500 to-blue-500 h-3 rounded-full transition-all duration-500"
                          style={{ width: `${(item.predicted / 40) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                  
                  {/* Change indicator */}
                  <div className="absolute right-0 top-0 flex items-center">
                    {item.predicted > item.current ? (
                      <div className="flex items-center text-green-500 text-xs">
                        <ArrowUp className="w-3 h-3 mr-1" />
                        +{item.predicted - item.current}%
                      </div>
                    ) : item.predicted < item.current ? (
                      <div className="flex items-center text-red-500 text-xs">
                        <ArrowDown className="w-3 h-3 mr-1" />
                        -{item.current - item.predicted}%
                      </div>
                    ) : (
                      <div className="flex items-center text-gray-500 text-xs">
                        <Minus className="w-3 h-3 mr-1" />
                        0%
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Insights Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-6 border border-green-200">
          <div className="flex items-center mb-3">
            <div className="p-2 bg-green-500 rounded-lg text-white mr-3">
              <ArrowUp className="w-5 h-5" />
            </div>
            <h4 className="font-semibold text-green-800">Rising Trends</h4>
          </div>
          <p className="text-green-700 text-sm mb-3">
            Sustainable materials and earth tones are gaining significant momentum
          </p>
          <div className="space-y-1 text-xs text-green-600">
            <div>• Recycled Polyester +28%</div>
            <div>• Sage Green +34%</div>
            <div>• Oversized Blazers +22%</div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-6 border border-blue-200">
          <div className="flex items-center mb-3">
            <div className="p-2 bg-blue-500 rounded-lg text-white mr-3">
              <TrendingUp className="w-5 h-5" />
            </div>
            <h4 className="font-semibold text-blue-800">Market Insights</h4>
          </div>
          <p className="text-blue-700 text-sm mb-3">
            Consumer preferences shifting towards comfort and sustainability
          </p>
          <div className="space-y-1 text-xs text-blue-600">
            <div>• 73% prefer sustainable materials</div>
            <div>• Comfort-wear up 45%</div>
            <div>• Bold colors gaining traction</div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-6 border border-purple-200">
          <div className="flex items-center mb-3">
            <div className="p-2 bg-purple-500 rounded-lg text-white mr-3">
              <Palette className="w-5 h-5" />
            </div>
            <h4 className="font-semibold text-purple-800">Color Forecast</h4>
          </div>
          <p className="text-purple-700 text-sm mb-3">
            Nature-inspired and tech-influenced colors dominating
          </p>
          <div className="space-y-1 text-xs text-purple-600">
            <div>• Earth tones +25% average</div>
            <div>• Digital brights emerging</div>
            <div>• Neutral bases remain strong</div>
          </div>
        </div>
      </div>
    </div>
  );
}