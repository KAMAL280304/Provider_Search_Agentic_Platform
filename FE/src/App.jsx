import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './Login';
import AgenticMemberPortalDemo from './AgenticMemberPortalDemo';
import LandingPage from './LandingPage';
import ProviderDashboard from './ProviderDashboard';
import PayerDashboard from './PayerDashboard';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('member'));

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login onLogin={() => setIsLoggedIn(true)} />} />
        <Route
          path="/"
          element={isLoggedIn ? <LandingPage onLogout={() => setIsLoggedIn(false)} /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/chat"
          element={isLoggedIn ? <AgenticMemberPortalDemo onLogout={() => setIsLoggedIn(false)} /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/provider"
          element={isLoggedIn ? <ProviderDashboard /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/payer"
          element={isLoggedIn ? <PayerDashboard /> : <Navigate to="/login" replace />}
        />
      </Routes>
    </Router>
  );
}

export default App;
