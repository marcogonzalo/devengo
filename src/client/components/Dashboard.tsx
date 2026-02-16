import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { Navbar, NavbarBrand, NavbarContent, NavbarItem, Button, Switch } from "@heroui/react";
import { Icon } from '@iconify/react';
import { useTheme } from "@heroui/use-theme";
import ClientManagement from './ClientManagement';
import AccrualOverview from './AccrualOverview';
import AccrualReports from './AccrualReports';
import IntegrationErrors from './IntegrationErrors';
import SyncManagement from './SyncManagement';

const Dashboard: React.FC = () => {
  const { theme, setTheme } = useTheme();

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar isBordered>
        <NavbarBrand>
          <Icon icon="lucide:zap" className="text-primary text-2xl mr-2" />
          <p className="font-bold text-inherit">Devengo</p>
        </NavbarBrand>
        <NavbarContent className="hidden sm:flex gap-4" justify="center">
          <NavbarItem>
            <Link to="/dashboard" className="text-foreground">Overview</Link>
          </NavbarItem>
          <NavbarItem>
            <Link to="/dashboard/clients" className="text-foreground">Clients</Link>
          </NavbarItem>
          <NavbarItem>
            <Link to="/dashboard/reports" className="text-foreground">Reports</Link>
          </NavbarItem>
          <NavbarItem>
            <Link to="/dashboard/errors" className="text-foreground">Integration Errors</Link>
          </NavbarItem>
          <NavbarItem>
            <Link to="/dashboard/sync" className="text-foreground">Sync Management</Link>
          </NavbarItem>
        </NavbarContent>
        <NavbarContent justify="end">
          <NavbarItem>
            <Switch
              size="sm"
              color="primary"
              startContent={<Icon icon="lucide:sun" />}
              endContent={<Icon icon="lucide:moon" />}
              isSelected={theme === 'dark'}
              onValueChange={toggleTheme}
            />
          </NavbarItem>
          <NavbarItem>
            <Button color="primary" variant="flat">
              Log Out
            </Button>
          </NavbarItem>
        </NavbarContent>
      </Navbar>

      <main className="flex-grow p-4">
        <Routes>
          <Route path="/" element={<AccrualOverview />} />
          <Route path="/clients" element={<ClientManagement />} />
          <Route path="/reports" element={<AccrualReports />} />
          <Route path="/errors" element={<IntegrationErrors />} />
          <Route path="/sync" element={<SyncManagement />} />
        </Routes>
      </main>
    </div>
  );
};

export default Dashboard;