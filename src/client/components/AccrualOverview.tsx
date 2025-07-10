import React, { useState, useEffect } from 'react';
import { Card, CardBody, CardHeader, Spinner, Button } from "@heroui/react";
import { Icon } from '@iconify/react';
import { dashboardApi, DashboardSummary } from '../utils/api';

const AccrualOverview: React.FC = () => {
  const [overviewData, setOverviewData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const formatCurrency = (amount: number): string => {
    return amount.toLocaleString("de-DE", { style: "currency", currency: "EUR" });
  };

  const fetchDashboardSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await dashboardApi.getSummary();
      
      if (response.error) {
        setError(response.error);
      } else if (response.data) {
        setOverviewData(response.data);
      }
    } catch (err) {
      setError('Failed to fetch dashboard summary');
      console.error('Error fetching dashboard summary:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardSummary();
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

  if (!overviewData) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Accrual Overview</h1>
        <Button 
          color="primary" 
          variant="flat" 
          onPress={fetchDashboardSummary}
          isLoading={loading}
          startContent={!loading && <Icon icon="lucide:refresh-cw" />}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>
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
            <p className="text-md">Total Amount</p>
          </CardHeader>
          <CardBody>
            <p className="text-2xl font-bold">{formatCurrency(overviewData.total_amount)}</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader className="flex gap-3">
            <Icon icon="lucide:check-circle" className="text-primary text-xl" />
            <p className="text-md">Accrued Amount</p>
          </CardHeader>
          <CardBody>
            <p className="text-2xl font-bold">{formatCurrency(overviewData.accrued_amount)}</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader className="flex gap-3">
            <Icon icon="lucide:clock" className="text-primary text-xl" />
            <p className="text-md">Pending Amount</p>
          </CardHeader>
          <CardBody>
            <p className="text-2xl font-bold">{formatCurrency(overviewData.pending_amount)}</p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
};

export default AccrualOverview;