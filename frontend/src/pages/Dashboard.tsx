// frontend/src/pages/Dashboard.tsx
import { useState, useEffect } from 'react';
import { Users, RefreshCw, CheckCircle2, Zap, TrendingUp, Map, Layers } from 'lucide-react';
import MainLayout from '../components/layout/MainLayout';
import { useAuthStore } from '../store/authStore';
import VideoStream from '../components/dashboard/VideoStream';
import StreamControls from '../components/dashboard/StreamControls';
import SystemInfoBanner from '../components/dashboard/SystemInfoBanner';
import { useYOLOStream } from '../hooks/useYOLOStream';

// ✅ NOVO: Imports para Zonas
import { useZones } from '../hooks/useZones';
import ZoneTable from '../components/dashboard/ZoneTable';
import ZoneDrawer from '../components/zones/ZoneDrawer';
import type { Zone, CreateZonePayload, UpdateZonePayload } from '../types/zones.types';

// ============================================================================
// StatCard Component
// ============================================================================
interface StatCardProps {
    icon: React.ElementType;
    iconColor: string;
    title: string;
    value: number | string;
    subtitle?: string;
}

function StatCard({ icon: Icon, iconColor, title, value, subtitle }: StatCardProps) {
    return (
        <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center gap-4">
                <div className={`p-3 rounded-lg ${iconColor}`}>
                    <Icon className="h-6 w-6 text-white" />
                </div>
                <div className="flex-1">
                    <p className="text-2xl font-bold text-gray-900">
                        {typeof value === 'number' ? value.toLocaleString() : value}
                    </p>
                    <p className="text-sm text-gray-600">{title}</p>
                    {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
                </div>
            </div>
        </div>
    );
}

// ============================================================================
// ✅ NOVO: ZonesSummaryCard Component (Mini Card de Resumo)
// ============================================================================
interface ZonesSummaryCardProps {
    totalZones: number;
    activeZones: number;
    onOpenMap: () => void;
}

function ZonesSummaryCard({ totalZones, activeZones, onOpenMap }: ZonesSummaryCardProps) {
    return (
        <div className="bg-white rounded-lg shadow border border-gray-200">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center gap-2">
                    <Layers className="w-5 h-5 text-blue-600" />
                    <h3 className="text-sm font-semibold text-gray-900">Zonas Configuradas</h3>
                </div>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
                {/* Stats */}
                <div className="grid grid-cols-2 gap-3">
                    <div className="text-center p-3 bg-blue-50 rounded-lg">
                        <p className="text-2xl font-bold text-blue-600">{totalZones}</p>
                        <p className="text-xs text-gray-600 mt-1">Total</p>
                    </div>
                    <div className="text-center p-3 bg-green-50 rounded-lg">
                        <p className="text-2xl font-bold text-green-600">{activeZones}</p>
                        <p className="text-xs text-gray-600 mt-1">Ativas</p>
                    </div>
                </div>

                {/* Map Button */}
                <button
                    onClick={onOpenMap}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all shadow-sm hover:shadow-md"
                >
                    <Map className="w-4 h-4" />
                    <span className="font-medium">Ver Mapa de Zonas</span>
                </button>

                {/* Info */}
                <p className="text-xs text-gray-500 text-center">
                    Clique para visualizar zonas no vídeo
                </p>
            </div>
        </div>
    );
}

// ============================================================================
// Dashboard Page
// ============================================================================
export default function Dashboard() {
    const { user } = useAuthStore();
    const { stats } = useYOLOStream(2000, true);

    // ✅ NOVO: Zonas State e Hook
    const { zones, loading: zonesLoading, fetchZones } = useZones();
    const [showZoneMap, setShowZoneMap] = useState(false);
    const [selectedZone, setSelectedZone] = useState<Zone | null>(null);

    const [dashboardStats] = useState({
        status: 'Sistema Operacional',
    });

    // ✅ Calcular status baseado no stream
    const systemStatus: 'online' | 'offline' | 'paused' | 'stopped' =
        stats?.system_status === 'running' ? 'online' :
            stats?.system_status === 'paused' ? 'paused' :
                stats?.system_status === 'stopped' ? 'stopped' : 'offline';

    // ✅ Formatar FPS atual (com fallback para fpsavg)
    const fpsCurrentDisplay = stats?.fps_current !== undefined
        ? Math.round(stats.fps_current)
        : Math.round(stats?.fpsavg || 0);

    // ✅ Formatar FPS médio (com fallback para fpsavg)
    const fpsAvgDisplay = stats?.fps_avg !== undefined
        ? Math.round(stats.fps_avg)
        : Math.round(stats?.fpsavg || 0);

    // ✅ NOVO: Calcular zonas ativas
    const activeZonesCount = zones.filter(z => z.enabled).length;

    // ✅ NOVO: Buscar zonas ao montar
    useEffect(() => {
        fetchZones(false); // false = apenas ativas
    }, [fetchZones]);

    // ✅ NOVO: Handler para abrir mapa
    const handleOpenMap = () => {
        setShowZoneMap(true);
        setSelectedZone(null);
    };

    return (
        <MainLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
                        <p className="text-gray-600 mt-1">Bem-vindo, {user?.username}!</p>
                    </div>
                    <button
                        onClick={() => fetchZones(false)}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <RefreshCw className="h-4 w-4" />
                        Atualizar
                    </button>
                </div>

                {/* ✅ System Info Banner */}
                <SystemInfoBanner
                    modelName="YOLOv8n"
                    videoSource={stats?.preset || "BALANCED"}
                    status={systemStatus}
                />

                {/* Stats Grid - 4 colunas */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <StatCard
                        icon={Users}
                        iconColor="bg-blue-500"
                        title="Detecções Hoje"
                        value={stats?.detected_count || 0}
                        subtitle="Últimas 24h"
                    />
                    <StatCard
                        icon={Zap}
                        iconColor="bg-yellow-500"
                        title="FPS Atual"
                        value={fpsCurrentDisplay}
                        subtitle="Instantâneo"
                    />
                    <StatCard
                        icon={TrendingUp}
                        iconColor="bg-green-500"
                        title="FPS Médio"
                        value={fpsAvgDisplay}
                        subtitle="Últimos 50 frames"
                    />
                    <StatCard
                        icon={CheckCircle2}
                        iconColor="bg-purple-500"
                        title={dashboardStats.status}
                        value={1}
                        subtitle="Status Sistema"
                    />
                </div>

                {/* ✅ MODIFICADO: Grid Video Stream + Controles + Zonas */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Video Stream - ocupa 2 colunas */}
                    <div className="lg:col-span-2">
                        <VideoStream />
                    </div>

                    {/* ✅ MODIFICADO: Coluna lateral com StreamControls + ZonesSummary */}
                    <div className="lg:col-span-1 space-y-6">
                        {/* Stream Controls */}
                        <StreamControls />

                        {/* ✅ NOVO: Resumo de Zonas */}
                        <ZonesSummaryCard
                            totalZones={zones.length}
                            activeZones={activeZonesCount}
                            onOpenMap={handleOpenMap}
                        />
                    </div>
                </div>

                {/* ✅ NOVO: Tabela de Zonas Monitoradas */}
                {zones.length > 0 && (
                    <ZoneTable
                        zones={zones
                            .filter(z => z.enabled)
                            .map(zone => ({
                                zone_id: zone.id,
                                zone_name: zone.name,
                                mode: zone.mode,
                                current_count: 0, // Será atualizado via WebSocket em versão futura
                                time_empty: 0,
                                time_full: 0,
                                state: 'normal' as const
                            }))}
                    />
                )}

                {/* ✅ NOVO: Mensagem quando não há zonas */}
                {zones.length === 0 && !zonesLoading && (
                    <div className="bg-white rounded-lg shadow border border-gray-200 p-12">
                        <div className="text-center space-y-3">
                            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
                                <Layers className="w-8 h-8 text-gray-400" />
                            </div>
                            <h3 className="text-lg font-semibold text-gray-900">
                                Nenhuma Zona Configurada
                            </h3>
                            <p className="text-gray-600">
                                Configure zonas para monitorar áreas específicas no vídeo
                            </p>
                            <button
                                onClick={() => window.location.href = '/zones'}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                <Layers className="w-4 h-4" />
                                Ir para Zonas
                            </button>
                        </div>
                    </div>
                )}

                {/* Atividade Recente */}
                <div className="bg-white rounded-lg shadow">
                    <div className="p-6 border-b border-gray-200">
                        <h2 className="text-lg font-semibold text-gray-900">Atividade Recente</h2>
                    </div>
                    <div className="p-6">
                        <p className="text-gray-500 text-center py-8">Nenhuma atividade recente</p>
                    </div>
                </div>
            </div>

            {/* ✅ CORRIGIDO: Modal de Visualização de Zonas */}
            {showZoneMap && (
                <ZoneDrawer
                    isOpen={true}
                    mode="view"
                    zone={selectedZone || undefined}
                    onClose={() => {
                        setShowZoneMap(false);
                        setSelectedZone(null);
                    }}
                    onSave={async (data: CreateZonePayload | UpdateZonePayload, zoneId?: number) => {
                        // View only - não permite edição
                        console.log('View mode - save disabled', { data, zoneId });
                    }}
                />
            )}
        </MainLayout>
    );
}
