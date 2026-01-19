/**
 * useCameras.ts v2.0 - Custom Hook for Camera Management
 * State management and CRUD operations for cameras
 */

import { useState, useCallback, useEffect } from 'react';
import { toast } from 'sonner';
import * as camerasApi from '../api/camerasApi';
import type {
    Camera,
    CreateCameraPayload,
    UpdateCameraPayload
} from '../types/cameras.types';

// ============================================
// TYPES
// ============================================

interface UseCamerasReturn {
    // State
    cameras: Camera[];
    loading: boolean;
    error: string | null;

    // Actions
    fetchCameras: (activeOnly?: boolean) => Promise<void>;
    createCamera: (payload: CreateCameraPayload) => Promise<Camera>;
    updateCamera: (id: number, payload: UpdateCameraPayload) => Promise<Camera>;
    deleteCamera: (id: number) => Promise<void>;
    toggleCamera: (id: number) => Promise<Camera>;
    bulkDelete: (ids: number[]) => Promise<void>;
    refresh: () => Promise<void>;
    clearError: () => void;
}

// ============================================
// CUSTOM HOOK
// ============================================

/**
 * Custom hook for managing camera CRUD operations
 * 
 * @param autoFetch - Automatically fetch cameras on mount (default: true)
 * @returns Camera state and CRUD operations
 * 
 * @example
 * ```tsx
 * const { cameras, loading, createCamera } = useCameras();
 * 
 * const handleCreate = async (data) => {
 *   await createCamera(data);
 *   toast.success('Camera created!');
 * };
 * ```
 */
export function useCameras(autoFetch: boolean = true): UseCamerasReturn {
    const [cameras, setCameras] = useState<Camera[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // ============================================
    // FETCH CAMERAS
    // ============================================

    /**
     * Fetch all cameras from API
     * @param activeOnly - If true, fetch only enabled cameras
     */
    const fetchCameras = useCallback(async (activeOnly: boolean = false) => {
        setLoading(true);
        setError(null);

        try {
            const response = await camerasApi.listCameras(activeOnly);
            setCameras(response.cameras);
        } catch (err: any) {
            const message = err?.response?.data?.detail || err?.message || 'Erro ao carregar câmeras';
            setError(message);
            toast.error(`Erro ao carregar câmeras: ${message}`);
            console.error('Error fetching cameras:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // ============================================
    // CREATE CAMERA
    // ============================================

    /**
     * Create a new camera
     * @param payload - Camera creation data
     * @returns Created camera object
     */
    const createCamera = useCallback(async (payload: CreateCameraPayload): Promise<Camera> => {
        setLoading(true);
        setError(null);

        try {
            const newCamera = await camerasApi.createCamera(payload);
            setCameras(prev => [...prev, newCamera]);
            return newCamera;
        } catch (err: any) {
            const message = err?.response?.data?.detail || err?.message || 'Erro ao criar câmera';
            setError(message);
            console.error('Error creating camera:', err);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    // ============================================
    // UPDATE CAMERA
    // ============================================

    /**
     * Update an existing camera
     * @param id - Camera ID
     * @param payload - Camera update data
     * @returns Updated camera object
     */
    const updateCamera = useCallback(async (
        id: number,
        payload: UpdateCameraPayload
    ): Promise<Camera> => {
        setLoading(true);
        setError(null);

        try {
            const updatedCamera = await camerasApi.updateCamera(id, payload);
            setCameras(prev =>
                prev.map(camera => (camera.id === id ? updatedCamera : camera))
            );
            return updatedCamera;
        } catch (err: any) {
            const message = err?.response?.data?.detail || err?.message || 'Erro ao atualizar câmera';
            setError(message);
            console.error('Error updating camera:', err);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    // ============================================
    // DELETE CAMERA
    // ============================================

    /**
     * Delete a camera
     * @param id - Camera ID to delete
     */
    const deleteCamera = useCallback(async (id: number): Promise<void> => {
        setLoading(true);
        setError(null);

        try {
            await camerasApi.deleteCamera(id);
            setCameras(prev => prev.filter(camera => camera.id !== id));
        } catch (err: any) {
            const message = err?.response?.data?.detail || err?.message || 'Erro ao deletar câmera';
            setError(message);
            console.error('Error deleting camera:', err);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    // ============================================
    // TOGGLE CAMERA
    // ============================================

    /**
     * Toggle camera enabled status
     * @param id - Camera ID to toggle
     * @returns Updated camera object
     */
    const toggleCamera = useCallback(async (id: number): Promise<Camera> => {
        setLoading(true);
        setError(null);

        try {
            const updatedCamera = await camerasApi.toggleCamera(id);
            setCameras(prev =>
                prev.map(camera => (camera.id === id ? updatedCamera : camera))
            );
            return updatedCamera;
        } catch (err: any) {
            const message = err?.response?.data?.detail || err?.message || 'Erro ao alternar câmera';
            setError(message);
            console.error('Error toggling camera:', err);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    // ============================================
    // BULK DELETE
    // ============================================

    /**
     * Delete multiple cameras
     * @param ids - Array of camera IDs to delete
     */
    const bulkDelete = useCallback(async (ids: number[]): Promise<void> => {
        setLoading(true);
        setError(null);

        try {
            await camerasApi.bulkDeleteCameras(ids);
            setCameras(prev => prev.filter(camera => !ids.includes(camera.id)));
        } catch (err: any) {
            const message = err?.response?.data?.detail || err?.message || 'Erro ao deletar câmeras';
            setError(message);
            console.error('Error bulk deleting cameras:', err);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    // ============================================
    // REFRESH
    // ============================================

    /**
     * Refresh the cameras list
     */
    const refresh = useCallback(async () => {
        await fetchCameras();
    }, [fetchCameras]);

    // ============================================
    // CLEAR ERROR
    // ============================================

    /**
     * Clear the current error state
     */
    const clearError = useCallback(() => {
        setError(null);
    }, []);

    // ============================================
    // AUTO FETCH ON MOUNT
    // ============================================

    useEffect(() => {
        if (autoFetch) {
            fetchCameras();
        }
    }, [autoFetch, fetchCameras]);

    // ============================================
    // RETURN
    // ============================================

    return {
        cameras,
        loading,
        error,
        fetchCameras,
        createCamera,
        updateCamera,
        deleteCamera,
        toggleCamera,
        bulkDelete,
        refresh,
        clearError
    };
}

export default useCameras;
