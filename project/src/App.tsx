import React, { useEffect } from 'react';
import { Data } from './pages/Data';
import ReactGA from "react-ga4";

ReactGA.initialize("G-B62YDVW6K9");

function App() {
  // ✅ Track initial page load
  useEffect(() => {
    ReactGA.send({ hitType: "pageview", page: window.location.pathname + window.location.search });
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <Data />
      </main>
    </div>
  );
}

function Header() {
  return (
    <header className="bg-[#98b78b] text-white shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center">
          <img 
            src="/cropped_image (2).png" 
            alt="Fashion Intelligence Logo" 
            className="w-12 h-12 mr-3"
          />
          <h1 className="text-xl font-semibold">Fashion Intelligence Dashboard</h1>
        </div>
      </div> 
    </header>
  );
}

export default App;
