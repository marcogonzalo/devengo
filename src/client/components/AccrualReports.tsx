import React, { useState, useEffect } from 'react';
import { Card, CardBody, CardHeader, Select, SelectItem, Button, Spinner } from "@heroui/react";
import { Icon } from '@iconify/react';
import { accrualReportsApi, MonthlyAccrualData, YearlyAccrualSummary } from '../utils/api';

const AccrualReports: React.FC = () => {
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState<string>('');
  const [monthlyData, setMonthlyData] = useState<MonthlyAccrualData[]>([]);
  const [totalYearAmount, setTotalYearAmount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatCurrency = (amount: number): string => {
    return amount.toLocaleString("de-DE", { style: "currency", currency: "EUR" });
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
      setError('Failed to fetch available years');
      console.error('Error fetching available years:', err);
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
      setError('Failed to fetch monthly data');
      console.error('Error fetching monthly data:', err);
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
      console.error('Error downloading CSV:', err);
      setError('Failed to download CSV file');
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
        <Spinner size="lg" />
      </div>
    );
  }

  if (error && !monthlyData.length) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Accrual Reports</h1>
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

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Accrual Reports</h1>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center w-full">
            <h2 className="text-lg font-semibold">Yearly Accrual Report</h2>
            <div className="flex gap-3 items-center">
              <Select
                label="Select Year"
                selectedKeys={selectedYear ? [selectedYear] : []}
                onChange={handleYearChange}
                className="max-w-xs"
                isDisabled={loading}
              >
                                 {availableYears.map((year) => (
                   <SelectItem key={year.toString()}>
                     {year.toString()}
                   </SelectItem>
                 ))}
              </Select>
              <Button
                color="primary"
                variant="flat"
                onPress={handleDownloadCSV}
                isLoading={downloading}
                isDisabled={!selectedYear}
                startContent={!downloading && <Icon icon="lucide:download" />}
              >
                {downloading ? 'Downloading...' : 'Download CSV'}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardBody>
          {error && (
            <div className="mb-4 p-3 bg-danger-50 border border-danger-200 rounded-lg">
              <div className="flex items-center gap-2 text-danger">
                <Icon icon="lucide:alert-circle" className="text-lg" />
                <p className="text-sm">{error}</p>
              </div>
            </div>
          )}
          
          <div className="space-y-4">
            {/* Year Summary */}
            <div className="bg-primary-50 dark:bg-primary-900/20 p-4 rounded-lg">
              <div className="flex justify-between items-center">
                <span className="text-lg font-semibold">Total for {selectedYear}:</span>
                <span className="text-xl font-bold text-primary">{formatCurrency(totalYearAmount)}</span>
              </div>
            </div>

            {/* Monthly Data */}
            <div className="space-y-2">
              {loading ? (
                <div className="flex justify-center py-8">
                  <Spinner size="md" />
                </div>
              ) : (
                monthlyData.map((data) => (
                  <div key={data.month} className="flex justify-between items-center p-3 bg-content2 rounded-lg">
                    <div className="flex items-center gap-3">
                      <Icon 
                        icon="lucide:calendar" 
                        className="text-primary text-lg" 
                      />
                      <span className="font-medium">{data.month}</span>
                    </div>
                    <span className={`font-semibold ${data.amount > 0 ? 'text-success' : 'text-default-500'}`}>
                      {formatCurrency(data.amount)}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};

export default AccrualReports;