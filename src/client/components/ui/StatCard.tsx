import React from "react";
import { Icon } from "@iconify/react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: string;
  /** Tailwind color name for the icon background, e.g. 'blue', 'green', 'amber', 'purple' */
  color?: "blue" | "green" | "amber" | "purple" | "red" | "cyan";
  sublabel?: string;
}

const colorMap: Record<
  string,
  { bg: string; iconColor: string; iconBg: string }
> = {
  blue: { bg: "#fff", iconColor: "#1976d2", iconBg: "rgba(25,118,210,0.1)" },
  green: { bg: "#fff", iconColor: "#16a34a", iconBg: "rgba(22,163,74,0.1)" },
  amber: { bg: "#fff", iconColor: "#d97706", iconBg: "rgba(217,119,6,0.1)" },
  purple: { bg: "#fff", iconColor: "#7c3aed", iconBg: "rgba(124,58,237,0.1)" },
  red: { bg: "#fff", iconColor: "#dc2626", iconBg: "rgba(220,38,38,0.1)" },
  cyan: { bg: "#fff", iconColor: "#0891b2", iconBg: "rgba(8,145,178,0.1)" },
};

const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon,
  color = "blue",
  sublabel,
}) => {
  const colors = colorMap[color];

  return (
    <div
      className="rounded-xl p-5 flex items-start justify-between"
      style={{
        backgroundColor: "var(--card)",
        border: "1px solid var(--border)",
        boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)",
      }}
    >
      <div className="flex flex-col gap-1">
        <span
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: "var(--muted-foreground)", letterSpacing: "0.06em" }}
        >
          {label}
        </span>
        <span
          className="text-xl font-bold mt-1"
          style={{ color: "var(--foreground)" }}
        >
          {value}
        </span>
        {sublabel && (
          <span
            className="text-xs mt-0.5"
            style={{ color: "var(--muted-foreground)" }}
          >
            {sublabel}
          </span>
        )}
      </div>
      <div
        className="flex items-center justify-center rounded-xl shrink-0"
        style={{
          width: 44,
          height: 44,
          backgroundColor: colors.iconBg,
        }}
      >
        <Icon
          icon={icon}
          width={22}
          height={22}
          style={{ color: colors.iconColor }}
        />
      </div>
    </div>
  );
};

export default StatCard;
