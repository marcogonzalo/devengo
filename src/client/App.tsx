import React, { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { HeroUIProvider } from "@heroui/react";
import { useTheme } from "@heroui/use-theme";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";

const AppContent: React.FC = () => {
  const { setTheme } = useTheme();

  // Default to light mode on first load if no preference stored
  useEffect(() => {
    const stored = localStorage.getItem("heroui-theme");
    if (!stored) {
      setTheme("light");
    }
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard/*" element={<Dashboard />} />
      </Routes>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <HeroUIProvider>
      <AppContent />
    </HeroUIProvider>
  );
};

export default App;
