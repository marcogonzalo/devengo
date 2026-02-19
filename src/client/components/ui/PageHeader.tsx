import React from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  actions,
}) => {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1
          className="text-xl font-semibold"
          style={{ color: "var(--foreground)" }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            className="text-sm mt-0.5"
            style={{ color: "var(--muted-foreground)" }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      )}
    </div>
  );
};

export default PageHeader;
