import React, { useState, useEffect } from 'react';
import { Card, CardBody, CardHeader, Spinner, Button } from "@heroui/react";
import { Icon } from '@iconify/react';
import { dashboardApi, DashboardSummary } from '../utils/api';

const AccrualOverview: React.FC = () => {
  const [overviewData, setOverviewData] = useState<DashboardSummary | null>(null);
  const [currentYearData, setCurrentYearData] = useState<DashboardSummary | null>(null);
  const [lastYearData, setLastYearData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const formatCurrency = (amount: number): string => {
    return amount.toLocaleString("de-DE", { style: "currency", currency: "EUR" });
  };

  const fetchDashboardSummaries = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch all three summaries in parallel
      const [totalResponse, currentYearResponse, lastYearResponse] = await Promise.all([
        dashboardApi.getSummary(), // No year parameter = all data
        dashboardApi.getSummaryCurrentYear(),
        dashboardApi.getSummaryLastYear()
      ]);
      
      // Handle errors from any of the requests
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
      
      // Set the data
      if (totalResponse.data) {
        setOverviewData(totalResponse.data);
      }
      if (currentYearResponse.data) {
        setCurrentYearData(currentYearResponse.data);
      }
      if (lastYearResponse.data) {
        setLastYearData(lastYearResponse.data);
      }
    } catch (err) {
      setError('Failed to fetch dashboard summaries');
      console.error('Error fetching dashboard summaries:', err);
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
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Accrual Overview</h1>
        <Card className="border-danger">
          <CardBody>
            <div className="flex items-center gap-2 text-danger">
              <Icon icon="lucide:alert-circle" className="text-xl" />
              <p>Error: {error}</p>
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  if (!overviewData || !currentYearData || !lastYearData) {
    return null;
  }

  const currentYear = new Date().getFullYear();

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Accrual Overview</h1>
        <Button 
          color="primary" 
          variant="flat" 
          onPress={fetchDashboardSummaries}
          isLoading={loading}
          startContent={!loading && <Icon icon="lucide:refresh-cw" />}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>
      
      {/* Total Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-foreground-700">Total</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:file-text" className="text-primary text-xl" />
              <p className="text-md">Total Contracts</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{overviewData.total_contracts}</p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:dollar-sign" className="text-primary text-xl" />
              <p className="text-md">Total Contract Amount</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{formatCurrency(overviewData.total_amount)}</p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:check-circle" className="text-warning text-xl" />
              <p className="text-md">Total Accrued Amount</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{formatCurrency(overviewData.accrued_amount)}</p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:clock" className="text-warning text-xl" />
              <p className="text-md">Total Pending Amount</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{formatCurrency(overviewData.pending_amount)}</p>
            </CardBody>
          </Card>
        </div>
      </div>

      {/* Current Year Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-foreground-700">{currentYear} (Current Year)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:file-text" className="text-primary text-xl" />
              <p className="text-md">Contracts</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{currentYearData.total_contracts}</p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:dollar-sign" className="text-primary text-xl" />
              <p className="text-md">Contract Amount</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{formatCurrency(currentYearData.total_amount)}</p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:check-circle" className="text-warning text-xl" />
              <p className="text-md">Accrued Amount</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{formatCurrency(currentYearData.accrued_amount)}</p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:clock" className="text-warning text-xl" />
              <p className="text-md">Pending Amount</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{formatCurrency(currentYearData.pending_amount)}</p>
            </CardBody>
          </Card>
        </div>
      </div>

      {/* Last Year Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-foreground-700">{currentYear - 1} (Last Year)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:file-text" className="text-primary text-xl" />
              <p className="text-md">Contracts</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{lastYearData.total_contracts}</p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:dollar-sign" className="text-primary text-xl" />
              <p className="text-md">Contract Amount</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{formatCurrency(lastYearData.total_amount)}</p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:check-circle" className="text-warning text-xl" />
              <p className="text-md">Accrued Amount</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{formatCurrency(lastYearData.accrued_amount)}</p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader className="flex gap-3">
              <Icon icon="lucide:clock" className="text-warning text-xl" />
              <p className="text-md">Pending Amount</p>
            </CardHeader>
            <CardBody>
              <p className="text-2xl font-bold">{formatCurrency(lastYearData.pending_amount)}</p>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AccrualOverview;