import React, { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import { Data } from "./pages/Data";
import { Chatbot } from "./pages/Chatbot";
import ReactGA from "react-ga4";

ReactGA.initialize("G-B62YDVW6K9");

function App() {
  useEffect(() => {
    ReactGA.send({
      hitType: "pageview",
      page: window.location.pathname + window.location.search,
    });
  }, []);

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Data />} />
            <Route path="/chat" element={<Chatbot />} /> {/* ✅ Add chatbot route */}
          </Routes>
        </main>
      </div>
    </Router>
  );
}

function Header() {
  return (
    <header className="bg-[#98b78b] text-white shadow-lg">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <div className="flex items-center">
          <img
            src="/cropped_image (2).png"
            alt="Fashion Intelligence Logo"
            className="w-12 h-12 mr-3"
          />
          <h1 className="text-xl font-semibold">Fashion Intelligence</h1>
        </div>
        <nav className="space-x-4">
          <Link to="/" className="hover:underline">
            Dashboard
          </Link>
          <Link to="/chat" className="hover:underline">
            Chatbot
          </Link>
        </nav>
      </div>
    </header>
  );
}

export default App;
