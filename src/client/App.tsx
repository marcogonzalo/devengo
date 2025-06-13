import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { HeroUIProvider } from "@heroui/react";
import Login from './components/Login';
import Dashboard from './components/Dashboard';

const App: React.FC = () => {
  return (
    <HeroUIProvider>
      <div className="dark min-h-screen bg-background text-foreground">
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/dashboard/*" element={<Dashboard />} />
        </Routes>
      </div>
    </HeroUIProvider>
  );
};

export default App;