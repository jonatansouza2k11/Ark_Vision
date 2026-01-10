/**
 * ============================================================================
 * zonesApi.ts - Zones API Client v3.0
 * ============================================================================
 * Cliente para consumir endpoints de zonas do backend
 * 
 * Backend: backend/api/zones.py (15 endpoints)
 * Padrão: Igual a dashboard.ts
 * ============================================================================
 */

import type {
    Zone,
    CreateZonePayload,
    UpdateZonePayload,
    PolygonValidation,
    ZoneStatistics,
    CloneZonePayload,
    BulkCreatePayload,
    BulkCreateResponse,
    BulkDeletePayload,
    Polygon
} from '../types/zones.types';

// ============================================================================
// CONFIG
// ============================================================================

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const ZONES_BASE = `${API_URL}/api/v1/zones`;

/**
 * Função auxiliar para obter headers de autenticação
 */
const getAuthHeaders = (): HeadersInit => {
    const token = localStorage.getItem('access_token');
    return {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
    };
};

/**
 * Função auxiliar para processar erros de API
 */
const handleApiError = async (response: Response): Promise<never> => {
    let errorMessage = `Erro ${response.status}: ${response.statusText}`;

    try {
        const errorData = await response.json();
        if (errorData.detail) {
            errorMessage = typeof errorData.detail === 'string'
                ? errorData.detail
                : JSON.stringify(errorData.detail);
        }
    } catch {
        // Ignore JSON parse errors
    }

    throw new Error(errorMessage);
};

// ============================================================================
// ZONES API CLIENT
// ============================================================================

export const zonesApi = {
    // ==========================================================================
    // CRUD BÁSICO (v2.0 Compatible - 5 endpoints)
    // ==========================================================================

    /**
     * POST /api/v1/zones - Criar nova zona
     * @param zone - Dados da zona a criar
     * @returns Zona criada
     */
    async createZone(zone: CreateZonePayload): Promise<Zone> {
        const response = await fetch(ZONES_BASE, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(zone),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    /**
     * GET /api/v1/zones - Listar todas as zonas
     * @param includeDisabled - Incluir zonas desabilitadas
     * @returns Lista de zonas
     */
    async listZones(includeDisabled = false): Promise<Zone[]> {
        const url = new URL(ZONES_BASE);
        if (includeDisabled) {
            url.searchParams.set('include_disabled', 'true');
        }

        const response = await fetch(url.toString(), {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    /**
     * GET /api/v1/zones/{zone_id} - Obter zona específica
     * @param zoneId - ID da zona
     * @returns Zona encontrada
     */
    async getZone(zoneId: number): Promise<Zone> {
        const response = await fetch(`${ZONES_BASE}/${zoneId}`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    /**
     * PUT /api/v1/zones/{zone_id} - Atualizar zona
     * @param zoneId - ID da zona
     * @param updates - Campos a atualizar
     * @returns Zona atualizada
     */
    async updateZone(zoneId: number, updates: UpdateZonePayload): Promise<Zone> {
        const response = await fetch(`${ZONES_BASE}/${zoneId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(updates),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    /**
     * DELETE /api/v1/zones/{zone_id} - Deletar zona (soft delete)
     * @param zoneId - ID da zona
     */
    async deleteZone(zoneId: number): Promise<void> {
        const response = await fetch(`${ZONES_BASE}/${zoneId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            await handleApiError(response);
        }
    },

    // ==========================================================================
    // OPERAÇÕES EM LOTE (v3.0 - 2 endpoints)
    // ==========================================================================

    /**
     * POST /api/v1/zones/bulk/create - Criar múltiplas zonas
     * @param payload - Lista de zonas a criar
     * @returns Resultado da criação em lote
     */
    async bulkCreateZones(payload: BulkCreatePayload): Promise<BulkCreateResponse> {
        const response = await fetch(`${ZONES_BASE}/bulk/create`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    /**
     * POST /api/v1/zones/bulk/delete - Deletar múltiplas zonas
     * @param payload - IDs das zonas a deletar
     * @returns Mensagem de sucesso
     */
    async bulkDeleteZones(payload: BulkDeletePayload): Promise<{ message: string }> {
        const response = await fetch(`${ZONES_BASE}/bulk/delete`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    // ==========================================================================
    // VALIDAÇÃO & UTILITÁRIOS (v3.0 - 3 endpoints)
    // ==========================================================================

    /**
     * POST /api/v1/zones/validate - Validar polígono
     * @param points - Pontos do polígono
     * @returns Resultado da validação
     */
    async validatePolygon(points: Polygon): Promise<PolygonValidation> {
        const response = await fetch(`${ZONES_BASE}/validate`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ points }),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    /**
     * POST /api/v1/zones/{zone_id}/clone - Clonar zona
     * @param zoneId - ID da zona a clonar
     * @param payload - Configurações de clonagem
     * @returns Zona clonada
     */
    async cloneZone(zoneId: number, payload: CloneZonePayload): Promise<Zone> {
        const response = await fetch(`${ZONES_BASE}/${zoneId}/clone`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    /**
     * GET /api/v1/zones/statistics - Estatísticas de zonas
     * @returns Estatísticas gerais
     */
    async getStatistics(): Promise<ZoneStatistics> {
        const response = await fetch(`${ZONES_BASE}/statistics`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    // ==========================================================================
    // IMPORT/EXPORT (v3.0 - 2 endpoints)
    // ==========================================================================

    /**
     * GET /api/v1/zones/export - Exportar zonas em JSON
     * @returns JSON com todas as zonas
     */
    async exportZones(): Promise<Zone[]> {
        const response = await fetch(`${ZONES_BASE}/export`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    /**
     * POST /api/v1/zones/import - Importar zonas de arquivo JSON
     * @param file - Arquivo JSON com zonas
     * @returns Mensagem de sucesso
     */
    async importZones(file: File): Promise<{ message: string; imported: number }> {
        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('access_token');
        const headers: HeadersInit = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${ZONES_BASE}/import`, {
            method: 'POST',
            headers,
            body: formData,
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    // ==========================================================================
    // TEMPLATES (v3.0 - 2 endpoints)
    // ==========================================================================

    /**
     * GET /api/v1/zones/templates - Listar templates disponíveis
     * @returns Lista de templates
     */
    async listTemplates(): Promise<Array<{
        id: string;
        name: string;
        description: string;
        default_settings: Record<string, any>;
    }>> {
        const response = await fetch(`${ZONES_BASE}/templates`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    /**
     * POST /api/v1/zones/templates/{template_name} - Criar zona de template
     * @param templateName - Nome do template (parking_spot, entrance, restricted_area)
     * @param zoneName - Nome da nova zona
     * @param points - Pontos do polígono
     * @returns Zona criada
     */
    async createFromTemplate(
        templateName: string,
        zoneName: string,
        points: Polygon
    ): Promise<Zone> {
        const response = await fetch(`${ZONES_BASE}/templates/${templateName}`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ zone_name: zoneName, points }),
        });

        if (!response.ok) {
            await handleApiError(response);
        }

        return response.json();
    },

    // ==========================================================================
    // HELPERS & CONVENIENCE METHODS
    // ==========================================================================

    /**
     * Habilitar/desabilitar zona
     * @param zoneId - ID da zona
     * @param enabled - Novo estado
     * @returns Zona atualizada
     */
    async toggleZone(zoneId: number, enabled: boolean): Promise<Zone> {
        return this.updateZone(zoneId, { enabled });
    },

    /**
     * Ativar/desativar zona
     * @param zoneId - ID da zona
     * @param active - Novo estado
     * @returns Zona atualizada
     */
    async setZoneActive(zoneId: number, active: boolean): Promise<Zone> {
        return this.updateZone(zoneId, { active });
    },

    /**
     * Atualizar apenas os pontos da zona
     * @param zoneId - ID da zona
     * @param points - Novos pontos
     * @returns Zona atualizada
     */
    async updateZonePoints(zoneId: number, points: Polygon): Promise<Zone> {
        return this.updateZone(zoneId, { points });
    },

    /**
     * Obter apenas zonas ativas
     * @returns Zonas ativas e habilitadas
     */
    async getActiveZones(): Promise<Zone[]> {
        const zones = await this.listZones(false);
        return zones.filter(zone => zone.enabled && zone.active);
    },

    /**
     * Deletar múltiplas zonas por IDs
     * @param zoneIds - Lista de IDs
     */
    async deleteMultipleZones(zoneIds: number[]): Promise<void> {
        await this.bulkDeleteZones({ zone_ids: zoneIds });
    },

    /**
     * Download de zonas como arquivo JSON
     */
    async downloadZonesAsFile(): Promise<void> {
        const zones = await this.exportZones();
        const blob = new Blob([JSON.stringify(zones, null, 2)], {
            type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `zones-export-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },
};

// ============================================================================
// DEFAULT EXPORT
// ============================================================================

export default zonesApi;
