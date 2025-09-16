import React from 'react';

interface PieChartData {
  name: string;
  value: number;
  color?: string;
}

interface PieChartProps {
  data: PieChartData[];
  size?: number;
  showLabels?: boolean;
  type?: 'color' | 'item' | 'material';
  showAll?: boolean;
  onToggleShowAll?: () => void;
}

export function PieChart({ data, size = 200, showLabels = true, type = 'item', showAll = false, onToggleShowAll }: PieChartProps) {
  const displayData = data.slice(0, 10);
  const total = displayData.reduce((sum, item) => sum + item.value, 0);
  const radius = size / 2 - 10;
  const centerX = size / 2;
  const centerY = size / 2;

  let cumulativePercentage = 0;

  const generateColor = (index: number) => {
    const colors = [
      '#10B981', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444',
      '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
    ];
    return colors[index % colors.length];
  };

  const createArcPath = (startAngle: number, endAngle: number) => {
    const start = polarToCartesian(centerX, centerY, radius, endAngle);
    const end = polarToCartesian(centerX, centerY, radius, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
    
    return [
      "M", centerX, centerY,
      "L", start.x, start.y,
      "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y,
      "Z"
    ].join(" ");
  };

  const polarToCartesian = (centerX: number, centerY: number, radius: number, angleInDegrees: number) => {
    const angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
    return {
      x: centerX + (radius * Math.cos(angleInRadians)),
      y: centerY + (radius * Math.sin(angleInRadians))
    };
  };

  if (total === 0) {
    return (
      <div className="flex items-center justify-center" style={{ width: size, height: size }}>
        <div className="text-gray-400 text-sm">No data</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="mb-4">
        {displayData.map((item, index) => {
          const percentage = (item.value / total) * 100;
          const startAngle = cumulativePercentage * 3.6;
          const endAngle = (cumulativePercentage + percentage) * 3.6;
          
          cumulativePercentage += percentage;
          
          const pathData = createArcPath(startAngle, endAngle);
          const fillColor = type === 'color' && item.color ? item.color : generateColor(index);
          
          return (
            <path
              key={index}
              d={pathData}
              fill={fillColor}
              stroke="white"
              strokeWidth="2"
              className="hover:opacity-80 transition-opacity cursor-pointer"
            />
          );
        })}
      </svg>
      
      {showLabels && (
        <div className="space-y-2 w-full max-w-xs">
          {displayData.slice(0, 5).map((item, index) => {
            const percentage = ((item.value / total) * 100).toFixed(1);
            const fillColor = type === 'color' && item.color ? item.color : generateColor(index);
            
            return (
              <div key={index} className="flex items-center justify-between text-sm">
                <div className="flex items-center flex-1 min-w-0">
                  <div
                    className="w-3 h-3 rounded-full mr-2 flex-shrink-0"
                    style={{ backgroundColor: fillColor }}
                  />
                  <span className="text-gray-700 truncate">{item.name}</span>
                </div>
                <div className="flex items-center ml-2 flex-shrink-0">
                  <span className="text-gray-600 text-xs mr-1">{item.value}</span>
                  <span className="text-gray-500 text-xs">({percentage}%)</span>
                </div>
              </div>
            );
          })}
          {displayData.length > 5 && onToggleShowAll && (
            <button 
              onClick={onToggleShowAll}
              className="text-xs text-blue-500 hover:text-blue-700 text-center pt-1 cursor-pointer hover:underline"
            >
              +{displayData.length - 5} more items
            </button>
          )}
        </div>
      )}
    </div>
  );
}