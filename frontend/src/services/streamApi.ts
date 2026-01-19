/**
 * streamApi.ts - Stream API Client v2.1
 * Multi-camera streaming API client for ARK Vision
 * Matches backend endpoints: /api/v1/stream/
 *
 * Suporta:
 * - /video_feed/{camera_id}
 * - /status            (global)
 * - /status/{camera_id}
 * - /cameras
 * - /snapshot/{camera_id}
 * - /start /pause /stop /reload_cameras /connections
 */

import axios, { type AxiosResponse } from 'axios';

// ============================================================================
// 🔧 AXIOS INSTANCE
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
            config.headers = config.headers ?? {};
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error),
);

// ============================================================================
// 📊 TYPES - Updated for Multi-Camera Support
// ============================================================================

/**
 * Status de streaming de uma câmera específica
 * Retornado por: GET /api/v1/stream/status/{camera_id}
 */
export interface CameraStreamStatus {
    camera_id: number;
    camera_name: string;
    fps_current: number;
    fps_avg: number;
    inzone: number;
    outzone: number;
    detected_count: number;
    system_status: 'running' | 'stopped' | 'paused' | 'error';
    paused: boolean;
    stream_active: boolean;
    active_connections: number;
    zones_loaded: number;
    active_tracks: number;
}

/**
 * Status resumido de runtime de uma câmera
 * Retornado por: GET /api/v1/stream/cameras
 */
export interface CameraRuntimeStatus {
    camera_id: number;
    name: string;
    running: boolean;
    current_fps: number;
    avg_fps: number;
    detections_today: number;
    active_tracks: number;
    zones_loaded: number;
}

/**
 * @deprecated Use CameraStreamStatus instead
 * Mantido para compatibilidade com código legado (useYOLOStream)
 */
export interface YOLOStats {
    fpsavg: number;
    inzone: number;
    outzone: number;
    detected_count: number;
    system_status: 'running' | 'paused' | 'stopped';
    paused: boolean;
    stream_active: boolean;
    preset: string;
    recent_alerts?: any[];
}

export interface Alert {
    id?: number;
    type: 'intrusion' | 'warning' | 'info';
    message: string;
    timestamp: string;
    severity?: 'low' | 'medium' | 'high' | 'critical';
}

/**
 * Generic API response wrapper (não muito usado aqui, mas mantido)
 */
export interface APIResponse<T = any> {
    success: boolean;
    data?: T;
    message?: string;
    error?: string;
}

export interface StreamControlResponse {
    message?: string;
    status: 'running' | 'paused' | 'stopped';
    paused?: boolean;
    cameras?: number[];
}

export interface ReloadCamerasResponse {
    status: string;
    cameras: number[];
    message: string;
}

export interface StreamConnectionsInfo {
    active_by_camera: Record<number, number>;
    total_count: number;
    limit: number;
    memory_status: {
        available: number;
        percent_used: number;
        threshold_percent: number;
        min_available_mb: number;
        available_ok: boolean;
    };
    stats: {
        total_frames: number;
        restarts: number;
        errors: number;
        memory_errors: number;
    };
    recent_events: Array<{
        type: string;
        timestamp: string;
        message: string;
    }>;
}

// ============================================================================
// 🎯 STREAM API METHODS v2.1
// ============================================================================

export const streamAPI = {
    // ========================================================================
    // 📹 VIDEO STREAMING
    // ========================================================================

    /**
     * Get stream URL for specific camera
     * Use this URL in <img> tag for MJPEG streaming
     *
     * @param cameraId - Camera ID from database
     * @returns Full URL for video feed
     *
     * @example
     * const streamUrl = streamAPI.getStreamUrl(1);
     */
    getStreamUrl: (cameraId: number): string => {
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        return `${baseUrl}/api/v1/stream/video_feed/${cameraId}`;
    },

    /**
     * @deprecated Use getStreamUrl(cameraId) instead
     * Maintained for backward compatibility - returns URL for camera ID 1
     */
    getStreamUrlLegacy: (): string => {
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        console.warn(
            '⚠️ getStreamUrlLegacy is deprecated. Use getStreamUrl(cameraId) instead.',
        );
        return `${baseUrl}/api/v1/stream/video_feed/1`;
    },

    // ========================================================================
    // 📊 STATUS & MONITORING
    // ========================================================================

    /**
     * Get detailed streaming status for specific camera
     *
     * @param cameraId - Camera ID
     * @returns AxiosResponse<CameraStreamStatus>
     */
    getStatus: (
        cameraId: number,
    ): Promise<AxiosResponse<CameraStreamStatus>> =>
        streamApi.get<CameraStreamStatus>(`/api/v1/stream/status/${cameraId}`),

    /**
     * Get list of all cameras with runtime status
     * Returns cameras loaded in VisionSystem with FPS, detections, etc.
     */
    getCameras: (): Promise<AxiosResponse<CameraRuntimeStatus[]>> =>
        streamApi.get<CameraRuntimeStatus[]>('/api/v1/stream/cameras'),

    /**
     * Get active streaming connections (ADMIN only)
     *
     * @returns Connection statistics and memory status
     */
    getConnections: (): Promise<AxiosResponse<StreamConnectionsInfo>> =>
        streamApi.get<StreamConnectionsInfo>('/api/v1/stream/connections'),

    // ========================================================================
    // 📸 SNAPSHOT
    // ========================================================================

    /**
     * Get snapshot (single frame) from specific camera
     *
     * @param cameraId - Camera ID
     * @returns Blob containing JPEG image
     */
    getSnapshot: async (cameraId: number): Promise<Blob> => {
        const response = await streamApi.get(`/api/v1/stream/snapshot/${cameraId}`, {
            responseType: 'blob',
        });
        return response.data as Blob;
    },

    /**
     * Download snapshot as file
     *
     * @param cameraId - Camera ID
     * @param filename - Optional custom filename
     */
    downloadSnapshot: async (
        cameraId: number,
        filename?: string,
    ): Promise<void> => {
        const blob = await streamAPI.getSnapshot(cameraId);
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');

        link.href = url;
        link.download = filename || `camera-${cameraId}-${Date.now()}.jpg`;

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    },

    // ========================================================================
    // 🎮 STREAM CONTROL
    // ========================================================================

    /**
     * Start all enabled cameras
     * Initializes VisionSystem and begins capture/inference
     */
    start: (): Promise<AxiosResponse<StreamControlResponse>> =>
        streamApi.post<StreamControlResponse>('/api/v1/stream/start'),

    /**
     * Pause/Resume YOLO stream (toggle)
     * Pauses processing while maintaining capture
     */
    pause: (): Promise<AxiosResponse<StreamControlResponse>> =>
        streamApi.post<StreamControlResponse>('/api/v1/stream/pause'),

    /**
     * Stop all cameras
     * Stops VisionSystem and releases resources
     */
    stop: (): Promise<AxiosResponse<StreamControlResponse>> =>
        streamApi.post<StreamControlResponse>('/api/v1/stream/stop'),

    /**
     * Reload cameras from database
     * Useful after enabling/disabling cameras without backend restart
     *
     * @returns Updated camera list (ids)
     */
    reloadCameras: (): Promise<AxiosResponse<ReloadCamerasResponse>> =>
        streamApi.post<ReloadCamerasResponse>('/api/v1/stream/reload_cameras'),

    // ========================================================================
    // 🔧 HELPER METHODS
    // ========================================================================

    /**
     * Check if specific camera is currently streaming
     *
     * @param cameraId - Camera ID to check
     * @returns True if camera is active and streaming
     */
    isCameraStreaming: async (cameraId: number): Promise<boolean> => {
        try {
            const response = await streamAPI.getStatus(cameraId);
            return (
                response.data.stream_active &&
                response.data.system_status === 'running'
            );
        } catch {
            return false;
        }
    },

    /**
     * Wait for camera to start streaming
     * Polls status until active or timeout
     *
     * @param cameraId - Camera ID
     * @param timeoutMs - Timeout in milliseconds (default: 10000)
     * @param intervalMs - Poll interval (default: 500)
     * @returns True if started successfully
     */
    waitForCameraStream: async (
        cameraId: number,
        timeoutMs: number = 10000,
        intervalMs: number = 500,
    ): Promise<boolean> => {
        const startTime = Date.now();

        while (Date.now() - startTime < timeoutMs) {
            if (await streamAPI.isCameraStreaming(cameraId)) {
                return true;
            }
            await new Promise((resolve) => setTimeout(resolve, intervalMs));
        }

        return false;
    },

    /**
     * Create a polling function for camera status
     * Returns cleanup function to stop polling
     *
     * @param cameraId - Camera ID to poll
     * @param callback - Function called with each status update
     * @param intervalMs - Poll interval (default: 2000)
     */
    pollCameraStatus: (
        cameraId: number,
        callback: (status: CameraStreamStatus) => void,
        intervalMs: number = 2000,
    ): (() => void) => {
        let active = true;

        const poll = async () => {
            while (active) {
                try {
                    const response = await streamAPI.getStatus(cameraId);
                    callback(response.data);
                } catch (error) {
                    console.error(`Error polling camera ${cameraId}:`, error);
                }
                await new Promise((resolve) => setTimeout(resolve, intervalMs));
            }
        };

        poll();

        return () => {
            active = false;
        };
    },
};

export default streamApi;
