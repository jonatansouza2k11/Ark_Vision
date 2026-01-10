// frontend/src/hooks/useYOLOStream.ts - v3.3.1 (FIXED)
import { useState, useEffect, useRef } from 'react';
import type { YOLOStats } from '../types/dashboard';

/**
 * ✅ v3.3.1 FIXES:
 * - Cleanup adequado ao desmontar
 * - Previne memory leaks
 * - Intervalo configurável
 * - Verifica mount state antes de atualizar
 * 
 * Hook para buscar stats do stream YOLO periodicamente
 * @param pollInterval - Intervalo de polling em ms (padrão: 2000ms)
 * @param enabled - Se o polling está ativo (padrão: true)
 */
export function useYOLOStream(pollInterval: number = 2000, enabled: boolean = true) {
    const [stats, setStats] = useState<YOLOStats | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // ✅ v3.3.1: Track mount state to prevent updates after unmount
    const isMountedRef = useRef(true);
    const intervalRef = useRef<NodeJS.Timeout | null>(null);

    // ✅ v3.3.1: Setup mount tracking
    useEffect(() => {
        isMountedRef.current = true;

        // Cleanup on unmount
        return () => {
            isMountedRef.current = false;
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        };
    }, []);

    useEffect(() => {
        if (!enabled) {
            // Clear interval if disabled
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
            return;
        }

        const fetchStats = async () => {
            // ✅ v3.3.1: Don't fetch if unmounted
            if (!isMountedRef.current) return;

            try {
                const token = localStorage.getItem('access_token');
                const response = await fetch('http://localhost:8000/api/v1/stream/status', {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();

                // ✅ v3.3.1: Only update state if still mounted
                if (isMountedRef.current) {
                    setStats(data);
                    setIsConnected(true);
                    setError(null);
                }
            } catch (err) {
                console.error('❌ Error fetching stream stats:', err);

                // ✅ v3.3.1: Only update state if still mounted
                if (isMountedRef.current) {
                    setIsConnected(false);
                    setError(err instanceof Error ? err.message : 'Erro desconhecido');
                }
            }
        };

        // Buscar imediatamente
        fetchStats();

        // ✅ v3.3.1: Clear existing interval before creating new one
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
        }

        // Atualizar periodicamente
        intervalRef.current = setInterval(fetchStats, pollInterval);

        // Cleanup on dependencies change
        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        };
    }, [pollInterval, enabled]);

    return { stats, isConnected, error };
}
