import React, { useState } from "react";
import {
  Routes,
  Route,
  Link,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { Button, Tooltip, Avatar } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useTheme } from "@heroui/use-theme";
import ClientManagement from "./ClientManagement";
import AccrualOverview from "./AccrualOverview";
import AccrualReports from "./AccrualReports";
import IntegrationErrors from "./IntegrationErrors";
import SyncManagement from "./SyncManagement";

interface NavItem {
  label: string;
  icon: string;
  path: string;
}

const navItems: NavItem[] = [
  { label: "Overview", icon: "lucide:bar-chart-2", path: "/dashboard" },
  { label: "Clients", icon: "lucide:users", path: "/dashboard/clients" },
  { label: "Reports", icon: "lucide:book-open", path: "/dashboard/reports" },
  { label: "Sync", icon: "lucide:refresh-cw", path: "/dashboard/sync" },
  { label: "Errors", icon: "lucide:zap", path: "/dashboard/errors" },
];

const Dashboard: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  const isActive = (path: string) => {
    if (path === "/dashboard") {
      return (
        location.pathname === "/dashboard" ||
        location.pathname === "/dashboard/"
      );
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div
      className="min-h-screen flex"
      style={{ backgroundColor: "var(--background)" }}
    >
      {/* Sidebar */}
      <aside
        className="fixed left-0 top-0 h-full z-50 flex flex-col transition-[width] duration-200 ease-in-out"
        style={{
          width: isExpanded
            ? "var(--sidebar-width-expanded)"
            : "var(--sidebar-width)",
          backgroundColor: "var(--sidebar-background)",
          borderRight: "1px solid var(--sidebar-border)",
        }}
        onMouseEnter={() => setIsExpanded(true)}
        onMouseLeave={() => setIsExpanded(false)}
      >
        {/* Logo */}
        <div
          className="flex items-center h-14 px-3 shrink-0 overflow-hidden"
          style={{ borderBottom: "1px solid var(--sidebar-border)" }}
        >
          <div
            className="flex items-center justify-center shrink-0 rounded-lg"
            style={{
              width: 32,
              height: 32,
              backgroundColor: "var(--primary)",
              color: "#fff",
              flexShrink: 0,
            }}
          >
            <Icon icon="lucide:zap" width={16} height={16} />
          </div>
          <span
            className="ml-3 font-bold text-sm whitespace-nowrap overflow-hidden transition-opacity duration-150"
            style={{
              color: "var(--foreground)",
              opacity: isExpanded ? 1 : 0,
              maxWidth: isExpanded ? 160 : 0,
              letterSpacing: "-0.01em",
            }}
          >
            Devengo
          </span>
        </div>

        {/* Nav items */}
        <nav className="flex flex-col gap-0.5 px-2 pt-3 flex-1 overflow-hidden">
          {navItems.map((item) => {
            const active = isActive(item.path);
            return (
              <Tooltip
                key={item.path}
                content={item.label}
                placement="right"
                isDisabled={isExpanded}
              >
                <Link
                  to={item.path}
                  className="flex items-center gap-3 px-2 py-2 rounded-lg transition-colors duration-100 outline-none"
                  style={{
                    color: active
                      ? "var(--primary)"
                      : "var(--sidebar-foreground)",
                    backgroundColor: active
                      ? "rgba(25,118,210,0.08)"
                      : "transparent",
                    minHeight: 36,
                    overflow: "hidden",
                    position: "relative",
                  }}
                  onMouseEnter={(e) => {
                    if (!active)
                      (e.currentTarget as HTMLElement).style.backgroundColor =
                        "var(--sidebar-accent)";
                  }}
                  onMouseLeave={(e) => {
                    if (!active)
                      (e.currentTarget as HTMLElement).style.backgroundColor =
                        "transparent";
                  }}
                >
                  {active && (
                    <span
                      className="absolute left-0 top-1/2 -translate-y-1/2 rounded-r-full"
                      style={{
                        width: 3,
                        height: 20,
                        backgroundColor: "var(--primary)",
                      }}
                    />
                  )}
                  <Icon
                    icon={item.icon}
                    width={18}
                    height={18}
                    className="shrink-0"
                    style={{
                      color: active
                        ? "var(--primary)"
                        : "var(--sidebar-foreground)",
                    }}
                  />
                  <span
                    className="text-sm font-medium whitespace-nowrap overflow-hidden transition-opacity duration-150"
                    style={{
                      color: active
                        ? "var(--primary)"
                        : "var(--sidebar-foreground)",
                      opacity: isExpanded ? 1 : 0,
                      maxWidth: isExpanded ? 160 : 0,
                    }}
                  >
                    {item.label}
                  </span>
                </Link>
              </Tooltip>
            );
          })}
        </nav>

        {/* Bottom actions */}
        <div
          className="flex flex-col gap-0.5 px-2 pb-3 shrink-0"
          style={{
            borderTop: "1px solid var(--sidebar-border)",
            paddingTop: 8,
          }}
        >
          {/* Theme toggle */}
          <Tooltip
            content={theme === "dark" ? "Light mode" : "Dark mode"}
            placement="right"
            isDisabled={isExpanded}
          >
            <button
              onClick={toggleTheme}
              className="flex items-center gap-3 px-2 py-2 rounded-lg transition-colors duration-100 w-full"
              style={{ color: "var(--sidebar-foreground)" }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.backgroundColor =
                  "var(--sidebar-accent)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.backgroundColor =
                  "transparent";
              }}
            >
              <Icon
                icon={theme === "dark" ? "lucide:sun" : "lucide:moon"}
                width={18}
                height={18}
                className="shrink-0"
              />
              <span
                className="text-sm font-medium whitespace-nowrap overflow-hidden transition-opacity duration-150"
                style={{
                  opacity: isExpanded ? 1 : 0,
                  maxWidth: isExpanded ? 160 : 0,
                }}
              >
                {theme === "dark" ? "Light mode" : "Dark mode"}
              </span>
            </button>
          </Tooltip>

          {/* Logout */}
          <Tooltip content="Log out" placement="right" isDisabled={isExpanded}>
            <button
              onClick={() => navigate("/")}
              className="flex items-center gap-3 px-2 py-2 rounded-lg transition-colors duration-100 w-full"
              style={{ color: "var(--sidebar-foreground)" }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.backgroundColor =
                  "var(--sidebar-accent)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.backgroundColor =
                  "transparent";
              }}
            >
              <Icon
                icon="lucide:log-out"
                width={18}
                height={18}
                className="shrink-0"
              />
              <span
                className="text-sm font-medium whitespace-nowrap overflow-hidden transition-opacity duration-150"
                style={{
                  opacity: isExpanded ? 1 : 0,
                  maxWidth: isExpanded ? 160 : 0,
                }}
              >
                Log out
              </span>
            </button>
          </Tooltip>
        </div>
      </aside>

      {/* Main content */}
      <main
        className="flex-1 min-h-screen overflow-auto transition-all duration-200"
        style={{
          marginLeft: "var(--sidebar-width)",
          backgroundColor: "var(--content-bg, #f8fafc)",
        }}
      >
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
