/**
 * cameras.types.ts - Camera Types for ARK Vision
 * Type definitions matching backend API models
 */

// ============================================
// ENUMS
// ============================================

export enum CameraStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
    ERROR = 'error',
    CONNECTING = 'connecting'
}

// ============================================
// BASE TYPES
// ============================================

export interface Camera {
    id: number;
    name: string;
    source: string;
    location: string | null;
    username: string | null;
    password: string | null;
    enabled: boolean;
    metadata: Record<string, any>;
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
    metadata?: Record<string, any>;
}

export interface UpdateCameraPayload {
    name?: string;
    source?: string;
    location?: string | null;
    username?: string | null;
    password?: string | null;
    enabled?: boolean;
    metadata?: Record<string, any>;
}

export interface CameraListResponse {
    total: number;
    cameras: Camera[];
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
    metadata: Record<string, any>;
}

export interface CameraFilters {
    search: string;
    enabled: boolean | null;
    location: string | null;
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
