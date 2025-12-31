// src/api/dashboard.ts
import {
    DashboardData,
    SystemInfo,
    DashboardStats,
    Alert,
    SystemLog,
    SystemSettings,
    Activity,
} from '../types/dashboard';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
    };
};

export const dashboardApi = {
    // ==========================================
    // DASHBOARD PRINCIPAL
    // ==========================================

    // Buscar todos os dados do dashboard de uma vez
    async getDashboardData(): Promise<DashboardData> {
        const response = await fetch(`${API_URL}/api/v1/dashboard`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            throw new Error('Erro ao buscar dados do dashboard');
        }

        return response.json();
    },

    // Buscar informações do sistema
    async getSystemInfo(): Promise<SystemInfo> {
        const response = await fetch(`${API_URL}/api/v1/system/info`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            throw new Error('Erro ao buscar informações do sistema');
        }

        return response.json();
    },

    // Buscar estatísticas em tempo real
    async getStats(): Promise<DashboardStats> {
        const response = await fetch(`${API_URL}/api/v1/stats`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            throw new Error('Erro ao buscar estatísticas');
        }

        return response.json();
    },

    // ==========================================
    // ALERTS (Tabela: alerts)
    // ==========================================

    // Buscar alertas recentes
    async getAlerts(limit = 20): Promise<Alert[]> {
        const response = await fetch(
            `${API_URL}/api/v1/alerts/recent?limit=${limit}`,
            {
                headers: getAuthHeaders(),
            }
        );

        if (!response.ok) {
            throw new Error('Erro ao buscar alertas');
        }

        return response.json();
    },

    // Deletar alerta específico
    async deleteAlert(personId: number, timestamp: string): Promise<boolean> {
        const response = await fetch(`${API_URL}/api/v1/alerts`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
            body: JSON.stringify({ person_id: personId, timestamp }),
        });

        if (!response.ok) {
            throw new Error('Erro ao deletar alerta');
        }

        return response.json();
    },

    // ==========================================
    // SYSTEM LOGS (Tabela: system_logs)
    // ==========================================

    // Buscar logs do sistema
    async getSystemLogs(limit = 100): Promise<SystemLog[]> {
        const response = await fetch(
            `${API_URL}/api/v1/system/logs?limit=${limit}`,
            {
                headers: getAuthHeaders(),
            }
        );

        if (!response.ok) {
            throw new Error('Erro ao buscar logs do sistema');
        }

        return response.json();
    },

    // Deletar log do sistema
    async deleteSystemLog(timestamp: string): Promise<boolean> {
        const response = await fetch(`${API_URL}/api/v1/system/logs`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
            body: JSON.stringify({ timestamp }),
        });

        if (!response.ok) {
            throw new Error('Erro ao deletar log');
        }

        return response.json();
    },

    // Criar log de ação do sistema
    async logSystemAction(
        action: 'PAUSAR' | 'RETOMAR' | 'PARAR' | 'INICIAR',
        reason?: string
    ): Promise<void> {
        const response = await fetch(`${API_URL}/api/v1/system/action`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ action, reason }),
        });

        if (!response.ok) {
            throw new Error('Erro ao registrar ação do sistema');
        }
    },

    // ==========================================
    // SETTINGS (Tabela: settings)
    // ==========================================

    // Buscar todas as configurações
    async getSettings(): Promise<SystemSettings> {
        const response = await fetch(`${API_URL}/api/v1/settings`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            throw new Error('Erro ao buscar configurações');
        }

        return response.json();
    },

    // Atualizar configuração específica
    async updateSetting(key: string, value: string | number | boolean): Promise<void> {
        const response = await fetch(`${API_URL}/api/v1/settings/${key}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ value }),
        });

        if (!response.ok) {
            throw new Error(`Erro ao atualizar configuração: ${key}`);
        }
    },

    // Atualizar múltiplas configurações de uma vez
    async updateSettings(settings: Partial<SystemSettings>): Promise<void> {
        const response = await fetch(`${API_URL}/api/v1/settings`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(settings),
        });

        if (!response.ok) {
            throw new Error('Erro ao atualizar configurações');
        }
    },

    // ==========================================
    // ATIVIDADES (Combinado: alerts + system_logs)
    // ==========================================

    // Buscar atividades recentes (alertas + logs)
    async getRecentActivities(limit = 10): Promise<Activity[]> {
        const response = await fetch(
            `${API_URL}/api/v1/activities/recent?limit=${limit}`,
            {
                headers: getAuthHeaders(),
            }
        );

        if (!response.ok) {
            throw new Error('Erro ao buscar atividades');
        }

        return response.json();
    },
};
