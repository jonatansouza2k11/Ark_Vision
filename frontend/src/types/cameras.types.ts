/**
 * cameras.types.ts - Camera Types for ARK Vision v2.0
 * Type definitions matching backend API models
 * Updated for multi-camera streaming with individual camera_id
 */

import type { TrackerType } from './trackers.types';

export interface CameraMetadata {
    default_tracker?: TrackerType;
    // outras chaves livres que você já use
    [key: string]: any;
  }

// ============================================
// ENUMS
// ============================================

export enum CameraStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
    ERROR = 'error',
    CONNECTING = 'connecting'
}

export enum StreamStatus {
    RUNNING = 'running',
    STOPPED = 'stopped',
    PAUSED = 'paused',
    ERROR = 'error'
}

// ============================================
// BASE TYPES - Database Models
// ============================================

export interface Camera {
    id: number;
    name: string;
    source: string;
    location: string | null;
    username: string | null;
    password: string | null;
    enabled: boolean;
    //metadata: Record<string, any>;
    metadata: CameraMetadata;
    created_at: string;
    updated_at: string | null;
}

export interface CreateCameraPayload {
    name: string;
    source: string;
    location?: string | null;
    username?: string | null;
    password?: string | null;
    enabled?: boolean;
    //metadata?: Record<string, any>;
    metadata?: CameraMetadata;
}

export interface UpdateCameraPayload {
    name?: string;
    source?: string;
    location?: string | null;
    username?: string | null;
    password?: string | null;
    enabled?: boolean;
    //metadata?: Record<string, any>;
    metadata?: CameraMetadata;
}

// 🔥 RENOMEADO: Para diferenciar da resposta de runtime status
export interface CameraCrudListResponse {
    total: number;
    cameras: Camera[];
}

// ============================================
// STREAMING & RUNTIME STATUS TYPES
// ============================================

/**
 * Status detalhado de streaming de uma câmera específica
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
    system_status: StreamStatus;
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
 * Informações de conexões ativas (admin)
 * Retornado por: GET /api/v1/stream/connections
 */
export interface StreamConnectionsInfo {
    active_by_camera: Record<number, string[]>;
    total_count: number;
    limit: number;
    memory_status: {
        available: boolean;
        percent_used: number;
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

// ============================================
// UI STATE TYPES
// ============================================

export interface CameraFormData {
    name: string;
    source: string;
    location: string;
    username: string;
    password: string;
    enabled: boolean;
    //metadata: Record<string, any>;
    metadata: CameraMetadata;

}

export interface CameraFilters {
    search: string;
    enabled: boolean | null;
    location: string | null;
}

/**
 * 🔥 NOVO: Estado do visualizador de stream
 */
export interface StreamViewerState {
    selectedCameraId: number | null;
    availableCameras: CameraRuntimeStatus[];
    streamUrl: string | null;
    isStreaming: boolean;
    isLoading: boolean;
    error: string | null;
}

/**
 * 🔥 NOVO: Configuração de seleção de câmera
 */
export interface CameraSelectionConfig {
    cameraId: number;
    autoStart?: boolean;
    showControls?: boolean;
}

// ============================================
// CONSTANTS
// ============================================

export const CAMERA_SOURCE_TYPES = {
    RTSP: 'rtsp',
    HTTP: 'http',
    DEVICE: 'device',
    FILE: 'file'
} as const;

export const DEFAULT_CAMERA_FORM: CameraFormData = {
    name: '',
    source: '',
    location: '',
    username: '',
    password: '',
    enabled: true,
    metadata: {}
};

// 🔥 NOVO: Configurações de stream
export const STREAM_CONFIG = {
    BASE_URL: '/api/v1/stream',
    DEFAULT_RECONNECT_DELAY: 3000,
    MAX_RECONNECT_ATTEMPTS: 5,
    STATUS_POLL_INTERVAL: 2000,
} as const;

// ============================================
// HELPER FUNCTIONS
// ============================================

export function getCameraSourceType(source: string): string {
    if (source.startsWith('rtsp://')) return CAMERA_SOURCE_TYPES.RTSP;
    if (source.startsWith('http://') || source.startsWith('https://')) return CAMERA_SOURCE_TYPES.HTTP;
    if (/^\d+$/.test(source)) return CAMERA_SOURCE_TYPES.DEVICE;
    return CAMERA_SOURCE_TYPES.FILE;
}

export function getCameraStatusColor(enabled: boolean): string {
    return enabled ? 'green' : 'gray';
}

export function getCameraStatusText(enabled: boolean): string {
    return enabled ? 'Ativa' : 'Inativa';
}

/**
 * 🔥 NOVO: Retorna cor baseada no status de streaming
 */
export function getStreamStatusColor(status: StreamStatus): string {
    switch (status) {
        case StreamStatus.RUNNING:
            return 'green';
        case StreamStatus.PAUSED:
            return 'yellow';
        case StreamStatus.STOPPED:
            return 'gray';
        case StreamStatus.ERROR:
            return 'red';
        default:
            return 'gray';
    }
}

/**
 * Retorna texto traduzido do status
 */
export function getStreamStatusText(status: StreamStatus): string {
    switch (status) {
        case StreamStatus.RUNNING:
            return 'Em execução';
        case StreamStatus.PAUSED:
            return 'Pausado';
        case StreamStatus.STOPPED:
            return 'Parado';
        case StreamStatus.ERROR:
            return 'Erro';
        default:
            return 'Desconhecido';
    }
}

export function formatCameraSource(source: string): string {
    const type = getCameraSourceType(source);

    switch (type) {
        case CAMERA_SOURCE_TYPES.RTSP:
            return `RTSP: ${source.replace(/\/\/.*@/, '//***@')}`; // Hide credentials
        case CAMERA_SOURCE_TYPES.HTTP:
            return `HTTP: ${source}`;
        case CAMERA_SOURCE_TYPES.DEVICE:
            return `Dispositivo: ${source}`;
        case CAMERA_SOURCE_TYPES.FILE:
            return `Arquivo: ${source}`;
        default:
            return source;
    }
}

export function validateCameraForm(data: CameraFormData): string[] {
    const errors: string[] = [];

    if (!data.name || data.name.trim().length === 0) {
        errors.push('Nome da câmera é obrigatório');
    }

    if (!data.source || data.source.trim().length === 0) {
        errors.push('Source da câmera é obrigatório');
    }

    if (data.name.length > 100) {
        errors.push('Nome não pode ter mais de 100 caracteres');
    }

    if (data.source.length > 500) {
        errors.push('Source não pode ter mais de 500 caracteres');
    }

    return errors;
}

/**
 * Gera URL de stream para câmera específica
 */
export function getStreamUrl(cameraId: number): string {
    return `${STREAM_CONFIG.BASE_URL}/video_feed/${cameraId}`;
}

/**
 * Gera URL de snapshot para câmera específica
 */
export function getSnapshotUrl(cameraId: number): string {
    return `${STREAM_CONFIG.BASE_URL}/snapshot/${cameraId}`;
}

/**
 * 🔥 NOVO: Gera URL de status para câmera específica
 */
export function getStatusUrl(cameraId: number): string {
    return `${STREAM_CONFIG.BASE_URL}/status/${cameraId}`;
}

/**
 * 🔥 NOVO: Verifica se câmera está disponível para streaming
 */
export function isCameraStreamable(camera: Camera): boolean {
    return camera.enabled && camera.source.trim().length > 0;
}

/**
 * 🔥 NOVO: Formata FPS com 1 casa decimal
 */
export function formatFPS(fps: number): string {
    return fps.toFixed(1);
}

/**
 * 🔥 NOVO: Valida camera_id
 */
export function isValidCameraId(cameraId: any): cameraId is number {
    return typeof cameraId === 'number' && cameraId > 0 && Number.isInteger(cameraId);
}
