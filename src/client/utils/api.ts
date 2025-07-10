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

// Dashboard API functions
export const dashboardApi = {
  // Get dashboard summary statistics
  getSummary: async (): Promise<ApiResponse<DashboardSummary>> => {
    return apiClient.get<DashboardSummary>('/accruals/dashboard-summary');
  },
}; 