// frontend/src/services/logsApi.ts

import api from './api';
import type {
    SystemLog,
    LogSearchRequest,
    LogSearchResponse,
    ExportFormat,
} from '../types/logs';
import { AxiosResponse } from 'axios';

/**
 * ============================================================================
 * LOGS API SERVICE
 * Todas as chamadas para endpoints de logs do backend
 * ============================================================================
 */

export const logsApi = {
    // ==================== SYSTEM LOGS ====================

    /**
     * GET /api/v1/admin/logs
     * Lista logs do sistema com limite
     */
    getSystemLogs: async (limit: number = 100): Promise<AxiosResponse<{ logs: SystemLog[]; count: number }>> => {
        return api.get('/api/v1/admin/logs', {
            params: { limit },
        });
    },

    /**
     * POST /api/v1/admin/logs/search
     * Busca avançada de logs com filtros
     */
    searchLogs: async (searchParams: LogSearchRequest): Promise<AxiosResponse<LogSearchResponse>> => {
        return api.post('/api/v1/admin/logs/search', searchParams);
    },

    /**
     * POST /api/v1/admin/logs/export
     * Exporta logs em JSON ou CSV
     */
    exportLogs: async (format: ExportFormat = 'json', limit: number = 1000): Promise<AxiosResponse<any>> => {
        return api.post('/api/v1/admin/logs/export', null, {
            params: { format, limit },
            responseType: format === 'csv' ? 'blob' : 'json',
        });
    },

    /**
     * DELETE /api/v1/admin/logs/old
     * Remove logs mais antigos que X dias
     */
    clearOldLogs: async (days: number = 30): Promise<AxiosResponse<{ message: string; days: number }>> => {
        return api.delete('/api/v1/admin/logs/old', {
            params: { days },
        });
    },

    // ==================== STATISTICS ====================

    /**
     * Calcula estatísticas localmente a partir dos logs
     * (Não há endpoint específico no backend, fazemos client-side)
     */
    calculateStatistics: (logs: SystemLog[]) => {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const thisWeek = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        const thisMonth = new Date(now.getFullYear(), now.getMonth(), 1);

        const stats = {
            total: logs.length,
            today: 0,
            this_week: 0,
            this_month: 0,
            by_action: {} as Record<string, number>,
            by_user: {} as Record<string, number>,
        };

        logs.forEach((log) => {
            const logDate = new Date(log.timestamp);

            // Count by period
            if (logDate >= today) stats.today++;
            if (logDate >= thisWeek) stats.this_week++;
            if (logDate >= thisMonth) stats.this_month++;

            // Count by action
            stats.by_action[log.action] = (stats.by_action[log.action] || 0) + 1;

            // Count by user
            if (log.username) {
                stats.by_user[log.username] = (stats.by_user[log.username] || 0) + 1;
            }
        });

        return stats;
    },

    // ==================== HELPER ====================

    /**
     * Download blob as file (para exports CSV)
     */
    downloadBlob: (blob: Blob, filename: string) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    },
};

export default logsApi;
