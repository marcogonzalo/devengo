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
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Sync Management</h1>
        <Button
          color="secondary"
          variant="flat"
          onPress={loadAvailableSteps}
          startContent={<Icon icon="lucide:refresh-cw" />}
        >
          Refresh Steps
        </Button>
      </div>

      {/* Date Configuration */}
      <Card>
        <CardHeader>
          <h2 className="text-xl font-semibold">Date Configuration</h2>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Year</label>
              <Input
                type="number"
                value={year.toString()}
                onChange={(e) =>
                  setYear(parseInt(e.target.value) || new Date().getFullYear())
                }
                placeholder="Enter year"
                className="max-w-xs"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                Month (Optional)
              </label>
              <Select
                placeholder="Select a specific month (leave empty for all months)"
                selectedKeys={selectedMonth ? [selectedMonth.toString()] : []}
                onSelectionChange={(keys) => {
                  const selected = Array.from(keys)[0] as string;
                  setSelectedMonth(selected ? parseInt(selected) : null);
                }}
                className="max-w-xs"
              >
                {getMonthOptions().map((option) => (
                  <SelectItem key={option.key}>{option.label}</SelectItem>
                ))}
              </Select>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Import Steps */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center space-x-3">
              <h3 className="text-lg font-medium">Import Steps</h3>
              <span className="text-sm text-gray-500">
                (Starting from:{" "}
                {availableSteps.import_steps.find(
                  (step) => step.id === importStartingPoint,
                )?.name || "Sync Invoices"}
                )
              </span>
            </div>
            <Button
              size="sm"
              variant="flat"
              color="secondary"
              onPress={() => setShowImportSteps(!showImportSteps)}
              startContent={
                <Icon
                  icon={
                    showImportSteps
                      ? "lucide:chevron-up"
                      : "lucide:chevron-down"
                  }
                />
              }
            >
              {showImportSteps ? "Hide" : "Show"} Steps
            </Button>
          </div>
        </CardHeader>
        {showImportSteps && (
          <CardBody>
            <div className="space-y-4">
              <div className="text-sm text-gray-600 mb-4">
                Select the starting point for the import process. All steps from
                the selected point onwards will be executed in order.
              </div>
              <RadioGroup
                value={importStartingPoint}
                onValueChange={setImportStartingPoint}
                className="space-y-3"
              >
                {availableSteps.import_steps.map((step) => (
                  <div
                    key={step.id}
                    className="flex items-start space-x-3 p-3 border rounded-lg"
                  >
                    <Radio value={step.id} />
                    <div className="flex-1">
                      <div className="font-medium">{step.name}</div>
                      <div className="text-sm text-gray-600">
                        {step.description}
                      </div>
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
                          <Icon icon="lucide:play" />
                        )
                      }
                    >
                      Run
                    </Button>
                  </div>
                ))}
              </RadioGroup>
            </div>
          </CardBody>
        )}

        {/* Execute Import Process Button - Always visible */}
        <CardBody className="pt-0">
          <div className="flex justify-end">
            <Button
              color="primary"
              size="lg"
              onPress={() => executeProcess("import")}
              isDisabled={isLoading}
              startContent={
                isLoading ? <Spinner size="sm" /> : <Icon icon="lucide:play" />
              }
            >
              Execute Import Process
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Accrual Steps */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-medium">Accrual Steps</h3>
        </CardHeader>
        <CardBody>
          <div className="space-y-4">
            <div className="text-sm text-gray-600 mb-4">
              Select the accrual process to execute.
            </div>
            <RadioGroup
              value={accrualStartingPoint}
              onValueChange={setAccrualStartingPoint}
              className="space-y-3"
            >
              {availableSteps.accrual_steps.map((step) => (
                <div
                  key={step.id}
                  className="flex items-start space-x-3 p-3 border rounded-lg"
                >
                  <Radio value={step.id} />
                  <div className="flex-1">
                    <div className="font-medium">{step.name}</div>
                    <div className="text-sm text-gray-600">
                      {step.description}
                    </div>
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
                        <Icon icon="lucide:play" />
                      )
                    }
                  >
                    Run
                  </Button>
                </div>
              ))}
            </RadioGroup>
          </div>

          <div className="flex justify-end mt-4">
            <Button
              color="primary"
              size="lg"
              onPress={() => executeProcess("accrual")}
              isDisabled={isLoading}
              startContent={
                isLoading ? <Spinner size="sm" /> : <Icon icon="lucide:play" />
              }
            >
              Execute Accrual Process
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Results */}
      {results && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-medium">Execution Results</h3>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {results.total_stats?.total_processed || 0}
                  </div>
                  <div className="text-sm text-blue-800">Processed</div>
                </div>
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {results.total_stats?.total_created || 0}
                  </div>
                  <div className="text-sm text-green-800">Created</div>
                </div>
                <div className="text-center p-3 bg-yellow-50 rounded-lg">
                  <div className="text-2xl font-bold text-yellow-600">
                    {results.total_stats?.total_updated || 0}
                  </div>
                  <div className="text-sm text-yellow-800">Updated</div>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">
                    {results.total_stats?.total_errors || 0}
                  </div>
                  <div className="text-sm text-red-800">Errors</div>
                </div>
              </div>

              {results.step_results && results.step_results.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Step Details</h4>
                  <div className="space-y-2">
                    {results.step_results.map((stepResult, index) => (
                      <div key={index} className="p-3 border rounded-lg">
                        <div className="font-medium">{stepResult.step}</div>
                        <div className="text-sm text-gray-600">
                          {stepResult.step === "invoices" &&
                          stepResult.stats?.total_received != null ? (
                            <>
                              Received: {stepResult.stats.total_received} |
                            </>
                          ) : null}
                          Processed: {stepResult.stats?.total_processed || 0} |
                          Created: {stepResult.stats?.total_created || 0} |
                          Updated: {stepResult.stats?.total_updated || 0} |
                          Errors: {stepResult.stats?.total_errors || 0}
                        </div>
                        {stepResult.stats?.error && (
                          <div className="text-sm text-red-600 mt-1">
                            Error: {stepResult.stats.error}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
};

export default SyncManagement;
