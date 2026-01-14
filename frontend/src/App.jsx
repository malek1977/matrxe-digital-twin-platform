import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-900 text-white">
        <Routes>
          <Route path="/" element={<h1 className="text-4xl text-center mt-10">🚀 MATRXe Platform</h1>} />
          <Route path="/app" element={<h1 className="text-4xl text-center mt-10">📱 Dashboard</h1>} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;