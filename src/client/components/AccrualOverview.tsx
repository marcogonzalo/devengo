import React from 'react';
import { Card, CardBody, CardHeader } from "@heroui/react";
import { Icon } from '@iconify/react';

const AccrualOverview: React.FC = () => {
  // Placeholder data - replace with actual data fetching logic
  const overviewData = {
    totalContracts: 150,
    totalAmount: 1500000,
    accruedAmount: 750000,
    pendingAmount: 750000,
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Accrual Overview</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex gap-3">
            <Icon icon="lucide:file-text" className="text-primary text-xl" />
            <p className="text-md">Total Contracts</p>
          </CardHeader>
          <CardBody>
            <p className="text-2xl font-bold">{overviewData.totalContracts}</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader className="flex gap-3">
            <Icon icon="lucide:dollar-sign" className="text-primary text-xl" />
            <p className="text-md">Total Amount</p>
          </CardHeader>
          <CardBody>
            <p className="text-2xl font-bold">${overviewData.totalAmount.toLocaleString()}</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader className="flex gap-3">
            <Icon icon="lucide:check-circle" className="text-primary text-xl" />
            <p className="text-md">Accrued Amount</p>
          </CardHeader>
          <CardBody>
            <p className="text-2xl font-bold">${overviewData.accruedAmount.toLocaleString()}</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader className="flex gap-3">
            <Icon icon="lucide:clock" className="text-primary text-xl" />
            <p className="text-md">Pending Amount</p>
          </CardHeader>
          <CardBody>
            <p className="text-2xl font-bold">${overviewData.pendingAmount.toLocaleString()}</p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
};

export default AccrualOverview;