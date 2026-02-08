import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './components/HomePage';
import Onboarding from './components/Onboarding';
import MainApp from './components/MainApp';

function App() {
  const [userData, setUserData] = useState<any>(null);

  // Initialize User ID on App Load
  React.useEffect(() => {
    const getUserId = async () => {
      try {
        const existing = localStorage.getItem("user_id");
        if (existing) {
          console.log("Found existing user_id:", existing);
          return;
        }

        const res = await fetch("http://localhost:8000/generate-user-id");
        if (!res.ok) throw new Error("Failed to generate user ID");

        const data = await res.json();
        console.log("Generated new user_id:", data.user_id);
        localStorage.setItem("user_id", data.user_id);
      } catch (error) {
        console.error("Error initializing user_id:", error);
      }
    };

    getUserId();
  }, []);

  // Wrapper for MainApp to pass userData and handle mode
  const MainAppWrapper = ({ mode }: { mode: 'agent' | 'creator' }) => {
    // In a real app, you might want to redirect to /onboarding if no userData
    // For now, we'll allow access or you can use a default
    const effectiveUserData = userData || { companyName: 'Demo Company' };

    return <MainApp userData={effectiveUserData} initialMode={mode} />;
  };

  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/onboarding"
          element={<Onboarding onFinish={(data) => setUserData(data)} />}
        />
        <Route path="/agent" element={<MainAppWrapper mode="agent" />} />
        <Route path="/creator" element={<MainAppWrapper mode="creator" />} />
        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;