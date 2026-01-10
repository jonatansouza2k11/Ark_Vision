// frontend/src/api/settingsApi.ts

/**
 * Settings API Client v4.1 - Advanced Features + YOLO Models
 */

import type {
    YOLOConfig,
    EmailConfig,
    AllSettings,
    ApiResponse,
    ExportData
} from '../types/settings.types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getAuthHeader = () => {
    const token = localStorage.getItem('access_token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };
};

// ============================================================================
// NEW v4.1: YOLO Models Types
// ============================================================================

export interface YOLOModel {
    filename: string;
    path: string;
    type: string;         // "YOLO v8", "YOLO v11"
    variant: string;      // "Nano (fastest)", "Small (balanced)", etc.
    size_mb: number;
}

export interface YOLOModelsResponse {
    models: YOLOModel[];
    current: string;      // Modelo atualmente em uso
    total: number;
    message?: string;
}

// ============================================================================
// Settings API
// ============================================================================

export const settingsApi = {
    // ========== Existing Methods ==========

    getAll: async (): Promise<ApiResponse<Record<string, any>>> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/settings`, {
                headers: getAuthHeader(),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            return { data };
        } catch (error) {
            console.error('❌ Settings fetch error:', error);
            return { error: error instanceof Error ? error.message : 'Failed to fetch settings' };
        }
    },

    getYoloConfig: async (): Promise<ApiResponse<YOLOConfig>> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/settings/yolo/config`, {
                headers: getAuthHeader(),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            return { data };
        } catch (error) {
            return { error: error instanceof Error ? error.message : 'Failed to fetch YOLO config' };
        }
    },

    getEmailConfig: async (): Promise<ApiResponse<EmailConfig>> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/settings/email/config`, {
                headers: getAuthHeader(),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            return { data };
        } catch (error) {
            return { error: error instanceof Error ? error.message : 'Failed to fetch email config' };
        }
    },

    updateMultiple: async (settings: Record<string, any>): Promise<ApiResponse<void>> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/settings`, {
                method: 'PUT',
                headers: getAuthHeader(),
                body: JSON.stringify({ settings }),
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            return { data: undefined };
        } catch (error) {
            return { error: error instanceof Error ? error.message : 'Failed to update settings' };
        }
    },

    updateYoloConfig: async (config: Partial<YOLOConfig>): Promise<ApiResponse<YOLOConfig>> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/settings/yolo/config`, {
                method: 'PUT',
                headers: getAuthHeader(),
                body: JSON.stringify(config),
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            const data = await response.json();
            return { data };
        } catch (error) {
            return { error: error instanceof Error ? error.message : 'Failed to update YOLO config' };
        }
    },

    updateEmailConfig: async (config: Partial<EmailConfig>): Promise<ApiResponse<EmailConfig>> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/settings/email/config`, {
                method: 'PUT',
                headers: getAuthHeader(),
                body: JSON.stringify(config),
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            const data = await response.json();
            return { data };
        } catch (error) {
            return { error: error instanceof Error ? error.message : 'Failed to update email config' };
        }
    },

    reset: async (): Promise<ApiResponse<void>> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/settings/reset`, {
                method: 'POST',
                headers: getAuthHeader(),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return { data: undefined };
        } catch (error) {
            return { error: error instanceof Error ? error.message : 'Failed to reset settings' };
        }
    },

    // ========== NEW v4.0: Compare (Diff) ==========

    compare: async (): Promise<ApiResponse<any>> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/settings/compare`, {
                headers: getAuthHeader(),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            return { data };
        } catch (error) {
            return { error: error instanceof Error ? error.message : 'Failed to compare settings' };
        }
    },

    // ========== NEW v4.0: Export ==========

    export: async (format: 'json' | 'yaml' = 'json', category?: string): Promise<ApiResponse<ExportData>> => {
        try {
            const params = new URLSearchParams({ format });
            if (category) params.append('category', category);

            const response = await fetch(`${API_BASE}/api/v1/settings/export?${params}`, {
                headers: getAuthHeader(),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            return { data };
        } catch (error) {
            return { error: error instanceof Error ? error.message : 'Failed to export settings' };
        }
    },

    // ========== NEW v4.0: Import ==========

    import: async (file: File, validateFirst: boolean = true): Promise<ApiResponse<any>> => {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const params = new URLSearchParams({ validate_first: validateFirst.toString() });

            const response = await fetch(`${API_BASE}/api/v1/settings/import?${params}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                },
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();
            return { data };
        } catch (error) {
            return { error: error instanceof Error ? error.message : 'Failed to import settings' };
        }
    },

    // ========== NEW v4.1: YOLO Available Models ==========

    getYoloModels: async (): Promise<YOLOModelsResponse> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/settings/available-models`, {
                headers: getAuthHeader(),
            });

            if (!response.ok) {
                console.error(`❌ HTTP Error: ${response.status} ${response.statusText}`);
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // ✅ Validação robusta da resposta
            if (!data || typeof data !== 'object') {
                console.error('❌ Resposta inválida da API:', data);
                return {
                    models: [],
                    current: '',
                    total: 0,
                    message: 'Resposta inválida do servidor'
                };
            }

            // ✅ Garante que models sempre seja um array
            const validModels = Array.isArray(data.models) ? data.models : [];

            console.log('✅ API response:', {
                modelsCount: validModels.length,
                current: data.current || 'none',
                total: data.total || 0
            });

            return {
                models: validModels,
                current: data.current || '',
                total: data.total || validModels.length,
                message: data.message
            };
        } catch (error) {
            console.error('❌ Failed to fetch YOLO models:', error);

            // ✅ Return fallback válido em caso de erro
            return {
                models: [],
                current: '',
                total: 0,
                message: error instanceof Error ? error.message : 'Failed to fetch models'
            };
        }
    },
};
