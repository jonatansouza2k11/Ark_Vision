// src/services/api.ts
import axios, { AxiosError, AxiosResponse } from 'axios';
import type {
    YOLOStats,
    LoginCredentials,
    RegisterData,
    AuthResponse,
    User,
    Settings,
    SettingsUpdate,
    LogEntry,
    SystemDiagnostics,
    APIResponse,
} from '../types';

// ============================================
// 🔗 CONFIGURATION
// ============================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 30000; // 30 seconds

// ============================================
// 🔗 AXIOS CLIENT CONFIGURATION
// ============================================

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: API_TIMEOUT,
    headers: {
        'Content-Type': 'application/json',
    },
});

// ============================================
// 📤 REQUEST INTERCEPTOR (Add Token)
// ============================================

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ============================================
// 📥 RESPONSE INTERCEPTOR (Handle Errors)
// ============================================

api.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error: AxiosError) => {
        const status = error.response?.status;

        // Handle authentication errors
        if (status === 401 || status === 403) {
            // Only redirect if not already on login page
            if (!window.location.pathname.includes('/login')) {
                console.error('❌ [API] Authentication failed, redirecting to login...');
                localStorage.removeItem('access_token');
                localStorage.removeItem('user');
                window.location.href = '/login';
            }
        }

        return Promise.reject(error);
    }
);

// ============================================
// 🎬 STREAM API
// ============================================

export const streamAPI = {
    /**
     * Get current stream status and stats
     */
    getStatus: () => api.get<YOLOStats>('/api/v1/stream/status'),

    /**
     * Start YOLO stream
     */
    start: () => api.post<APIResponse>('/api/v1/stream/start'),

    /**
     * Pause/Resume YOLO stream (toggle)
     */
    pause: () => api.post<APIResponse>('/api/v1/stream/pause'),

    /**
     * Stop YOLO stream
     */
    stop: () => api.post<APIResponse>('/api/v1/stream/stop'),
};

// ============================================
// 🔐 AUTH API
// ============================================

export const authAPI = {
    /**
     * Login user and store authentication token
     */
    login: async (credentials: LoginCredentials): Promise<AxiosResponse<AuthResponse>> => {
        try {
            console.log('🔐 [AUTH] Attempting login...');

            // Prepare form data (backend expects form-urlencoded)
            const formData = new URLSearchParams();
            formData.append('username', credentials.username);
            formData.append('password', credentials.password);

            // Make login request
            const response = await api.post<AuthResponse>('/api/v1/auth/login', formData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            });

            // ✅ Save token and user data
            if (response.data.access_token) {
                localStorage.setItem('access_token', response.data.access_token);
                console.log('✅ [AUTH] Token saved successfully');

                if (response.data.user) {
                    localStorage.setItem('user', JSON.stringify(response.data.user));
                }

                // Verify token was saved
                const savedToken = localStorage.getItem('access_token');
                if (!savedToken) {
                    throw new Error('Failed to save authentication token');
                }
            } else {
                throw new Error('No access token in response');
            }

            return response;

        } catch (error: any) {
            console.error('❌ [AUTH] Login failed:', error.response?.data || error.message);
            throw error;
        }
    },

    /**
     * Register new user
     */
    register: (data: RegisterData) => api.post<APIResponse>('/api/v1/auth/register', data),

    /**
     * Logout user
     */
    logout: async () => {
        try {
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            await api.post('/api/v1/auth/logout');
        } catch (error) {
            console.warn('⚠️ [AUTH] Logout endpoint failed (ignoring)');
        }
    },

    /**
     * Get current authenticated user
     */
    getCurrentUser: () => api.get<User>('/api/v1/auth/me'),

    /**
     * Check if user is authenticated
     */
    isAuthenticated: (): boolean => {
        return !!localStorage.getItem('access_token');
    },

    /**
     * Get stored user data
     */
    getStoredUser: (): User | null => {
        const userStr = localStorage.getItem('user');
        if (!userStr) return null;

        try {
            return JSON.parse(userStr);
        } catch (error) {
            console.error('❌ [AUTH] Failed to parse stored user:', error);
            return null;
        }
    },
};

// ============================================
// ⚙️ SETTINGS API
// ============================================

export const settingsAPI = {
    /**
     * Get all settings
     */
    getAll: () => api.get<Settings>('/api/v1/settings'),

    /**
     * Update settings
     */
    update: (settings: SettingsUpdate) => api.put<APIResponse>('/api/v1/settings', settings),

    /**
     * Reset settings to default
     */
    reset: () => api.post<APIResponse>('/api/v1/settings/reset'),
};

// ============================================
// 📋 LOGS API
// ============================================

export const logsAPI = {
    /**
     * Get recent logs
     */
    getRecent: (limit: number = 100) => api.get<LogEntry[]>(`/api/v1/logs?limit=${limit}`),

    /**
     * Get logs by level
     */
    getByLevel: (level: string, limit: number = 100) =>
        api.get<LogEntry[]>(`/api/v1/logs?level=${level}&limit=${limit}`),

    /**
     * Clear all logs
     */
    clear: () => api.delete<APIResponse>('/api/v1/logs'),
};

// ============================================
// 🔧 DIAGNOSTICS API
// ============================================

export const diagnosticsAPI = {
    /**
     * Get system diagnostics
     */
    getSystemInfo: () => api.get<SystemDiagnostics>('/api/v1/diagnostics'),

    /**
     * Run health check
     */
    healthCheck: () => api.get<APIResponse>('/health'),
};

// ============================================
// 👥 USERS API (Admin)
// ============================================

export const usersAPI = {
    /**
     * Get all users
     */
    getAll: () => api.get<User[]>('/api/v1/users'),

    /**
     * Get user by ID
     */
    getById: (id: number) => api.get<User>(`/api/v1/users/${id}`),

    /**
     * Update user
     */
    update: (id: number, data: Partial<User>) => api.put<APIResponse>(`/api/v1/users/${id}`, data),

    /**
     * Delete user
     */
    delete: (id: number) => api.delete<APIResponse>(`/api/v1/users/${id}`),
};

// ============================================
// 💾 BACKUP API (Admin)
// ============================================

export const backupAPI = {
    /**
     * Create backup
     */
    create: () => api.post<APIResponse>('/api/v1/admin/backup'),

    /**
     * List backups
     */
    list: () => api.get<string[]>('/api/v1/admin/backups'),

    /**
     * Restore backup
     */
    restore: (filename: string) => api.post<APIResponse>('/api/v1/admin/restore', { filename }),
};

export default api;
