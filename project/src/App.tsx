import React, { useState } from 'react';
import { Navigation } from './components/Navigation';
import { Overview } from './pages/Overview';
import { Data } from './pages/Data';
import { FashionStatistics } from './pages/FashionStatistics';

function App() {
  const [currentPage, setCurrentPage] = useState('overview');

  const renderPage = () => {
    switch (currentPage) {
      case 'overview':
        return <Overview />;
      case 'data':
        return <Data />;
      case 'fashion-statistics':
        return <FashionStatistics />;
      default:
        return <Overview />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header currentPage={currentPage} onPageChange={setCurrentPage} />
      
      <main className="container mx-auto px-4 py-8">
        {renderPage()}
      </main>
    </div>
  );
}

interface HeaderProps {
  currentPage: string;
  onPageChange: (page: string) => void;
}

function Header({ currentPage, onPageChange }: HeaderProps) {
  return (
    <header className="bg-[#98b78b] text-white shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <img 
              src="/cropped_image (2).png" 
              alt="Fashion Intelligence Logo" 
              className="w-12 h-12 mr-3"
            />
          </div>
          <Navigation currentPage={currentPage} onPageChange={onPageChange} />
        </div>
      </div>
    </header>
  );
}

export default App;