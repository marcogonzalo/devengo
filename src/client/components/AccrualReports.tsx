import React from 'react';
import { Card, CardBody, CardHeader, Select, SelectItem } from "@heroui/react";
import { Icon } from '@iconify/react';

const AccrualReports: React.FC = () => {
  const [selectedYear, setSelectedYear] = React.useState('2023');

  const formatCurrency = (amount: number): string => {
    return amount
      .toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      .replace(/,/g, '.')
      .replace(/\.([^.]*)$/, ',$1') + ' €';
  };

  // Placeholder data - replace with actual data fetching logic
  const years = ['2023', '2022', '2021', '2020'];
  const monthlyData = [
    { month: 'Jan', amount: 50000 },
    { month: 'Feb', amount: 60000 },
    { month: 'Mar', amount: 75000 },
    // Add more months as needed
  ];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Accrual Reports</h1>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Yearly Accrual Report</h2>
            <Select
              label="Select Year"
              selectedKeys={[selectedYear]}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="max-w-xs"
            >
              {years.map((year) => (
                <SelectItem key={year}>
                  {year}
                </SelectItem>
              ))}
            </Select>
          </div>
        </CardHeader>
        <CardBody>
          <div className="space-y-2">
            {monthlyData.map((data) => (
              <div key={data.month} className="flex justify-between items-center">
                <span>{data.month}</span>
                <span className="font-semibold">{formatCurrency(data.amount)}</span>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>
    </div>
  );
};

export default AccrualReports;