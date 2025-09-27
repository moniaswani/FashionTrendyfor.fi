import React from 'react';
import { BarChart3, Database, TrendingUp } from 'lucide-react';

interface NavigationProps {
  currentPage: string;
  onPageChange: (page: string) => void;
}

export function Navigation({ currentPage, onPageChange }: NavigationProps) {
  const pages = [
    { id: 'overview', name: 'Overview', icon: BarChart3 },
    { id: 'data', name: 'Data', icon: Database },
    { id: 'fashion-statistics', name: 'Fashion Statistics', icon: TrendingUp },
  ];

  return (
    <nav className="flex space-x-1">
      {pages.map((page) => {
        const Icon = page.icon;
        return (
          <button
            key={page.id}
            onClick={() => onPageChange(page.id)}
            className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              currentPage === page.id
                ? 'bg-white/20 text-white'
                : 'text-white/80 hover:text-white hover:bg-white/10'
            }`}
          >
            <Icon className="w-4 h-4 mr-2" />
            {page.name}
          </button>
        );
      })}
    </nav>
  );
}