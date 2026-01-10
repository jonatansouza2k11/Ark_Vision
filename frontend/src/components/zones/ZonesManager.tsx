/**
 * ============================================================================
 * ZonesManager.tsx - Zones Management Page v3.0
 * ============================================================================
 * Componente principal que integra toda a funcionalidade de zonas
 * 
 * Features:
 * - Gerenciamento completo de zonas (CRUD)
 * - Estatísticas em tempo real
 * - Integração ZoneDrawer + ZonesList + useZones
 * - Export/Import de zonas
 * - Bulk operations
 * - Notificações Toast
 * ============================================================================
 */

import { useState, useEffect } from 'react';
import {
    Plus,
    Download,
    Upload,
    RefreshCw,
    BarChart3,
    Trash2,
    Copy
} from 'lucide-react';
import { useZones } from '../../hooks/useZones';
import { useToast } from '../../hooks/useToast';
import ZoneDrawer from './ZoneDrawer';
import ZonesList from './ZonesList';
import { zonesApi } from '../../api/zonesApi';
import type {
    Zone,
    CreateZonePayload,
    UpdateZonePayload
} from '../../types/zones.types';

// ============================================================================
// STATISTICS CARD
// ============================================================================

interface StatCardProps {
    label: string;
    value: number | string;
    icon: React.ReactNode;
    color: string;
}

function StatCard({ label, value, icon, color }: StatCardProps) {
    return (
        <div className="bg-white rounded-xl border-2 border-gray-200 p-4">
            <div className="flex items-center gap-3">
                <div
                    className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: `${color}15` }}
                >
                    <div style={{ color }}>{icon}</div>
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-2xl font-bold text-gray-900">{value}</p>
                    <p className="text-sm text-gray-600 truncate">{label}</p>
                </div>
            </div>
        </div>
    );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function ZonesManager() {
    // ==========================================================================
    // HOOKS
    // ==========================================================================

    const {
        zones,
        loading,
        error,
        fetchZones,      // ← ADICIONAR
        createZone,
        updateZone,
        deleteZone,
        toggleZone,
        bulkDelete,
        statistics,
        loadStatistics,
        refresh
    } = useZones();

    const { success, error: showError, info } = useToast();

    // ==========================================================================
    // STATE
    // ==========================================================================

    const [drawerState, setDrawerState] = useState<{
        isOpen: boolean;
        mode: 'create' | 'edit' | 'view';
        zone: Zone | null;
    }>({
        isOpen: false,
        mode: 'create',
        zone: null
    });

    const [selectedZones, setSelectedZones] = useState<number[]>([]);
    const [isRefreshing, setIsRefreshing] = useState(false);

    // ==========================================================================
    // EFFECTS
    // ==========================================================================

    /**
     * ✅ CORRIGIDO: Carrega zonas E estatísticas na montagem
     */
    useEffect(() => {
        fetchZones();      // ← ADICIONAR
        loadStatistics();

        // Refresh estatísticas a cada 30 segundos
        const interval = setInterval(() => {
            loadStatistics();
        }, 30000);

        return () => clearInterval(interval);
    }, [fetchZones, loadStatistics]); // ← ADICIONAR fetchZones

    // ==========================================================================
    // DRAWER HANDLERS
    // ==========================================================================

    const handleOpenCreateDrawer = () => {
        setDrawerState({
            isOpen: true,
            mode: 'create',
            zone: null
        });
    };

    const handleOpenEditDrawer = (zone: Zone) => {
        setDrawerState({
            isOpen: true,
            mode: 'edit',
            zone
        });
    };

    const handleOpenViewDrawer = (zone: Zone) => {
        setDrawerState({
            isOpen: true,
            mode: 'view',
            zone
        });
    };

    const handleCloseDrawer = () => {
        setDrawerState({
            isOpen: false,
            mode: 'create',
            zone: null
        });
    };

    /**
     * ✅ CORRIGIDO: Adiciona feedback de sucesso/erro
     */
    const handleSaveZone = async (
        data: CreateZonePayload | UpdateZonePayload,
        zoneId?: number
    ) => {
        try {
            if (drawerState.mode === 'create') {
                const result = await createZone(data as CreateZonePayload);
                if (result) {
                    success('Zona criada com sucesso!');
                    handleCloseDrawer();
                } else {
                    showError('Erro ao criar zona');
                }
            } else if (drawerState.mode === 'edit' && zoneId) {
                const result = await updateZone(zoneId, data as UpdateZonePayload);
                if (result) {
                    success('Zona atualizada com sucesso!');
                    handleCloseDrawer();
                } else {
                    showError('Erro ao atualizar zona');
                }
            }
        } catch (err) {
            showError(err instanceof Error ? err.message : 'Erro ao salvar zona');
        }
    };

    // ==========================================================================
    // ZONE ACTIONS
    // ==========================================================================

    const handleDeleteZone = async (zoneId: number) => {
        const confirmed = window.confirm('Tem certeza que deseja deletar esta zona?');
        if (!confirmed) return;

        const result = await deleteZone(zoneId);
        if (result) {
            success('Zona deletada com sucesso!');
        } else {
            showError('Erro ao deletar zona');
        }
    };

    const handleToggleZone = async (zoneId: number, enabled: boolean) => {
        const result = await toggleZone(zoneId, enabled);
        if (result) {
            success(enabled ? 'Zona ativada!' : 'Zona desativada!');
        } else {
            showError('Erro ao alterar status da zona');
        }
    };

    // ==========================================================================
    // BULK OPERATIONS
    // ==========================================================================

    const handleBulkDelete = async () => {
        if (selectedZones.length === 0) {
            info('Nenhuma zona selecionada');
            return;
        }

        const confirmed = window.confirm(
            `Deletar ${selectedZones.length} zona(s) selecionada(s)?`
        );

        if (!confirmed) return;

        const result = await bulkDelete(selectedZones);
        if (result) {
            success(`${selectedZones.length} zona(s) deletada(s) com sucesso!`);
            setSelectedZones([]);
        } else {
            showError('Erro ao deletar zonas');
        }
    };

    // ==========================================================================
    // IMPORT/EXPORT
    // ==========================================================================

    const handleExport = async () => {
        try {
            await zonesApi.downloadZonesAsFile();
            success('Zonas exportadas com sucesso!');
        } catch (err) {
            showError('Erro ao exportar zonas');
        }
    };

    const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        try {
            const result = await zonesApi.importZones(file);
            success(`${result.imported} zona(s) importada(s) com sucesso!`);
            await refresh();
        } catch (err) {
            showError('Erro ao importar zonas');
        }

        // Reset input
        e.target.value = '';
    };

    // ==========================================================================
    // REFRESH
    // ==========================================================================

    const handleRefresh = async () => {
        setIsRefreshing(true);
        try {
            await refresh();
            info('Zonas atualizadas');
        } finally {
            setIsRefreshing(false);
        }
    };

    // ==========================================================================
    // RENDER
    // ==========================================================================

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">
                                Gerenciamento de Zonas
                            </h1>
                            <p className="text-gray-600 mt-1">
                                Configure e monitore zonas de detecção do sistema
                            </p>
                        </div>

                        <div className="flex items-center gap-3">
                            {/* Refresh Button */}
                            <button
                                onClick={handleRefresh}
                                disabled={isRefreshing}
                                className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium disabled:opacity-50"
                                title="Atualizar"
                            >
                                <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
                                <span className="hidden sm:inline">Atualizar</span>
                            </button>

                            {/* Export Button */}
                            <button
                                onClick={handleExport}
                                className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                                title="Exportar"
                            >
                                <Download className="w-5 h-5" />
                                <span className="hidden sm:inline">Exportar</span>
                            </button>

                            {/* Import Button */}
                            <label className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium cursor-pointer">
                                <Upload className="w-5 h-5" />
                                <span className="hidden sm:inline">Importar</span>
                                <input
                                    type="file"
                                    accept=".json"
                                    onChange={handleImport}
                                    className="hidden"
                                />
                            </label>

                            {/* Create Button */}
                            <button
                                onClick={handleOpenCreateDrawer}
                                className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-lg shadow-blue-600/30"
                            >
                                <Plus className="w-5 h-5" />
                                Nova Zona
                            </button>
                        </div>
                    </div>

                    {/* Statistics */}
                    {statistics && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                            <StatCard
                                label="Total de Zonas"
                                value={statistics.total_zones}
                                icon={<BarChart3 className="w-6 h-6" />}
                                color="#3B82F6"
                            />
                            <StatCard
                                label="Zonas Ativas"
                                value={statistics.enabled_zones}
                                icon={
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                }
                                color="#10B981"
                            />
                            <StatCard
                                label="Zonas Inativas"
                                value={statistics.disabled_zones}
                                icon={
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                }
                                color="#6B7280"
                            />
                            <StatCard
                                label="Área Média"
                                value={statistics.average_area ? `${statistics.average_area.toFixed(0)}px²` : 'N/A'}
                                icon={
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1v-3z" />
                                    </svg>
                                }
                                color="#8B5CF6"
                            />
                        </div>
                    )}
                </div>

                {/* Error State */}
                {error && (
                    <div className="mb-6 bg-red-50 border-2 border-red-200 rounded-xl p-4">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
                                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </div>
                            <div className="flex-1">
                                <h3 className="font-semibold text-red-900">Erro ao carregar zonas</h3>
                                <p className="text-sm text-red-700">{error}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Bulk Actions Bar */}
                {selectedZones.length > 0 && (
                    <div className="mb-6 bg-blue-50 border-2 border-blue-200 rounded-xl p-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                                    <Copy className="w-5 h-5 text-blue-600" />
                                </div>
                                <div>
                                    <p className="font-semibold text-blue-900">
                                        {selectedZones.length} zona(s) selecionada(s)
                                    </p>
                                    <p className="text-sm text-blue-700">
                                        Escolha uma ação para aplicar
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setSelectedZones([])}
                                    className="px-4 py-2 bg-white border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 transition-colors text-sm font-medium"
                                >
                                    Cancelar
                                </button>
                                <button
                                    onClick={handleBulkDelete}
                                    className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    Deletar Selecionadas
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Zones List */}
                <ZonesList
                    zones={zones}
                    loading={loading}
                    onEdit={handleOpenEditDrawer}
                    onDelete={handleDeleteZone}
                    onToggle={handleToggleZone}
                    onView={handleOpenViewDrawer}
                    selectedZones={selectedZones}
                    onSelectionChange={setSelectedZones}
                />

                {/* Zone Drawer */}
                <ZoneDrawer
                    isOpen={drawerState.isOpen}
                    mode={drawerState.mode}
                    zone={drawerState.zone}
                    onClose={handleCloseDrawer}
                    onSave={handleSaveZone}
                    streamUrl="http://localhost:8000/video_feed"
                />
            </div>
        </div>
    );
}
