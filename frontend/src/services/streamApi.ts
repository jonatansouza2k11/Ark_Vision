import axios from 'axios';
import { YOLOStats } from '../types/dashboard';

// ============================================
// 🎬 STREAM API CLIENT
// ============================================
const streamApi = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// ✅ Interceptor para adicionar token (COM DEBUG)
streamApi.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        
        // 🔍 DEBUG: Verificar token
        console.log('🔍 [streamApi] Token from storage:', token ? `${token.substring(0, 20)}...` : 'NULL');
        console.log('🔍 [streamApi] Request URL:', config.url);
        
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
            console.log('✅ [streamApi] Authorization header set');
        } else {
            console.error('❌ [streamApi] No token found in localStorage!');
        }
        
        // 🔍 DEBUG: Ver todos os headers
        console.log('🔍 [streamApi] Request headers:', config.headers);
        
        return config;
    },
    (error) => {
        console.error('❌ [streamApi] Request interceptor error:', error);
        return Promise.reject(error);
    }
);

// ✅ Interceptor de resposta para tratar erros (COM DEBUG)
streamApi.interceptors.response.use(
    (response) => {
        console.log('✅ [streamApi] Response success:', response.status, response.config.url);
        return response;
    },
    (error) => {
        console.error('❌ [streamApi] Response error:', {
            status: error.response?.status,
            statusText: error.response?.statusText,
            data: error.response?.data,
            url: error.config?.url
        });
        
        // Se for 401 ou 403, redirecionar para login
        if (error.response?.status === 401 || error.response?.status === 403) {
            console.error('❌ [streamApi] Authentication failed, clearing token and redirecting...');
            localStorage.removeItem('access_token');
            
            // Redirecionar para login (ajuste conforme seu router)
            if (!window.location.pathname.includes('/login')) {
                window.location.href = '/login';
            }
        }
        
        return Promise.reject(error);
    }
);

// ============================================
// 📊 TYPES
// ============================================
export interface Alert {
    id?: number;
    type: 'intrusion' | 'warning' | 'info';
    message: string;
    timestamp: string;
    severity?: 'low' | 'medium' | 'high' | 'critical';
}

export interface APIResponse<T = any> {
    success: boolean;
    data?: T;
    message?: string;
    error?: string;
}

// ============================================
// 🎯 STREAM API METHODS
// ============================================
export const streamAPI = {
    /**
     * Get current stream status and stats
     */
    getStatus: () => {
        console.log('🎯 [streamAPI] Calling getStatus...');
        return streamApi.get<YOLOStats>('/api/v1/stream/status');
    },

    /**
     * Start YOLO stream
     */
    start: () => {
        console.log('🎯 [streamAPI] Calling start...');
        return streamApi.post<APIResponse>('/api/v1/stream/start');
    },

    /**
     * Pause/Resume YOLO stream (toggle)
     */
    pause: () => {
        console.log('🎯 [streamAPI] Calling pause...');
        return streamApi.post<APIResponse>('/api/v1/stream/pause');
    },

    /**
     * Stop YOLO stream
     */
    stop: () => {
        console.log('🎯 [streamAPI] Calling stop...');
        return streamApi.post<APIResponse>('/api/v1/stream/stop');
    },

    /**
     * Get stream URL for video player
     */
    getStreamUrl: () => {
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const streamUrl = `${baseUrl}/video_feed`;
        console.log('🎯 [streamAPI] Stream URL:', streamUrl);
        return streamUrl;
    },
};

export default streamApi;
