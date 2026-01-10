// src/api/dashboard.ts
import {
    DashboardData,
    SystemInfo,
    DashboardStats,
    Alert,
    SystemLog,
    SystemSettings,
    Activity,
    ZonesStatisticsResponse,
} from '../types/dashboard';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
    };
};

async function parseJsonOrThrow<T>(response: Response, fallbackMessage: string): Promise<T> {
    if (!response.ok) {
        // tenta ler um erro do backend sem “quebrar” a UX
        try {
            const payload = await response.json();
            const detail =
                (payload && (payload.detail || payload.message || payload.error)) ??
                fallbackMessage;
            throw new Error(typeof detail === 'string' ? detail : fallbackMessage);
        } catch {
            throw new Error(fallbackMessage);
        }
    }
    return (await response.json()) as T;
}

// Backend atual (zones.py) retorna campos como totalzones, enabledzones...
type BackendZonesStatisticsResponse = {
    totalzones: number;
    enabledzones: number;
    disabledzones: number;
    activezones: number;
    zonesbymode: Record<string, number>;
    averagearea: number | null;
    totaldetections?: number | null;
    mostactivezones?: Array<Record<string, any>>;
    timestamp: string;
};

function mapZonesStatisticsResponse(
    backend: BackendZonesStatisticsResponse
): ZonesStatisticsResponse {
    return {
        total_zones: backend.totalzones,
        enabled_zones: backend.enabledzones,
        disabled_zones: backend.disabledzones,
        active_zones: backend.activezones,
        zones_by_mode: backend.zonesbymode ?? {},
        average_area: backend.averagearea ?? 0,
        total_detections: backend.totaldetections ?? null,
        most_active_zones: backend.mostactivezones ?? [],
        timestamp: backend.timestamp,
    };
}

export const dashboardApi = {
    // ==========================================
    // DASHBOARD PRINCIPAL
    // ==========================================

    async getDashboardData(): Promise<DashboardData> {
        const response = await fetch(`${API_URL}/api/v1/dashboard`, {
            headers: getAuthHeaders(),
        });
        return parseJsonOrThrow<DashboardData>(response, 'Erro ao buscar dados do dashboard');
    },

    async getSystemInfo(): Promise<SystemInfo> {
        const response = await fetch(`${API_URL}/api/v1/system/info`, {
            headers: getAuthHeaders(),
        });
        return parseJsonOrThrow<SystemInfo>(response, 'Erro ao buscar informações do sistema');
    },

    async getStats(): Promise<DashboardStats> {
        const response = await fetch(`${API_URL}/api/v1/stats`, {
            headers: getAuthHeaders(),
        });
        return parseJsonOrThrow<DashboardStats>(response, 'Erro ao buscar estatísticas');
    },

    // ==========================================
    // ZONAS (NEW v3.0)
    // ==========================================

    async getZonesStatistics(): Promise<ZonesStatisticsResponse> {
        const response = await fetch(`${API_URL}/api/v1/zones/statistics`, {
            headers: getAuthHeaders(),
        });

        const backend = await parseJsonOrThrow<BackendZonesStatisticsResponse>(
            response,
            'Erro ao buscar estatísticas das zonas'
        );

        return mapZonesStatisticsResponse(backend);
    },

    // ==========================================
    // ALERTS (Tabela: alerts)
    // ==========================================

    async getAlerts(limit = 20): Promise<Alert[]> {
        const response = await fetch(`${API_URL}/api/v1/alerts/recent?limit=${limit}`, {
            headers: getAuthHeaders(),
        });
        return parseJsonOrThrow<Alert[]>(response, 'Erro ao buscar alertas');
    },

    async deleteAlert(personId: number, timestamp: string): Promise<boolean> {
        const response = await fetch(`${API_URL}/api/v1/alerts`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
            body: JSON.stringify({ person_id: personId, timestamp }),
        });

        const payload = await parseJsonOrThrow<any>(response, 'Erro ao deletar alerta');
        // mantém compatibilidade: aceita boolean puro ou {success:true}
        return typeof payload === 'boolean' ? payload : Boolean(payload?.success ?? true);
    },

    // ==========================================
    // SYSTEM LOGS (Tabela: system_logs)
    // ==========================================

    async getSystemLogs(limit = 100): Promise<SystemLog[]> {
        const response = await fetch(`${API_URL}/api/v1/system/logs?limit=${limit}`, {
            headers: getAuthHeaders(),
        });
        return parseJsonOrThrow<SystemLog[]>(response, 'Erro ao buscar logs do sistema');
    },

    async deleteSystemLog(timestamp: string): Promise<boolean> {
        const response = await fetch(`${API_URL}/api/v1/system/logs`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
            body: JSON.stringify({ timestamp }),
        });

        const payload = await parseJsonOrThrow<any>(response, 'Erro ao deletar log');
        return typeof payload === 'boolean' ? payload : Boolean(payload?.success ?? true);
    },

    async logSystemAction(
        action: 'PAUSAR' | 'RETOMAR' | 'PARAR' | 'INICIAR',
        reason?: string
    ): Promise<void> {
        const response = await fetch(`${API_URL}/api/v1/system/action`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ action, reason }),
        });

        await parseJsonOrThrow<any>(response, 'Erro ao registrar ação do sistema');
    },

    // ==========================================
    // SETTINGS (Tabela: settings)
    // ==========================================

    async getSettings(): Promise<SystemSettings> {
        const response = await fetch(`${API_URL}/api/v1/settings`, {
            headers: getAuthHeaders(),
        });
        return parseJsonOrThrow<SystemSettings>(response, 'Erro ao buscar configurações');
    },

    async updateSetting(key: string, value: string | number | boolean): Promise<void> {
        const response = await fetch(`${API_URL}/api/v1/settings/${key}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ value }),
        });

        await parseJsonOrThrow<any>(response, `Erro ao atualizar configuração: ${key}`);
    },

    async updateSettings(settings: Partial<SystemSettings>): Promise<void> {
        const response = await fetch(`${API_URL}/api/v1/settings`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(settings),
        });

        await parseJsonOrThrow<any>(response, 'Erro ao atualizar configurações');
    },

    // ==========================================
    // ATIVIDADES (Combinado: alerts + system_logs)
    // ==========================================

    async getRecentActivities(limit = 10): Promise<Activity[]> {
        const response = await fetch(`${API_URL}/api/v1/activities/recent?limit=${limit}`, {
            headers: getAuthHeaders(),
        });
        return parseJsonOrThrow<Activity[]>(response, 'Erro ao buscar atividades');
    },
};
