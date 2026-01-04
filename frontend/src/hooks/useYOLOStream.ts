// src/hooks/useYOLOStream.ts
import { useState, useEffect } from 'react';
import type { YOLOStats } from '../types/dashboard';

export function useYOLOStream() {
    const [stats, setStats] = useState<YOLOStats | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchStats = async () => {
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
                setStats(data);
                setIsConnected(true);
                setError(null);
            } catch (err) {
                console.error('❌ Error fetching stream stats:', err);
                setIsConnected(false);
                setError(err instanceof Error ? err.message : 'Erro desconhecido');
            }
        };

        // Buscar imediatamente
        fetchStats();

        // Atualizar a cada 2 segundos
        const interval = setInterval(fetchStats, 2000);

        // Cleanup
        return () => clearInterval(interval);
    }, []);

    return { stats, isConnected, error };
}
