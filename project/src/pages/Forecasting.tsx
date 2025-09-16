import React from 'react';
import { TrendingUp, Calendar, Target, BarChart } from 'lucide-react';

export function Forecasting() {
  const forecasts = [
    {
      title: 'Color Trends Q2 2025',
      accuracy: '87%',
      status: 'Active',
      lastUpdated: '2 days ago',
      icon: Target,
    },
    {
      title: 'Material Preferences',
      accuracy: '92%',
      status: 'Training',
      lastUpdated: '5 hours ago',
      icon: BarChart,
    },
    {
      title: 'Seasonal Patterns',
      accuracy: '79%',
      status: 'Pending',
      lastUpdated: '1 week ago',
      icon: Calendar,
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Fashion forecasting</h2>
        <p className="text-gray-600">
          AI-powered trend prediction and fashion forecasting models.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {forecasts.map((forecast, index) => {
          const Icon = forecast.icon;
          return (
            <div key={index} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className="bg-purple-100 p-2 rounded-lg">
                    <Icon className="w-5 h-5 text-purple-600" />
                  </div>
                  <div className="ml-3">
                    <h3 className="font-semibold text-gray-900">{forecast.title}</h3>
                    <p className="text-sm text-gray-500">Updated {forecast.lastUpdated}</p>
                  </div>
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Accuracy</span>
                  <span className="font-semibold text-green-600">{forecast.accuracy}</span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Status</span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    forecast.status === 'Active' ? 'bg-green-100 text-green-800' :
                    forecast.status === 'Training' ? 'bg-blue-100 text-blue-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {forecast.status}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center mb-6">
          <TrendingUp className="w-6 h-6 text-purple-600 mr-3" />
          <h3 className="text-xl font-semibold text-gray-900">Trend predictions</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h4 className="font-medium text-gray-900">Upcoming color trends</h4>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-emerald-500 rounded-full mr-3"></div>
                  <span className="text-sm font-medium">Emerald green</span>
                </div>
                <span className="text-sm text-gray-600">+15% trend</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-orange-400 rounded-full mr-3"></div>
                  <span className="text-sm font-medium">Warm orange</span>
                </div>
                <span className="text-sm text-gray-600">+12% trend</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-purple-500 rounded-full mr-3"></div>
                  <span className="text-sm font-medium">Deep purple</span>
                </div>
                <span className="text-sm text-gray-600">+8% trend</span>
              </div>
            </div>
          </div>
          
          <div className="space-y-4">
            <h4 className="font-medium text-gray-900">Material predictions</h4>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium">Sustainable fabrics</span>
                <span className="text-sm text-green-600">+22% growth</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium">Technical textiles</span>
                <span className="text-sm text-green-600">+18% growth</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium">Recycled materials</span>
                <span className="text-sm text-green-600">+14% growth</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}