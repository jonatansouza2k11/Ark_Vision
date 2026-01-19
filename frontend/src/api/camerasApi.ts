/**
 * camerasApi.ts - Cameras API Client
 * HTTP client for camera CRUD operations
 * Matches backend endpoints: /api/v1/cameras/
 */

import axios from 'axios';
import type {
    Camera,
    CreateCameraPayload,
    UpdateCameraPayload,
    CameraCrudListResponse  // 🔥 CORRIGIDO: Novo nome
} from '../types/cameras.types';

// ============================================
// CONFIGURATION
// ============================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const CAMERAS_ENDPOINT = `${API_BASE_URL}/api/v1/cameras/`;

// ============================================
// AUTH HELPERS
// ============================================

function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('access_token');
    return token
        ? {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
        : { 'Content-Type': 'application/json' };
}

// ============================================
// API FUNCTIONS
// ============================================

/**
 * List all cameras
 */
export async function listCameras(activeOnly: boolean = false): Promise<CameraCrudListResponse> {
    const response = await axios.get<CameraCrudListResponse>(CAMERAS_ENDPOINT, {
        headers: getAuthHeaders(),
        params: { active_only: activeOnly }
    });
    return response.data;
}

/**
 * List only active cameras
 */
export async function listActiveCameras(): Promise<CameraCrudListResponse> {
    const response = await axios.get<CameraCrudListResponse>(`${CAMERAS_ENDPOINT}active`, {
        headers: getAuthHeaders()
    });
    return response.data;
}

/**
 * Get camera by ID
 */
export async function getCameraById(cameraId: number): Promise<Camera> {
    const response = await axios.get<Camera>(`${CAMERAS_ENDPOINT}${cameraId}`, {
        headers: getAuthHeaders()
    });
    return response.data;
}

/**
 * Create new camera (ADMIN only)
 */
export async function createCamera(payload: CreateCameraPayload): Promise<Camera> {
    const response = await axios.post<Camera>(CAMERAS_ENDPOINT, payload, {
        headers: getAuthHeaders()
    });
    return response.data;
}

/**
 * Update camera (ADMIN only)
 */
export async function updateCamera(
    cameraId: number,
    payload: UpdateCameraPayload
): Promise<Camera> {
    const response = await axios.put<Camera>(`${CAMERAS_ENDPOINT}${cameraId}`, payload, {
        headers: getAuthHeaders()
    });
    return response.data;
}

/**
 * Delete camera (ADMIN only)
 */
export async function deleteCamera(cameraId: number): Promise<void> {
    await axios.delete(`${CAMERAS_ENDPOINT}${cameraId}`, {
        headers: getAuthHeaders()
    });
}

/**
 * Toggle camera enabled status (ADMIN only)
 */
export async function toggleCamera(cameraId: number): Promise<Camera> {
    const response = await axios.patch<Camera>(
        `${CAMERAS_ENDPOINT}${cameraId}/toggle`,
        {},
        { headers: getAuthHeaders() }
    );
    return response.data;
}

// ============================================
// BULK OPERATIONS
// ============================================

/**
 * Delete multiple cameras (ADMIN only)
 */
export async function bulkDeleteCameras(cameraIds: number[]): Promise<void> {
    await Promise.all(cameraIds.map(id => deleteCamera(id)));
}

/**
 * Toggle multiple cameras (ADMIN only)
 */
export async function bulkToggleCameras(cameraIds: number[]): Promise<Camera[]> {
    const results = await Promise.all(cameraIds.map(id => toggleCamera(id)));
    return results;
}

// ============================================
// EXPORT DEFAULT
// ============================================

export default {
    listCameras,
    listActiveCameras,
    getCameraById,
    createCamera,
    updateCamera,
    deleteCamera,
    toggleCamera,
    bulkDeleteCameras,
    bulkToggleCameras
};
