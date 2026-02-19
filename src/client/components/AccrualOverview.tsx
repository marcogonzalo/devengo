import React, { useState, useEffect } from "react";
import { Button, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";
import { dashboardApi, DashboardSummary } from "../utils/api";
import PageHeader from "./ui/PageHeader";
import StatCard from "./ui/StatCard";

const AccrualOverview: React.FC = () => {
  const [overviewData, setOverviewData] = useState<DashboardSummary | null>(
    null,
  );
  const [currentYearData, setCurrentYearData] =
    useState<DashboardSummary | null>(null);
  const [lastYearData, setLastYearData] = useState<DashboardSummary | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const formatCurrency = (amount: number): string => {
    return amount.toLocaleString("de-DE", {
      style: "currency",
      currency: "EUR",
    });
  };

  const fetchDashboardSummaries = async () => {
    try {
      setLoading(true);
      setError(null);

      const [totalResponse, currentYearResponse, lastYearResponse] =
        await Promise.all([
          dashboardApi.getSummary(),
          dashboardApi.getSummaryCurrentYear(),
          dashboardApi.getSummaryLastYear(),
        ]);

      if (totalResponse.error) {
        setError(totalResponse.error);
        return;
      }
      if (currentYearResponse.error) {
        setError(currentYearResponse.error);
        return;
      }
      if (lastYearResponse.error) {
        setError(lastYearResponse.error);
        return;
      }

      if (totalResponse.data) setOverviewData(totalResponse.data);
      if (currentYearResponse.data)
        setCurrentYearData(currentYearResponse.data);
      if (lastYearResponse.data) setLastYearData(lastYearResponse.data);
    } catch (err) {
      setError("Failed to fetch dashboard summaries");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardSummaries();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div
          className="flex items-center gap-3 p-4 rounded-lg"
          style={{
            backgroundColor: "rgba(220,38,38,0.06)",
            border: "1px solid rgba(220,38,38,0.2)",
          }}
        >
          <Icon
            icon="lucide:alert-circle"
            width={18}
            height={18}
            style={{ color: "#dc2626" }}
          />
          <p className="text-sm" style={{ color: "#dc2626" }}>
            Error: {error}
          </p>
        </div>
      </div>
    );
  }

  if (!overviewData || !currentYearData || !lastYearData) return null;

  const currentYear = new Date().getFullYear();

  return (
    <div className="p-6 space-y-8">
      <PageHeader
        title="Accrual Overview"
        subtitle="Summary of contracts and accruals across all periods"
        actions={
          <Button
            size="sm"
            variant="bordered"
            onPress={fetchDashboardSummaries}
            isLoading={loading}
            startContent={
              !loading ? (
                <Icon icon="lucide:refresh-cw" width={14} height={14} />
              ) : undefined
            }
          >
            Refresh
          </Button>
        }
      />

      {/* Total */}
      <section>
        <h2
          className="text-sm font-semibold uppercase tracking-wider mb-3"
          style={{ color: "var(--muted-foreground)" }}
        >
          All time
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Contracts"
            value={overviewData.total_contracts}
            icon="lucide:file-text"
            color="blue"
          />
          <StatCard
            label="Contract Amount"
            value={formatCurrency(overviewData.total_amount)}
            icon="lucide:euro"
            color="green"
          />
          <StatCard
            label="Accrued Amount"
            value={formatCurrency(overviewData.accrued_amount)}
            icon="lucide:check-circle"
            color="cyan"
          />
          <StatCard
            label="Pending Amount"
            value={formatCurrency(overviewData.pending_amount)}
            icon="lucide:clock"
            color="amber"
          />
        </div>
      </section>

      {/* Current year */}
      <section>
        <h2
          className="text-sm font-semibold uppercase tracking-wider mb-3"
          style={{ color: "var(--muted-foreground)" }}
        >
          {currentYear} — Current year
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Contracts"
            value={currentYearData.total_contracts}
            icon="lucide:file-text"
            color="blue"
          />
          <StatCard
            label="Contract Amount"
            value={formatCurrency(currentYearData.total_amount)}
            icon="lucide:euro"
            color="green"
          />
          <StatCard
            label="Accrued Amount"
            value={formatCurrency(currentYearData.accrued_amount)}
            icon="lucide:check-circle"
            color="cyan"
          />
          <StatCard
            label="Pending Amount"
            value={formatCurrency(currentYearData.pending_amount)}
            icon="lucide:clock"
            color="amber"
          />
        </div>
      </section>

      {/* Last year */}
      <section>
        <h2
          className="text-sm font-semibold uppercase tracking-wider mb-3"
          style={{ color: "var(--muted-foreground)" }}
        >
          {currentYear - 1} — Last year
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Contracts"
            value={lastYearData.total_contracts}
            icon="lucide:file-text"
            color="blue"
          />
          <StatCard
            label="Contract Amount"
            value={formatCurrency(lastYearData.total_amount)}
            icon="lucide:euro"
            color="green"
          />
          <StatCard
            label="Accrued Amount"
            value={formatCurrency(lastYearData.accrued_amount)}
            icon="lucide:check-circle"
            color="cyan"
          />
          <StatCard
            label="Pending Amount"
            value={formatCurrency(lastYearData.pending_amount)}
            icon="lucide:clock"
            color="amber"
          />
        </div>
      </section>
    </div>
  );
};

export default AccrualOverview;
