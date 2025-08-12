import React, { useState, useEffect } from 'react';
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button,
  Chip,
  Spinner,
  Card,
  CardBody,
  CardHeader,
  Input,
  Pagination,
  Checkbox,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Textarea,
  Tooltip,
  useDisclosure
} from '@heroui/react';
import { integrationErrorsApi, IntegrationErrorRead, IntegrationErrorSummary } from '../utils/api';
import { Icon } from '@iconify/react';

interface PaginationState {
  page: number;
  limit: number;
  total: number;
}

interface FilterState {
  integration_name: string;
  operation_type: string;
  entity_type: string;
  is_resolved: boolean | null;
  is_ignored: boolean | null;
}

interface FilterOptions {
  integrations: string[];
  operations: string[];
  entityTypes: string[];
}

const IntegrationErrors: React.FC = () => {
  const [errors, setErrors] = useState<IntegrationErrorRead[]>([]);
  const [summary, setSummary] = useState<IntegrationErrorSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedErrors, setSelectedErrors] = useState<Set<number>>(new Set());
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    integrations: [],
    operations: [],
    entityTypes: []
  });
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    limit: 10,
    total: 0
  });
  const [filters, setFilters] = useState<FilterState>({
    integration_name: '',
    operation_type: '',
    entity_type: '',
    is_resolved: null,
    is_ignored: null
  });

  const { isOpen: isResolveModalOpen, onOpen: onResolveModalOpen, onClose: onResolveModalClose } = useDisclosure();
  const [resolveNotes, setResolveNotes] = useState('');
  const [isResolving, setIsResolving] = useState(false);

  // Extract filter options from summary data
  const extractFilterOptions = (summaryData: IntegrationErrorSummary) => {
    const integrations = Object.keys(summaryData.errors_by_integration);
    const operations = Object.keys(summaryData.errors_by_operation);
    const entityTypes = Object.keys(summaryData.errors_by_entity_type);
    
    setFilterOptions({
      integrations: integrations.sort(),
      operations: operations.sort(),
      entityTypes: entityTypes.sort()
    });
  };

  // Fetch errors and summary
  const fetchData = async () => {
    try {
      setLoading(true);
      const [errorsResponse, summaryResponse] = await Promise.all([
        integrationErrorsApi.getErrorsWithCount({
          ...filters,
          limit: pagination.limit,
          offset: (pagination.page - 1) * pagination.limit,
        }),
        integrationErrorsApi.getSummary()
      ]);

      if (errorsResponse.data) {
        setErrors(errorsResponse.data.errors);
        setPagination(prev => ({ ...prev, total: errorsResponse.data.total }));
      }

      if (summaryResponse.data) {
        setSummary(summaryResponse.data);
        extractFilterOptions(summaryResponse.data);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filters, pagination.page, pagination.limit]);

  // Handle filter changes
  const handleFilterChange = (key: keyof FilterState, value: string | boolean | null) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 })); // Reset to first page
  };

  // Handle pagination
  const handlePageChange = (page: number) => {
    setPagination(prev => ({ ...prev, page }));
  };

  // Handle selection
  const handleSelectionChange = (keys: Set<number>) => {
    setSelectedErrors(keys);
  };

  // Get unique values for filter options
  const getUniqueValues = (field: keyof IntegrationErrorRead): string[] => {
    const values = errors.map(error => error[field]);
    return Array.from(new Set(values.filter(v => v !== null && v !== undefined))).map(String);
  };

  // Handle resolve
  const handleResolve = async (errorIds: number[], notes?: string) => {
    try {
      setIsResolving(true);
      const response = await integrationErrorsApi.bulkResolveErrors(errorIds, notes);
      if (response.data) {
        setSelectedErrors(new Set());
        setResolveNotes('');
        onResolveModalClose();
        fetchData(); // Refresh data
      }
    } catch (error) {
      console.error('Error resolving errors:', error);
    } finally {
      setIsResolving(false);
    }
  };

  // Handle ignore
  const handleIgnore = async (errorIds: number[]) => {
    if (window.confirm('Are you sure you want to ignore these errors?')) {
      try {
        const response = await integrationErrorsApi.bulkIgnoreErrors(errorIds);
        if (response.data) {
          setSelectedErrors(new Set());
          fetchData(); // Refresh data
        }
      } catch (error) {
        console.error('Error ignoring errors:', error);
      }
    }
  };

  // Handle delete
  const handleDelete = async (errorId: number) => {
    if (window.confirm('Are you sure you want to delete this error?')) {
      try {
        const response = await integrationErrorsApi.deleteError(errorId);
        if (response.data) {
          fetchData(); // Refresh data
        }
      } catch (error) {
        console.error('Error deleting error:', error);
      }
    }
  };

  // Handle bulk resolve
  const handleBulkResolve = () => {
    if (selectedErrors.size > 0) {
      onResolveModalOpen();
    }
  };

  // Handle bulk ignore
  const handleBulkIgnore = async () => {
    if (selectedErrors.size > 0 && window.confirm(`Are you sure you want to ignore ${selectedErrors.size} selected error(s)?`)) {
      try {
        const response = await integrationErrorsApi.bulkIgnoreErrors(Array.from(selectedErrors));
        if (response.data) {
          setSelectedErrors(new Set());
          fetchData(); // Refresh data
        }
      } catch (error) {
        console.error('Error ignoring errors:', error);
      }
    }
  };

  // Handle bulk delete
  const handleBulkDelete = async () => {
    if (selectedErrors.size > 0 && window.confirm(`Are you sure you want to delete ${selectedErrors.size} errors?`)) {
      try {
        // Delete each error individually
        const deletePromises = Array.from(selectedErrors).map(errorId => 
          integrationErrorsApi.deleteError(errorId)
        );
        await Promise.all(deletePromises);
        setSelectedErrors(new Set());
        fetchData(); // Refresh data
      } catch (error) {
        console.error('Error deleting errors:', error);
      }
    }
  };

  const columns = [
    { key: 'integration_name', label: 'Integration' },
    { key: 'operation_type', label: 'Operation' },
    { key: 'entity_type', label: 'Entity Type' },
    { key: 'external_id', label: 'External ID' },
    { key: 'error_message', label: 'Error Message' },
    { key: 'status', label: 'Status' },
    { key: 'created_at', label: 'Created At' },
    { key: 'actions', label: 'Actions' }
  ];

  const renderCell = (error: IntegrationErrorRead, columnKey: string) => {
    switch (columnKey) {
      case 'integration_name':
        return (
          <div className="flex flex-col">
            <p className="text-bold text-small capitalize">{error.integration_name}</p>
          </div>
        );
      case 'operation_type':
        return (
          <div className="flex flex-col">
            <p className="text-bold text-small capitalize">{error.operation_type}</p>
          </div>
        );
      case 'entity_type':
        return (
          <div className="flex flex-col">
            <p className="text-bold text-small capitalize">{error.entity_type}</p>
          </div>
        );
      case 'external_id':
        return (
          <div className="flex flex-col">
            <p className="text-bold text-small">{error.external_id}</p>
          </div>
        );
      case 'error_message':
        return (
          <div className="flex flex-col">
            <p className="text-bold text-small">{error.error_message}</p>
          </div>
        );
      case 'status':
        if (error.is_ignored) {
          return (
            <Chip
              color="warning"
              variant="flat"
              size="sm"
            >
              Ignored
            </Chip>
          );
        }
        return (
          <Chip
            color={error.is_resolved ? 'success' : 'danger'}
            variant="flat"
            size="sm"
          >
            {error.is_resolved ? 'Resolved' : 'Unresolved'}
          </Chip>
        );
      case 'created_at':
        return new Date(error.created_at).toLocaleDateString();
      case 'actions':
        return (
          <div className="flex gap-2">
            {!error.is_resolved && !error.is_ignored && (
              <Tooltip content="Resolve">
                <Button
                  isIconOnly
                  size="sm"
                  variant="flat"
                  color="success"
                  onPress={() => handleResolve([error.id])}
                >
                  <Icon icon="mdi:check" />
                </Button>
              </Tooltip>
            )}
            {!error.is_resolved && !error.is_ignored && (
              <Tooltip content="Ignore">
                <Button
                  isIconOnly
                  size="sm"
                  variant="flat"
                  color="warning"
                  onPress={() => handleIgnore([error.id])}
                >
                  <Icon icon="mdi:eye-off" />
                </Button>
              </Tooltip>
            )}
            <Tooltip content="Delete">
              <Button
                isIconOnly
                size="sm"
                variant="flat"
                color="danger"
                onPress={() => handleDelete(error.id)}
              >
                <Icon icon="mdi:delete" />
              </Button>
            </Tooltip>
          </div>
        );
      default:
        const value = error[columnKey as keyof IntegrationErrorRead];
        if (value === null || value === undefined) return '';
        return String(value);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Integration Errors</h1>
        <div className="flex gap-2">
          {selectedErrors.size > 0 && (
            <>
              <Button
                color="success"
                variant="flat"
                onPress={handleBulkResolve}
                startContent={<Icon icon="mdi:check" />}
              >
                Resolve Selected ({selectedErrors.size})
              </Button>
              <Button
                color="warning"
                variant="flat"
                onPress={handleBulkIgnore}
                startContent={<Icon icon="mdi:eye-off" />}
              >
                Ignore Selected ({selectedErrors.size})
              </Button>
              <Button
                color="danger"
                variant="flat"
                onPress={handleBulkDelete}
                startContent={<Icon icon="mdi:delete" />}
              >
                Delete Selected ({selectedErrors.size})
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <Card>
            <CardBody>
              <div className="text-center">
                <p className="text-sm text-gray-500">Total Errors</p>
                <p className="text-2xl font-bold">{summary.total_errors}</p>
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <div className="text-center">
                <p className="text-sm text-gray-500">Resolved</p>
                <p className="text-2xl font-bold text-green-600">{summary.resolved_errors}</p>
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <div className="text-center">
                <p className="text-sm text-gray-500">Unresolved</p>
                <p className="text-2xl font-bold text-red-600">{summary.unresolved_errors}</p>
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <div className="text-center">
                <p className="text-sm text-gray-500">Ignored</p>
                <p className="text-2xl font-bold text-yellow-600">{summary.ignored_errors}</p>
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <div className="text-center">
                <p className="text-sm text-gray-500">Integrations</p>
                <p className="text-2xl font-bold">{Object.keys(summary.errors_by_integration).length}</p>
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">Filters</h3>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Integration</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={filters.integration_name}
                onChange={(e) => handleFilterChange('integration_name', e.target.value)}
              >
                <option value="">All Integrations</option>
                {filterOptions.integrations.map(integration => (
                  <option key={integration} value={integration}>{integration}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Operation</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={filters.operation_type}
                onChange={(e) => handleFilterChange('operation_type', e.target.value)}
              >
                <option value="">All Operations</option>
                {filterOptions.operations.map(operation => (
                  <option key={operation} value={operation}>{operation}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Entity Type</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={filters.entity_type}
                onChange={(e) => handleFilterChange('entity_type', e.target.value)}
              >
                <option value="">All Entity Types</option>
                {filterOptions.entityTypes.map(entityType => (
                  <option key={entityType} value={entityType}>{entityType}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Status</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={filters.is_resolved === null && filters.is_ignored === null ? '' : 
                       filters.is_resolved === true ? 'resolved' : 
                       filters.is_ignored === true ? 'ignored' : 'unresolved'}
                onChange={(e) => {
                  if (e.target.value === '') {
                    handleFilterChange('is_resolved', null);
                    handleFilterChange('is_ignored', null);
                  } else if (e.target.value === 'resolved') {
                    handleFilterChange('is_resolved', true);
                    handleFilterChange('is_ignored', false);
                  } else if (e.target.value === 'ignored') {
                    handleFilterChange('is_resolved', false);
                    handleFilterChange('is_ignored', true);
                  } else {
                    handleFilterChange('is_resolved', false);
                    handleFilterChange('is_ignored', false);
                  }
                }}
              >
                <option value="">All Statuses</option>
                <option value="unresolved">Unresolved</option>
                <option value="resolved">Resolved</option>
                <option value="ignored">Ignored</option>
              </select>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Errors Table */}
      <Card>
        <CardBody>
          <Table
            aria-label="Integration errors table"
            selectionMode="multiple"
            selectedKeys={selectedErrors}
            onSelectionChange={handleSelectionChange}
          >
            <TableHeader columns={columns}>
              {(column) => (
                <TableColumn key={column.key}>
                  {column.label}
                </TableColumn>
              )}
            </TableHeader>
            <TableBody items={errors}>
              {(error) => (
                <TableRow key={error.id}>
                  {(columnKey) => <TableCell>{renderCell(error, String(columnKey))}</TableCell>}
                </TableRow>
              )}
            </TableBody>
          </Table>

          {/* Pagination */}
          {pagination.total > pagination.limit && (
            <div className="flex justify-center mt-4">
              <Pagination
                total={Math.ceil(pagination.total / pagination.limit)}
                page={pagination.page}
                onChange={handlePageChange}
              />
            </div>
          )}
        </CardBody>
      </Card>

      {/* Resolve Modal */}
      <Modal isOpen={isResolveModalOpen} onClose={onResolveModalClose}>
        <ModalContent>
          <ModalHeader>Resolve Errors</ModalHeader>
          <ModalBody>
            <p>Are you sure you want to resolve {selectedErrors.size} selected error(s)?</p>
            <Textarea
              label="Resolution Notes (optional)"
              placeholder="Add notes about how the errors were resolved..."
              value={resolveNotes}
              onChange={(e) => setResolveNotes(e.target.value)}
            />
          </ModalBody>
          <ModalFooter>
            <Button variant="flat" onPress={onResolveModalClose}>
              Cancel
            </Button>
            <Button
              color="success"
              onPress={() => handleResolve(Array.from(selectedErrors), resolveNotes)}
              isLoading={isResolving}
            >
              Resolve
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </div>
  );
};

export default IntegrationErrors;
