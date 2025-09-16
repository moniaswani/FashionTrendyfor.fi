import React from 'react';
import { ChevronDown } from 'lucide-react';

interface Option {
  id: string;
  name: string;
  description: string;
}

interface UnifiedSelectorProps {
  options: Option[];
  currentOption: string;
  onOptionChange: (optionId: string) => void;
}

export function UnifiedSelector({
  options,
  currentOption,
  onOptionChange,
}: UnifiedSelectorProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const currentOptionInfo = options.find((o) => o.id === currentOption);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full max-w-md bg-white border border-gray-200 rounded-lg px-4 py-3 text-left shadow-sm hover:shadow-md transition-shadow"
      >
        <div>
          <div className="font-medium text-gray-900">{currentOptionInfo?.name}</div>
          <div className="text-sm text-gray-500">{currentOptionInfo?.description}</div>
        </div>
        <ChevronDown
          className={`w-5 h-5 text-gray-400 transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
          {options.map((option) => (
            <button
              key={option.id}
              onClick={() => {
                onOptionChange(option.id);
                setIsOpen(false);
              }}
              className={`w-full text-left px-4 py-3 hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg ${
                option.id === currentOption
                  ? 'bg-green-50 border-l-4 border-green-500'
                  : ''
              }`}
            >
              <div className="font-medium text-gray-900">{option.name}</div>
              <div className="text-sm text-gray-500">{option.description}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
