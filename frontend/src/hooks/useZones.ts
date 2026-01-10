/**
 * ============================================================================
 * useZones.ts - Hook para gerenciar zonas v3.0
 * ============================================================================
 * Hook customizado com CRUD completo + estatísticas
 * ============================================================================
 */

import { useState, useCallback } from 'react';
import { zonesApi } from '../api/zonesApi';
import type {
    Zone,
    CreateZonePayload,
    UpdateZonePayload,
    ZoneStatistics
} from '../types/zones.types';


// ============================================================================
// INTERFACE
// ============================================================================

interface UseZonesReturn {
    // State
    zones: Zone[];
    loading: boolean;
    error: string | null;
    statistics: ZoneStatistics | null;

    // CRUD Operations
    fetchZones: (includeDisabled?: boolean) => Promise<void>;
    createZone: (payload: CreateZonePayload) => Promise<Zone | null>;
    updateZone: (id: number, payload: UpdateZonePayload) => Promise<Zone | null>;
    deleteZone: (id: number) => Promise<boolean>;
    toggleZone: (id: number, enabled: boolean) => Promise<boolean>;

    // Bulk Operations
    bulkDelete: (ids: number[]) => Promise<boolean>;
    deleteMultiple: (ids: number[]) => Promise<boolean>; // Mantém compatibilidade

    // Statistics
    loadStatistics: () => Promise<void>;

    // Utility
    refresh: () => Promise<void>;
    refreshZones: () => Promise<void>; // Mantém compatibilidade
    clearError: () => void;
}


// ============================================================================
// HOOK
// ============================================================================

export function useZones(): UseZonesReturn {
    // ==========================================================================
    // STATE
    // ==========================================================================

    const [zones, setZones] = useState<Zone[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [statistics, setStatistics] = useState<ZoneStatistics | null>(null);

    // ==========================================================================
    // FETCH ZONES
    // ==========================================================================

    const fetchZones = useCallback(async (includeDisabled = false) => {
        setLoading(true);
        setError(null);

        try {
            const data = await zonesApi.listZones(includeDisabled);
            setZones(data);
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Erro ao buscar zonas';
            setError(errorMessage);
            console.error('Erro ao buscar zonas:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // ==========================================================================
    // LOAD STATISTICS
    // ==========================================================================

    const loadStatistics = useCallback(async () => {
        try {
            const stats = await zonesApi.getStatistics();
            setStatistics(stats);
        } catch (err) {
            console.error('Erro ao carregar estatísticas:', err);
            // Não mostra erro ao usuário, apenas loga
        }
    }, []);

    // ==========================================================================
    // CREATE ZONE
    // ==========================================================================

    const createZone = useCallback(async (payload: CreateZonePayload): Promise<Zone | null> => {
        setLoading(true);
        setError(null);

        try {
            const newZone = await zonesApi.createZone(payload);
            setZones(prev => [...prev, newZone]);

            // Atualiza estatísticas após criar
            await loadStatistics();

            return newZone;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Erro ao criar zona';
            setError(errorMessage);
            console.error('Erro ao criar zona:', err);
            return null;
        } finally {
            setLoading(false);
        }
    }, [loadStatistics]);

    // ==========================================================================
    // UPDATE ZONE
    // ==========================================================================

    const updateZone = useCallback(async (
        id: number,
        payload: UpdateZonePayload
    ): Promise<Zone | null> => {
        setLoading(true);
        setError(null);

        try {
            const updatedZone = await zonesApi.updateZone(id, payload);
            setZones(prev => prev.map(z => z.id === id ? updatedZone : z));

            // Atualiza estatísticas após atualizar
            await loadStatistics();

            return updatedZone;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Erro ao atualizar zona';
            setError(errorMessage);
            console.error('Erro ao atualizar zona:', err);
            return null;
        } finally {
            setLoading(false);
        }
    }, [loadStatistics]);

    // ==========================================================================
    // DELETE ZONE
    // ==========================================================================

    const deleteZone = useCallback(async (id: number): Promise<boolean> => {
        setLoading(true);
        setError(null);

        try {
            await zonesApi.deleteZone(id);
            setZones(prev => prev.filter(z => z.id !== id));

            // Atualiza estatísticas após deletar
            await loadStatistics();

            return true;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Erro ao deletar zona';
            setError(errorMessage);
            console.error('Erro ao deletar zona:', err);
            return false;
        } finally {
            setLoading(false);
        }
    }, [loadStatistics]);

    // ==========================================================================
    // TOGGLE ZONE (Enable/Disable)
    // ==========================================================================

    const toggleZone = useCallback(async (
        id: number,
        enabled: boolean
    ): Promise<boolean> => {
        setLoading(true);
        setError(null);

        try {
            const updatedZone = await zonesApi.updateZone(id, { enabled });
            setZones(prev => prev.map(z => z.id === id ? updatedZone : z));

            // Atualiza estatísticas após toggle
            await loadStatistics();

            return true;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Erro ao alterar status';
            setError(errorMessage);
            console.error('Erro ao alterar status da zona:', err);
            return false;
        } finally {
            setLoading(false);
        }
    }, [loadStatistics]);

    // ==========================================================================
    // BULK DELETE
    // ==========================================================================

    const bulkDelete = useCallback(async (ids: number[]): Promise<boolean> => {
        if (ids.length === 0) return false;

        setLoading(true);
        setError(null);

        try {
            await zonesApi.deleteMultipleZones(ids);
            setZones(prev => prev.filter(z => !ids.includes(z.id)));

            // Atualiza estatísticas após deletar múltiplas
            await loadStatistics();

            return true;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Erro ao deletar zonas';
            setError(errorMessage);
            console.error('Erro ao deletar múltiplas zonas:', err);
            return false;
        } finally {
            setLoading(false);
        }
    }, [loadStatistics]);

    // Alias para manter compatibilidade
    const deleteMultiple = bulkDelete;

    // ==========================================================================
    // REFRESH ALL
    // ==========================================================================

    const refresh = useCallback(async () => {
        await Promise.all([
            fetchZones(),
            loadStatistics()
        ]);
    }, [fetchZones, loadStatistics]);

    // Alias para manter compatibilidade
    const refreshZones = refresh;

    // ==========================================================================
    // CLEAR ERROR
    // ==========================================================================

    const clearError = useCallback(() => {
        setError(null);
    }, []);

    // ==========================================================================
    // RETURN
    // ==========================================================================

    return {
        // State
        zones,
        loading,
        error,
        statistics,

        // CRUD Operations
        fetchZones,
        createZone,
        updateZone,
        deleteZone,
        toggleZone,

        // Bulk Operations
        bulkDelete,
        deleteMultiple, // Alias

        // Statistics
        loadStatistics,

        // Utility
        refresh,
        refreshZones, // Alias
        clearError,
    };
}
