import React, { useState, useEffect } from "react";
import { Select, SelectItem, Button, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";
import {
  accrualReportsApi,
  MonthlyAccrualData,
  YearlyAccrualSummary,
} from "../utils/api";
import PageHeader from "./ui/PageHeader";
import StatCard from "./ui/StatCard";

const AccrualReports: React.FC = () => {
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [monthlyData, setMonthlyData] = useState<MonthlyAccrualData[]>([]);
  const [totalYearAmount, setTotalYearAmount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatCurrency = (amount: number): string => {
    return amount.toLocaleString("de-DE", {
      style: "currency",
      currency: "EUR",
    });
  };

  const fetchAvailableYears = async () => {
    try {
      const response = await accrualReportsApi.getAvailableYears();
      if (response.error) {
        setError(response.error);
      } else if (response.data) {
        setAvailableYears(response.data.years);
        // Set current year as default if available
        const currentYear = new Date().getFullYear();
        const defaultYear = response.data.years.includes(currentYear)
          ? currentYear
          : response.data.years[0];
        setSelectedYear(defaultYear.toString());
      }
    } catch (err) {
      setError("Failed to fetch available years");
      console.error("Error fetching available years:", err);
    }
  };

  const fetchMonthlyData = async (year: number) => {
    try {
      setLoading(true);
      const response = await accrualReportsApi.getMonthlyAccruals(year);
      if (response.error) {
        setError(response.error);
      } else if (response.data) {
        setMonthlyData(response.data.monthly_data);
        setTotalYearAmount(response.data.total_year_amount);
        setError(null);
      }
    } catch (err) {
      setError("Failed to fetch monthly data");
      console.error("Error fetching monthly data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleYearChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const year = e.target.value;
    setSelectedYear(year);
    if (year) {
      fetchMonthlyData(parseInt(year));
    }
  };

  const handleDownloadCSV = async () => {
    if (!selectedYear) return;

    try {
      setDownloading(true);
      await accrualReportsApi.downloadYearCSV(parseInt(selectedYear));
    } catch (err) {
      console.error("Error downloading CSV:", err);
      setError("Failed to download CSV file");
    } finally {
      setDownloading(false);
    }
  };

  useEffect(() => {
    fetchAvailableYears();
  }, []);

  useEffect(() => {
    if (selectedYear) {
      fetchMonthlyData(parseInt(selectedYear));
    }
  }, [selectedYear]);

  if (loading && !monthlyData.length) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  if (error && !monthlyData.length) {
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

  const nonZeroMonths = monthlyData.filter((d) => d.amount > 0).length;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Accrual Reports"
        subtitle="Monthly accrual breakdown by year"
        actions={
          <div className="flex items-center gap-2">
            <Select
              selectedKeys={selectedYear ? [selectedYear] : []}
              onChange={handleYearChange}
              size="sm"
              className="w-28"
              isDisabled={loading}
              aria-label="Select year"
            >
              {availableYears.map((year) => (
                <SelectItem key={year.toString()}>{year.toString()}</SelectItem>
              ))}
            </Select>
            <Button
              size="sm"
              color="primary"
              onPress={handleDownloadCSV}
              isLoading={downloading}
              isDisabled={!selectedYear}
              startContent={
                !downloading ? (
                  <Icon icon="lucide:download" width={14} height={14} />
                ) : undefined
              }
            >
              Export CSV
            </Button>
          </div>
        }
      />

      {/* Summary stat */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label={`Total ${selectedYear}`}
          value={formatCurrency(totalYearAmount)}
          icon="lucide:euro"
          color="blue"
        />
        <StatCard
          label="Active months"
          value={nonZeroMonths}
          icon="lucide:calendar"
          color="green"
          sublabel={`out of ${monthlyData.length}`}
        />
        <StatCard
          label="Monthly average"
          value={
            nonZeroMonths > 0
              ? formatCurrency(totalYearAmount / nonZeroMonths)
              : "—"
          }
          icon="lucide:trending-up"
          color="cyan"
        />
      </div>

      {/* Monthly table */}
      <div
        className="rounded-xl overflow-hidden"
        style={{
          backgroundColor: "var(--card)",
          border: "1px solid var(--border)",
          boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)",
        }}
      >
        <div
          className="px-5 py-3 flex items-center justify-between"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <h2
            className="text-sm font-semibold"
            style={{ color: "var(--foreground)" }}
          >
            Monthly breakdown — {selectedYear}
          </h2>
          {error && (
            <span className="text-xs" style={{ color: "#dc2626" }}>
              {error}
            </span>
          )}
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <Spinner size="md" color="primary" />
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: "var(--border)" }}>
            {monthlyData.map((data, idx) => (
              <div
                key={data.month}
                className="flex items-center justify-between px-5 py-3 transition-colors"
                style={{
                  backgroundColor:
                    idx % 2 === 0 ? "transparent" : "rgba(0,0,0,0.01)",
                }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="flex items-center justify-center rounded-lg shrink-0"
                    style={{
                      width: 32,
                      height: 32,
                      backgroundColor: "rgba(25,118,210,0.08)",
                    }}
                  >
                    <Icon
                      icon="lucide:calendar"
                      width={15}
                      height={15}
                      style={{ color: "#1976d2" }}
                    />
                  </div>
                  <span
                    className="text-sm font-medium"
                    style={{ color: "var(--foreground)" }}
                  >
                    {data.month}
                  </span>
                </div>
                <span
                  className="text-sm font-semibold tabular-nums"
                  style={{
                    color:
                      data.amount > 0 ? "#16a34a" : "var(--muted-foreground)",
                  }}
                >
                  {formatCurrency(data.amount)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AccrualReports;
