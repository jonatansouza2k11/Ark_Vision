// frontend/src/services/streamApi.ts
import axios from 'axios';

// ============================================================================
// 🎬 STREAM API CLIENT
// ============================================================================
const streamApi = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor para adicionar token
streamApi.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ============================================================================
// 📊 TYPES
// ============================================================================

export interface YOLOStats {
    fpsavg: number;
    inzone: number;
    outzone: number;
    detected_count: number;
    system_status: 'running' | 'paused' | 'stopped';
    paused: boolean;
    stream_active: boolean;
    preset: string;
    recent_alerts: any[];
}

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

export interface StreamControlResponse {
    message: string;
    status: 'running' | 'paused' | 'stopped';
    paused?: boolean;
}

// ============================================================================
// 🎯 STREAM API METHODS
// ============================================================================

export const streamAPI = {
    /**
     * Get current stream status and stats
     */
    getStatus: () => streamApi.get<YOLOStats>('/api/v1/stream/status'),

    /**
     * Start YOLO stream
     */
    start: () => streamApi.post<StreamControlResponse>('/api/v1/stream/start'),

    /**
     * Pause/Resume YOLO stream (toggle)
     */
    pause: () => streamApi.post<StreamControlResponse>('/api/v1/stream/pause'),

    /**
     * Stop YOLO stream
     */
    stop: () => streamApi.post<StreamControlResponse>('/api/v1/stream/stop'),

    /**
     * Get stream URL for video player
     */
    getStreamUrl: () => {
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        return `${baseUrl}/api/v1/stream/video`;
    },
};

export default streamApi;
