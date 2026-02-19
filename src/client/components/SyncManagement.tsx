import React, { useState, useEffect } from "react";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Input,
  Select,
  SelectItem,
  Radio,
  RadioGroup,
  Spinner,
  Divider,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import { syncAPI, ApiResponse, SyncStatusResponse } from "../utils/api";
import PageHeader from "./ui/PageHeader";

interface SyncStep {
  id: string;
  name: string;
  description: string;
}

interface AvailableSteps {
  import_steps: SyncStep[];
  accrual_steps: SyncStep[];
}

interface SyncResult {
  process_id: string;
  process_type: string;
  status: string;
  total_stats?: any;
  step_results?: any[];
}

const SyncManagement: React.FC = () => {
  const [availableSteps, setAvailableSteps] = useState<AvailableSteps>({
    import_steps: [],
    accrual_steps: [],
  });
  const [importStartingPoint, setImportStartingPoint] =
    useState<string>("invoices");
  const [accrualStartingPoint, setAccrualStartingPoint] =
    useState<string>("accruals");
  const [year, setYear] = useState<number>(new Date().getFullYear() - 1);
  const [selectedMonth, setSelectedMonth] = useState<number | null>(
    new Date().getMonth() === 0 ? 12 : new Date().getMonth(),
  );
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<SyncResult | null>(null);
  const [showImportSteps, setShowImportSteps] = useState<boolean>(false);

  // Load latest processed month and year from database
  useEffect(() => {
    const loadLatestProcessedMonthYear = async () => {
      try {
        const response = await syncAPI.getLatestProcessedMonthYear();
        if (
          response.data &&
          response.data.year !== null &&
          response.data.month !== null
        ) {
          setYear(response.data.year);
          setSelectedMonth(response.data.month);
        } else {
          // Fallback to last month if no data found
          const now = new Date();
          const lastMonth = now.getMonth() === 0 ? 12 : now.getMonth();
          const lastYear =
            now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();
          setYear(lastYear);
          setSelectedMonth(lastMonth);
        }
      } catch (error) {
        console.error("Error loading latest processed month/year:", error);
        // Fallback to last month on error
        const now = new Date();
        const lastMonth = now.getMonth() === 0 ? 12 : now.getMonth();
        const lastYear =
          now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();
        setYear(lastYear);
        setSelectedMonth(lastMonth);
      }
    };

    loadLatestProcessedMonthYear();
  }, []);

  // No auto-selection needed for starting point approach

  const loadAvailableSteps = async () => {
    try {
      const response: ApiResponse<AvailableSteps> =
        await syncAPI.getAvailableSteps();
      setAvailableSteps(response.data);
    } catch (error) {
      console.error("Error loading available steps:", error);
    }
  };

  const getMonthOptions = () => {
    return [
      { key: "1", label: "January" },
      { key: "2", label: "February" },
      { key: "3", label: "March" },
      { key: "4", label: "April" },
      { key: "5", label: "May" },
      { key: "6", label: "June" },
      { key: "7", label: "July" },
      { key: "8", label: "August" },
      { key: "9", label: "September" },
      { key: "10", label: "October" },
      { key: "11", label: "November" },
      { key: "12", label: "December" },
    ];
  };

  // No need for step toggle function with starting point approach

  const executeProcess = async (processType: "import" | "accrual") => {
    if (!year) {
      alert("Please specify a year");
      return;
    }

    const startingPoint =
      processType === "import" ? importStartingPoint : accrualStartingPoint;

    setIsLoading(true);
    try {
      const response: ApiResponse<SyncStatusResponse> =
        await syncAPI.executeProcess({
          process_type: processType,
          steps: [startingPoint], // Pass starting point as single-item array for compatibility
          year,
          month: selectedMonth || undefined,
        });
      setResults(response.data?.data);
    } catch (error) {
      console.error(`Error executing ${processType} process:`, error);
      alert(`Error executing ${processType} process: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const executeSingleStep = async (
    stepId: string,
    stepType: "import" | "accrual",
  ) => {
    if (!year) {
      alert("Please specify a year");
      return;
    }

    setIsLoading(true);
    try {
      const response: ApiResponse<SyncStatusResponse> =
        await syncAPI.executeStep({
          step: stepId,
          year,
          month: selectedMonth || undefined,
        });
      setResults(response.data?.data);
    } catch (error) {
      console.error(`Error executing step ${stepId}:`, error);
      alert(`Error executing step ${stepId}: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAvailableSteps();
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <PageHeader
        title="Sync Management"
        subtitle="Configure and run import and accrual sync processes"
        actions={
          <Button
            size="sm"
            variant="bordered"
            onPress={loadAvailableSteps}
            startContent={
              <Icon icon="lucide:refresh-cw" width={14} height={14} />
            }
          >
            Refresh Steps
          </Button>
        }
      />

      {/* Date Configuration */}
      <div
        className="rounded-xl p-5"
        style={{
          backgroundColor: "var(--card)",
          border: "1px solid var(--border)",
          boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)",
        }}
      >
        <p
          className="text-sm font-semibold mb-4"
          style={{ color: "var(--foreground)" }}
        >
          Date Configuration
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label
              className="block text-xs font-medium mb-1.5"
              style={{ color: "var(--muted-foreground)" }}
            >
              Year
            </label>
            <Input
              type="number"
              value={year.toString()}
              onChange={(e) =>
                setYear(parseInt(e.target.value) || new Date().getFullYear())
              }
              placeholder="Enter year"
              size="sm"
              variant="bordered"
              className="max-w-xs"
            />
          </div>
          <div>
            <label
              className="block text-xs font-medium mb-1.5"
              style={{ color: "var(--muted-foreground)" }}
            >
              Month (optional)
            </label>
            <Select
              placeholder="All months"
              selectedKeys={selectedMonth ? [selectedMonth.toString()] : []}
              onSelectionChange={(keys) => {
                const selected = Array.from(keys)[0] as string;
                setSelectedMonth(selected ? parseInt(selected) : null);
              }}
              size="sm"
              variant="bordered"
              className="max-w-xs"
            >
              {getMonthOptions().map((option) => (
                <SelectItem key={option.key}>{option.label}</SelectItem>
              ))}
            </Select>
          </div>
        </div>
      </div>

      {/* Import Steps */}
      <div
        className="rounded-xl overflow-hidden"
        style={{
          backgroundColor: "var(--card)",
          border: "1px solid var(--border)",
          boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)",
        }}
      >
        <div
          className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div>
            <p
              className="text-sm font-semibold"
              style={{ color: "var(--foreground)" }}
            >
              Import Steps
            </p>
            <p
              className="text-xs mt-0.5"
              style={{ color: "var(--muted-foreground)" }}
            >
              Starting from:{" "}
              {availableSteps.import_steps.find(
                (s) => s.id === importStartingPoint,
              )?.name || "Sync Invoices"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="bordered"
              onPress={() => setShowImportSteps(!showImportSteps)}
              endContent={
                <Icon
                  icon={
                    showImportSteps
                      ? "lucide:chevron-up"
                      : "lucide:chevron-down"
                  }
                  width={14}
                  height={14}
                />
              }
            >
              {showImportSteps ? "Hide" : "Show"} steps
            </Button>
            <Button
              size="sm"
              color="primary"
              onPress={() => executeProcess("import")}
              isDisabled={isLoading}
              startContent={
                isLoading ? (
                  <Spinner size="sm" />
                ) : (
                  <Icon icon="lucide:play" width={14} height={14} />
                )
              }
            >
              Run Import
            </Button>
          </div>
        </div>
        {showImportSteps && (
          <div className="p-5 space-y-2">
            <p
              className="text-xs mb-3"
              style={{ color: "var(--muted-foreground)" }}
            >
              Select the starting point. All steps from the selected point
              onwards will run in order.
            </p>
            <RadioGroup
              value={importStartingPoint}
              onValueChange={setImportStartingPoint}
              className="space-y-2"
            >
              {availableSteps.import_steps.map((step) => (
                <div
                  key={step.id}
                  className="flex items-center gap-3 p-3 rounded-lg transition-colors"
                  style={{ border: "1px solid var(--border)" }}
                >
                  <Radio value={step.id} />
                  <div className="flex-1 min-w-0">
                    <p
                      className="text-sm font-medium"
                      style={{ color: "var(--foreground)" }}
                    >
                      {step.name}
                    </p>
                    <p
                      className="text-xs mt-0.5"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      {step.description}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="flat"
                    color="primary"
                    onPress={() => executeSingleStep(step.id, "import")}
                    isDisabled={isLoading}
                    startContent={
                      isLoading ? (
                        <Spinner size="sm" />
                      ) : (
                        <Icon icon="lucide:play" width={13} height={13} />
                      )
                    }
                  >
                    Run
                  </Button>
                </div>
              ))}
            </RadioGroup>
          </div>
        )}
      </div>

      {/* Accrual Steps */}
      <div
        className="rounded-xl overflow-hidden"
        style={{
          backgroundColor: "var(--card)",
          border: "1px solid var(--border)",
          boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)",
        }}
      >
        <div
          className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div>
            <p
              className="text-sm font-semibold"
              style={{ color: "var(--foreground)" }}
            >
              Accrual Steps
            </p>
            <p
              className="text-xs mt-0.5"
              style={{ color: "var(--muted-foreground)" }}
            >
              Select the accrual process to execute
            </p>
          </div>
          <Button
            size="sm"
            color="primary"
            onPress={() => executeProcess("accrual")}
            isDisabled={isLoading}
            startContent={
              isLoading ? (
                <Spinner size="sm" />
              ) : (
                <Icon icon="lucide:play" width={14} height={14} />
              )
            }
          >
            Run Accruals
          </Button>
        </div>
        <div className="p-5 space-y-2">
          <RadioGroup
            value={accrualStartingPoint}
            onValueChange={setAccrualStartingPoint}
            className="space-y-2"
          >
            {availableSteps.accrual_steps.map((step) => (
              <div
                key={step.id}
                className="flex items-center gap-3 p-3 rounded-lg"
                style={{ border: "1px solid var(--border)" }}
              >
                <Radio value={step.id} />
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-medium"
                    style={{ color: "var(--foreground)" }}
                  >
                    {step.name}
                  </p>
                  <p
                    className="text-xs mt-0.5"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    {step.description}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="flat"
                  color="primary"
                  onPress={() => executeSingleStep(step.id, "accrual")}
                  isDisabled={isLoading}
                  startContent={
                    isLoading ? (
                      <Spinner size="sm" />
                    ) : (
                      <Icon icon="lucide:play" width={13} height={13} />
                    )
                  }
                >
                  Run
                </Button>
              </div>
            ))}
          </RadioGroup>
        </div>
      </div>

      {/* Results */}
      {results && (
        <div
          className="rounded-xl overflow-hidden"
          style={{
            backgroundColor: "var(--card)",
            border: "1px solid var(--border)",
            boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)",
          }}
        >
          <div
            className="px-5 py-4"
            style={{ borderBottom: "1px solid var(--border)" }}
          >
            <p
              className="text-sm font-semibold"
              style={{ color: "var(--foreground)" }}
            >
              Execution Results
            </p>
          </div>
          <div className="p-5 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                {
                  label: "Processed",
                  value: results.total_stats?.total_processed || 0,
                  color: "#1976d2",
                  bg: "rgba(25,118,210,0.06)",
                },
                {
                  label: "Created",
                  value: results.total_stats?.total_created || 0,
                  color: "#16a34a",
                  bg: "rgba(22,163,74,0.06)",
                },
                {
                  label: "Updated",
                  value: results.total_stats?.total_updated || 0,
                  color: "#d97706",
                  bg: "rgba(217,119,6,0.06)",
                },
                {
                  label: "Errors",
                  value: results.total_stats?.total_errors || 0,
                  color: "#dc2626",
                  bg: "rgba(220,38,38,0.06)",
                },
              ].map(({ label, value, color, bg }) => (
                <div
                  key={label}
                  className="p-3 rounded-lg text-center"
                  style={{ backgroundColor: bg }}
                >
                  <p className="text-2xl font-bold" style={{ color }}>
                    {value}
                  </p>
                  <p className="text-xs font-medium mt-0.5" style={{ color }}>
                    {label}
                  </p>
                </div>
              ))}
            </div>

            {results.step_results && results.step_results.length > 0 && (
              <div>
                <p
                  className="text-xs font-semibold uppercase tracking-wider mb-2"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  Step details
                </p>
                <div className="space-y-2">
                  {results.step_results.map((stepResult, index) => (
                    <div
                      key={index}
                      className="p-3 rounded-lg"
                      style={{ border: "1px solid var(--border)" }}
                    >
                      <p
                        className="text-sm font-medium"
                        style={{ color: "var(--foreground)" }}
                      >
                        {stepResult.step}
                      </p>
                      <p
                        className="text-xs mt-1"
                        style={{ color: "var(--muted-foreground)" }}
                      >
                        {stepResult.step === "invoices" &&
                          stepResult.stats?.total_received != null &&
                          `Received: ${stepResult.stats.total_received} · `}
                        Processed: {stepResult.stats?.total_processed || 0} ·
                        Created: {stepResult.stats?.total_created || 0} ·
                        Updated: {stepResult.stats?.total_updated || 0} ·
                        Errors: {stepResult.stats?.total_errors || 0}
                      </p>
                      {stepResult.stats?.error && (
                        <p
                          className="text-xs mt-1"
                          style={{ color: "#dc2626" }}
                        >
                          Error: {stepResult.stats.error}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SyncManagement;
