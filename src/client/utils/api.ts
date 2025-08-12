// API client configuration and utility functions
const API_BASE_URL = process.env.NODE_ENV === 'production' ? process.env.VITE_API_URL : 'http://localhost:3001/api';

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      console.error('API request error:', error);
      return { error: error instanceof Error ? error.message : 'An unknown error occurred' };
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();

// Client-specific API functions
export interface ClientRead {
  id: number;
  name: string;
  identifier: string; // email
  created_at: string;
  updated_at: string;
}

export interface ClientExternalId {
  id: number;
  client_id: number;
  system: string;
  external_id: string;
}

export interface ClientMissingExternalId {
  id: number;
  name: string;
  identifier: string; // email
  system: string;
}

export interface ClientExternalIdCreate {
  system: string;
  external_id: string;
}

export interface ClientUpdate {
  name?: string;
  identifier?: string; // email
}

export const clientApi = {
  // Get all clients
  getClients: async (): Promise<ApiResponse<ClientRead[]>> => {
    return apiClient.get<ClientRead[]>('/clients');
  },

  // Get clients with missing external IDs
  getClientsMissingExternalIds: async (): Promise<ApiResponse<ClientMissingExternalId[]>> => {
    return apiClient.get<ClientMissingExternalId[]>('/clients/missing-external-ids');
  },

  // Add external ID to a client
  addExternalId: async (clientId: number, externalIdData: ClientExternalIdCreate): Promise<ApiResponse<ClientExternalId>> => {
    return apiClient.post<ClientExternalId>(`/clients/${clientId}/external-ids`, externalIdData);
  },

  // Get client by ID
  getClient: async (clientId: number): Promise<ApiResponse<ClientRead>> => {
    return apiClient.get<ClientRead>(`/clients/${clientId}`);
  },

  // Update client
  updateClient: async (clientId: number, updateData: ClientUpdate): Promise<ApiResponse<ClientRead>> => {
    return apiClient.put<ClientRead>(`/clients/${clientId}`, updateData);
  },
};

// Dashboard summary types
export interface DashboardSummary {
  total_contracts: number;
  total_amount: number;
  accrued_amount: number;
  pending_amount: number;
}

// Monthly accrual data types
export interface MonthlyAccrualData {
  month: string;
  month_number: number;
  amount: number;
}

export interface YearlyAccrualSummary {
  year: number;
  monthly_data: MonthlyAccrualData[];
  total_year_amount: number;
}

export interface AvailableYears {
  years: number[];
}

// Dashboard API functions
export const dashboardApi = {
  // Get dashboard summary statistics
  getSummary: async (year?: number): Promise<ApiResponse<DashboardSummary>> => {
    const queryParam = year ? `?year=${year}` : '';
    return apiClient.get<DashboardSummary>(`/accruals/dashboard-summary${queryParam}`);
  },

  // Get current year dashboard summary statistics
  getSummaryCurrentYear: async (): Promise<ApiResponse<DashboardSummary>> => {
    const currentYear = new Date().getFullYear();
    return dashboardApi.getSummary(currentYear);
  },

  // Get last year dashboard summary statistics
  getSummaryLastYear: async (): Promise<ApiResponse<DashboardSummary>> => {
    const lastYear = new Date().getFullYear() - 1;
    return dashboardApi.getSummary(lastYear);
  },
};

// Accrual Reports API functions
export const accrualReportsApi = {
  // Get available years for reports
  getAvailableYears: async (): Promise<ApiResponse<AvailableYears>> => {
    return apiClient.get<AvailableYears>('/accruals/available-years');
  },

  // Get monthly accrual data for a specific year
  getMonthlyAccruals: async (year: number): Promise<ApiResponse<YearlyAccrualSummary>> => {
    return apiClient.get<YearlyAccrualSummary>(`/accruals/monthly-accruals/${year}`);
  },

  // Download CSV for a specific year
  downloadYearCSV: async (year: number): Promise<void> => {
    try {
      const startDate = `${year}-01-01`;
      const endDate = `${year}-12-31`;
      
      const response = await fetch(`${API_BASE_URL}/accruals/export/csv?start_date=${startDate}&end_date=${endDate}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Create a blob from the response
      const blob = await response.blob();
      
      // Create a download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `accruals_${year}.csv`;
      
      // Trigger download
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading CSV:', error);
      throw error;
    }
  },
};

// Integration Errors API types and functions
export interface IntegrationErrorRead {
  id: number;
  integration_name: string;
  operation_type: string;
  external_id: string;
  entity_type: string;
  error_message: string;
  error_details: Record<string, any>;
  client_id?: number;
  contract_id?: number;
  is_resolved: boolean;
  is_ignored: boolean;
  resolved_at?: string;
  resolution_notes?: string;
  ignored_at?: string;
  ignore_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface IntegrationErrorFilter {
  integration_name?: string;
  operation_type?: string;
  entity_type?: string;
  is_resolved?: boolean;
  is_ignored?: boolean;
  client_id?: number;
  contract_id?: number;
  limit?: number;
  offset?: number;
}

export interface IntegrationErrorSummary {
  total_errors: number;
  resolved_errors: number;
  unresolved_errors: number;
  ignored_errors: number;
  errors_by_integration: Record<string, number>;
  errors_by_operation: Record<string, number>;
  errors_by_entity_type: Record<string, number>;
}

export const integrationErrorsApi = {
  // Get integration errors with filtering and pagination
  getErrors: async (filters: IntegrationErrorFilter): Promise<ApiResponse<IntegrationErrorRead[]>> => {
    const queryParams = new URLSearchParams();
    if (filters.integration_name) queryParams.append('integration_name', filters.integration_name);
    if (filters.operation_type) queryParams.append('operation_type', filters.operation_type);
    if (filters.entity_type) queryParams.append('entity_type', filters.entity_type);
    if (filters.is_resolved !== null && filters.is_resolved !== undefined) queryParams.append('is_resolved', filters.is_resolved.toString());
    if (filters.is_ignored !== null && filters.is_ignored !== undefined) queryParams.append('is_ignored', filters.is_ignored.toString());
    if (filters.client_id) queryParams.append('client_id', filters.client_id.toString());
    if (filters.contract_id) queryParams.append('contract_id', filters.contract_id.toString());
    if (filters.limit) queryParams.append('limit', filters.limit.toString());
    if (filters.offset) queryParams.append('offset', filters.offset.toString());
    
    return apiClient.get<IntegrationErrorRead[]>(`/integrations/errors/?${queryParams.toString()}`);
  },

  // Get integration errors with count for pagination
  getErrorsWithCount: async (filters: IntegrationErrorFilter): Promise<ApiResponse<{errors: IntegrationErrorRead[], total: number}>> => {
    const queryParams = new URLSearchParams();
    if (filters.integration_name) queryParams.append('integration_name', filters.integration_name);
    if (filters.operation_type) queryParams.append('operation_type', filters.operation_type);
    if (filters.entity_type) queryParams.append('entity_type', filters.entity_type);
    if (filters.is_resolved !== null && filters.is_resolved !== undefined) queryParams.append('is_resolved', filters.is_resolved.toString());
    if (filters.is_ignored !== null && filters.is_ignored !== undefined) queryParams.append('is_ignored', filters.is_ignored.toString());
    if (filters.client_id) queryParams.append('client_id', filters.client_id.toString());
    if (filters.contract_id) queryParams.append('contract_id', filters.contract_id.toString());
    if (filters.limit) queryParams.append('limit', filters.limit.toString());
    if (filters.offset) queryParams.append('offset', filters.offset.toString());
    
    return apiClient.get<{errors: IntegrationErrorRead[], total: number}>(`/integrations/errors/list?${queryParams.toString()}`);
  },

  // Get integration errors summary
  getSummary: async (): Promise<ApiResponse<IntegrationErrorSummary>> => {
    return apiClient.get<IntegrationErrorSummary>('/integrations/errors/summary');
  },

  // Get a specific integration error
  getError: async (errorId: number): Promise<ApiResponse<IntegrationErrorRead>> => {
    return apiClient.get<IntegrationErrorRead>(`/integrations/errors/${errorId}`);
  },

  // Create a new integration error
  createError: async (errorData: Omit<IntegrationErrorRead, 'id' | 'created_at' | 'updated_at'>): Promise<ApiResponse<IntegrationErrorRead>> => {
    return apiClient.post<IntegrationErrorRead>('/integrations/errors', errorData);
  },

  // Update an integration error
  updateError: async (errorId: number, updateData: Partial<IntegrationErrorRead>): Promise<ApiResponse<IntegrationErrorRead>> => {
    return apiClient.put<IntegrationErrorRead>(`/integrations/errors/${errorId}`, updateData);
  },

  // Delete an integration error
  deleteError: async (errorId: number): Promise<ApiResponse<{ message: string }>> => {
    return apiClient.delete<{ message: string }>(`/integrations/errors/${errorId}`);
  },

  // Resolve an integration error
  resolveError: async (errorId: number, resolutionNotes?: string): Promise<ApiResponse<IntegrationErrorRead>> => {
    const params = resolutionNotes ? `?resolution_notes=${encodeURIComponent(resolutionNotes)}` : '';
    return apiClient.post<IntegrationErrorRead>(`/integrations/errors/${errorId}/resolve${params}`);
  },

  // Bulk resolve integration errors
  bulkResolveErrors: async (errorIds: number[], resolutionNotes?: string): Promise<ApiResponse<{ message: string; resolved_count: number; total_requested: number }>> => {
    return apiClient.post<{ message: string; resolved_count: number; total_requested: number }>('/integrations/errors/bulk-resolve', {
      error_ids: errorIds,
      resolution_notes: resolutionNotes
    });
  },

  // Ignore an integration error
  ignoreError: async (errorId: number, ignoreNotes?: string): Promise<ApiResponse<IntegrationErrorRead>> => {
    const queryParams = new URLSearchParams();
    if (ignoreNotes) queryParams.append('ignore_notes', ignoreNotes);
    return apiClient.post<IntegrationErrorRead>(`/integrations/errors/${errorId}/ignore?${queryParams.toString()}`);
  },

  // Bulk ignore integration errors
  bulkIgnoreErrors: async (errorIds: number[], ignoreNotes?: string): Promise<ApiResponse<{ message: string; ignored_count: number; total_requested: number }>> => {
    return apiClient.post<{ message: string; ignored_count: number; total_requested: number }>('/integrations/errors/bulk-ignore', {
      error_ids: errorIds,
      ignore_notes: ignoreNotes
    });
  },
}; 