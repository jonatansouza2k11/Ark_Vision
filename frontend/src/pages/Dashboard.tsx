// frontend/src/pages/Dashboard.tsx

import { useState, useEffect } from 'react';
import {
    Users,
    RefreshCw,
    CheckCircle2,
    Zap,
    TrendingUp,
    Map,
    Layers,
    Camera,
    Video,
} from 'lucide-react';

import MainLayout from '../components/layout/MainLayout';
import { useAuthStore } from '../store/authStore';
import VideoStream from '../components/dashboard/VideoStream';
import StreamControls from '../components/dashboard/StreamControls';
//import SystemInfoBanner from '../components/dashboard/SystemInfoBanner';
import { useYOLOStream } from '../hooks/useYOLOStream';
import { streamAPI, type CameraRuntimeStatus } from '../services/streamApi';

// ✅ Zonas
import { useZones } from '../hooks/useZones';
import ZoneTable, { type ZoneTableItem } from '../components/dashboard/ZoneTable';
import ZoneDrawer from '../components/zones/ZoneDrawer';
import type { Zone, CreateZonePayload, UpdateZonePayload } from '../types/zones.types';

// ✅ Câmeras
import { useCameras } from '../hooks/useCameras';

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
// ZonesSummaryCard Component
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

                {/* Button */}
                <button
                    onClick={onOpenMap}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all shadow-sm hover:shadow-md"
                >
                    <Map className="w-4 h-4" />
                    <span className="font-medium">Mapear Zonas</span>
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
// CamerasSummaryCard Component
// ============================================================================

interface CamerasSummaryCardProps {
    totalCameras: number;
    activeCameras: number;
    onManageCameras: () => void;
}

function CamerasSummaryCard({
    totalCameras,
    activeCameras,
    onManageCameras,
}: CamerasSummaryCardProps) {
    return (
        <div className="bg-white rounded-lg shadow border border-gray-200">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center gap-2">
                    <Camera className="w-5 h-5 text-purple-600" />
                    <h3 className="text-sm font-semibold text-gray-900">Câmeras Configuradas</h3>
                </div>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
                {/* Stats */}
                <div className="grid grid-cols-2 gap-3">
                    <div className="text-center p-3 bg-purple-50 rounded-lg">
                        <p className="text-2xl font-bold text-purple-600">{totalCameras}</p>
                        <p className="text-xs text-gray-600 mt-1">Total</p>
                    </div>
                    <div className="text-center p-3 bg-green-50 rounded-lg">
                        <p className="text-2xl font-bold text-green-600">{activeCameras}</p>
                        <p className="text-xs text-gray-600 mt-1">Ativas</p>
                    </div>
                </div>

                {/* Button */}
                <button
                    onClick={onManageCameras}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-700 hover:to-purple-800 transition-all shadow-sm hover:shadow-md"
                >
                    <Camera className="w-4 h-4" />
                    <span className="font-medium">Gerenciar Câmeras</span>
                </button>

                {/* Info */}
                <p className="text-xs text-gray-500 text-center">
                    Adicione e configure câmeras de vídeo
                </p>
            </div>
        </div>
    );
}

// ============================================================================
// Normalização de estado do backend -> estado do ZoneTable
// ============================================================================
function normalizeState(backendState: string | undefined | null): ZoneTableItem['state'] {
    if (!backendState) return 'normal';

    const key = backendState.toUpperCase().replace(/[\s]/g, '');

    const stateMap: Record<string, ZoneTableItem['state']> = {
        NORMAL: 'normal',
        EMPTY: 'empty',
        EMPTYPENDING: 'emptypending',
        OCCUPIED: 'normal',
        FULL: 'critical',
        FULLPENDING: 'fullpending',
        WARNING: 'warning',
        CRITICAL: 'critical',
        ALERT: 'alert',
        PENDING: 'pending',
        DETECTED: 'alert',
        IDLE: 'normal',
        TRACKING: 'normal',

        // Estados específicos de fila
        QUEUENORMAL: 'normal',
        QUEUEWARNING: 'warning',
        QUEUECRITICAL: 'critical',
    };

    return stateMap[key] ?? 'normal';
  }

// ============================================================================
// Dashboard Page
// ============================================================================

export default function Dashboard() {
    const user = useAuthStore((s) => s.user);

    // ✅ usar destructuring do hook (UseYOLOStreamReturn)
    const {
        stats,
        error: streamError,
    } = useYOLOStream(2000, true);

    // Zonas
    const {
        zones,
        loading: zonesLoading,
        fetchZones,
        createZone,
    } = useZones();

    // Drawer de zonas
    const [showZoneMap, setShowZoneMap] = useState(false);
    const [selectedZone, setSelectedZone] = useState<Zone | null>(null);

    // Métricas de zonas em tempo real (payload da API em snake_case)
    const [zoneMetrics, setZoneMetrics] = useState<any[]>([]);

    // Câmeras (lista de configuração) – hook retorna objeto
    const {
        cameras,
    } = useCameras();

    // Câmeras disponíveis no VisionSystem (runtime)
    const [availableCameras, setAvailableCameras] = useState<CameraRuntimeStatus[]>([]);
    const [selectedCameraId, setSelectedCameraId] = useState<number | null>(null);

    // Status do sistema com base no stream (mapeia system_status -> banner)
    const systemStatus: 'online' | 'offline' | 'paused' | 'stopped' = !stats
        ? 'offline'
        : stats.system_status === 'running'
            ? 'online'
            : stats.system_status === 'paused'
                ? 'paused'
                : stats.system_status === 'stopped'
                    ? 'stopped'
                    : 'offline';

    // FPS atual com fallbacks (fps_current -> fps_avg -> fpsavg)
    const fpsCurrentDisplay = stats
        ? Math.round(
            (stats.fps_current ??
                stats.fps_avg ??
                stats.fpsavg ??
                0),
        )
        : 0;

    // FPS médio (fps_avg -> fpsavg -> fps_current)
    const fpsAvgDisplay = stats
        ? Math.round(
            (stats.fps_avg ??
                stats.fpsavg ??
                stats.fps_current ??
                0),
        )
        : 0;

    // Detecções (campo oficial em YOLOStats)
    const detectedToday = stats?.detected_count ?? 0;

    // Zonas e câmeras ativas
    const activeZonesCount = zones.filter((z) => z.enabled).length;
    const activeCamerasCount = cameras.filter((c) => c.enabled).length;

    // ==========================================================================
    // Efeitos de carregamento
    // ==========================================================================

    // Buscar zonas ao montar
    useEffect(() => {
        fetchZones(false);
    }, [fetchZones]);

    // Carregar câmeras disponíveis no VisionSystem
    useEffect(() => {
        const loadAvailableCameras = async () => {
            try {
                // Recarrega do backend para pegar zonas/câmeras atualizadas
                await streamAPI.reloadCameras().catch((err: unknown) => {
                    console.warn('Failed to reload cameras', err);
                });

                const response = await streamAPI.getCameras();
                setAvailableCameras(response.data);

                // Seleciona primeira câmera por padrão
                if (!selectedCameraId && response.data.length > 0) {
                    setSelectedCameraId(response.data[0].camera_id);
                }
            } catch (error) {
                console.error('Error loading cameras', error);
            }
        };

        loadAvailableCameras();

        // Recarrega quando a página ganha foco
        const handleFocus = () => {
            loadAvailableCameras();
        };

        const handleVisibility = () => {
            if (!document.hidden) {
                loadAvailableCameras();
            }
        };

        window.addEventListener('focus', handleFocus);
        document.addEventListener('visibilitychange', handleVisibility);

        return () => {
            window.removeEventListener('focus', handleFocus);
            document.removeEventListener('visibilitychange', handleVisibility);
        };
    }, [selectedCameraId]);

    // Carregar métricas de zonas periodicamente
    useEffect(() => {
        if (!selectedCameraId) return;

        const loadZoneMetrics = async () => {
            try {
                const token = localStorage.getItem('access_token');
                const response = await fetch(
                    `http://localhost:8000/api/v1/stream/zone_metrics/${selectedCameraId}`,
                    {
                        headers: {
                            Authorization: token ? `Bearer ${token}` : '',
                        },
                    },
                );

                if (response.ok) {
                    const data = await response.json();
                    setZoneMetrics(data ?? []);
                } else {
                    console.warn('Falha ao carregar métricas de zona', response.status);
                }
            } catch (error) {
                console.error('Error loading zone metrics', error);
            }
        };

        loadZoneMetrics();
        const interval = setInterval(loadZoneMetrics, 2000);
        return () => clearInterval(interval);
    }, [selectedCameraId]);

    // ==========================================================================
    // Handlers
    // ==========================================================================

    const handleOpenMap = () => {
        setShowZoneMap(true);
        setSelectedZone(null);
    };

    const handleManageCameras = () => {
        window.location.href = '/cameras';
    };

    const handleManageZones = () => {
        window.location.href = '/zones';
    };

    const handleRefreshAll = () => {
        fetchZones(false);
        // força reload de câmeras/runtime
        (async () => {
            try {
                await streamAPI.reloadCameras();
                const response = await streamAPI.getCameras();
                setAvailableCameras(response.data);
            } catch (err) {
                console.error('Erro ao recarregar câmeras', err);
            }
        })();
    };

    // ==========================================================================
    // Mapeamento das métricas da API -> ZoneTableItem[]
    // ==========================================================================

    const zoneTableData: ZoneTableItem[] = zones
        .filter((z) => z.enabled)
        .map((zone) => {
            // Métricas em snake_case vindas da API
            const metrics = zoneMetrics.find(
                (m) => m.zone_id === zone.id || m.zoneid === zone.id,
            );

            // if (zone.mode === 'queue') {
            //   console.log('[QUEUE METRICS]', {
            //     zoneId: zone.id,
            //     zoneName: zone.name,
            //     metrics,
            //   });
            // }

            // Usa state ou status, com fallback para 'normal'
            const backendState: string =
                (metrics?.state as string) ?? (metrics?.status as string) ?? 'normal';
            const normalizedState = normalizeState(backendState);
            const hasAlert = metrics?.alert === true;

            // Objeto base compatível com o ZoneTableItem atual
            const base: ZoneTableItem = {
                // Campos exigidos por ZoneTableItem
                zoneid: zone.id,
                zonename: zone.name,
                mode: zone.mode,

                currentcount: metrics?.current_count ?? metrics?.currentcount ?? 0,
                timeempty: metrics?.time_empty ?? metrics?.timeempty ?? 0,
                timefull: metrics?.time_full ?? metrics?.timefull ?? 0,

                state: hasAlert ? 'alert' : normalizedState,

                maxcapacity: metrics?.max_capacity ?? metrics?.maxcapacity,
                cameraid: zone.camera_id ?? null,
                fulltimeout: metrics?.full_timeout ?? metrics?.fulltimeout,

                countin: metrics?.count_in ?? metrics?.countin,
                countout: metrics?.count_out ?? metrics?.countout,
                countdirection: metrics?.count_direction ?? metrics?.countdirection,

                alert: metrics?.alert ?? false,
                alertmessage:
                    metrics?.alert_message ?? metrics?.alertmessage ?? null,
                resetinterval: metrics?.reset_interval ?? metrics?.resetinterval,
                lastreset: metrics?.last_reset ?? metrics?.lastreset ?? null,

                // Inicializa KPIs de fila como indefinidos
                queue_length: undefined,
                avg_wait_time: undefined,
                max_wait_time: undefined,
                abandon_count: undefined,
                abandon_avg_wait: undefined,
                last_abandon_wait: undefined,
            };

            // Métricas específicas de FILA (queue) – todas as quantidades disponíveis
            if (zone.mode === 'queue') {
                // Comprimento da fila
                const queueLenRaw =
                    metrics?.queue_length ??
                    metrics?.queuelength ?? // legado
                    metrics?.queueLength ?? // camelCase eventual
                    metrics?.metadata?.queue_length ??
                    metrics?.metadata?.queuelength ??
                    base.currentcount;

                base.queue_length =
                    queueLenRaw !== undefined && queueLenRaw !== null
                        ? Number(queueLenRaw)
                        : base.currentcount;

                // Garantir que venham como number (formatTime exige número finito)
                const avgWaitRaw =
                    metrics?.avg_wait_time ??
                    metrics?.avgwaittime ?? // legado
                    metrics?.avgWaitTime ?? // camelCase eventual
                    metrics?.metadata?.avg_wait_time ??
                    metrics?.metadata?.avgwaittime;

                const maxWaitRaw =
                    metrics?.max_wait_time ??
                    metrics?.maxwaittime ?? // legado
                    metrics?.maxWaitTime ?? // camelCase eventual
                    metrics?.metadata?.max_wait_time ??
                    metrics?.metadata?.maxwaittime;

                const abandonCountRaw =
                    metrics?.abandon_count ??
                    metrics?.abandoncount ?? // legado
                    metrics?.abandonCount ??
                    metrics?.metadata?.abandon_count ??
                    metrics?.metadata?.abandoncount;

                const abandonAvgRaw =
                    metrics?.abandon_avg_wait ??
                    metrics?.abandonavgwait ?? // legado
                    metrics?.abandonAvgWait ??
                    metrics?.metadata?.abandon_avg_wait ??
                    metrics?.metadata?.abandonavgwait;

                const lastAbandonRaw =
                    metrics?.last_abandon_wait ??
                    metrics?.lastabandonwait ?? // legado
                    metrics?.lastAbandonWait ??
                    metrics?.metadata?.last_abandon_wait ??
                    metrics?.metadata?.lastabandonwait;

                base.avg_wait_time =
                    avgWaitRaw !== undefined && avgWaitRaw !== null
                        ? Number(avgWaitRaw)
                        : undefined;

                base.max_wait_time =
                    maxWaitRaw !== undefined && maxWaitRaw !== null
                        ? Number(maxWaitRaw)
                        : undefined;

                base.abandon_count =
                    abandonCountRaw !== undefined && abandonCountRaw !== null
                        ? Number(abandonCountRaw)
                        : undefined;

                base.abandon_avg_wait =
                    abandonAvgRaw !== undefined && abandonAvgRaw !== null
                        ? Number(abandonAvgRaw)
                        : undefined;

                base.last_abandon_wait =
                    lastAbandonRaw !== undefined && lastAbandonRaw !== null
                        ? Number(lastAbandonRaw)
                        : undefined;
            }

            return base;
        });

    // ==========================================================================
    // Render
    // ==========================================================================

    return (
        <MainLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
                        <p className="text-gray-600 mt-1">
                            Bem-vindo, {user?.username}!
                        </p>
                    </div>

                    <button
                        onClick={handleRefreshAll}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <RefreshCw className="h-4 w-4" />
                        Atualizar
                    </button>
                </div>

                {/* System Info */}
                {/*
                <SystemInfoBanner
                    modelName="YOLOv8n"
                    videoSource={stats?.preset ?? 'BALANCED'}
                    status={systemStatus}
                />
                */}

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <StatCard
                        icon={Users}
                        iconColor="bg-blue-500"
                        title="Detecções Hoje"
                        value={detectedToday}
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
                        title="Status Sistema"
                        value={systemStatus.toUpperCase()}
                        subtitle="Baseado no stream"
                    />
                </div>

                {/* Grid Video + Sidebar */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Vídeo - 2 colunas */}
                    <div className="lg:col-span-2 space-y-4">
                        {/* Seletor de Câmera */}
                        <div className="bg-white rounded-lg shadow border border-gray-200 p-4">
                            <div className="flex items-center gap-3 mb-3">
                                <Video className="w-5 h-5 text-gray-500" />
                                <label className="text-sm font-medium text-gray-700">
                                    Câmeras
                                </label>
                            </div>

                            <select
                                value={selectedCameraId ?? ''}
                                onChange={(e) =>
                                    setSelectedCameraId(
                                        e.target.value ? Number(e.target.value) : null,
                                    )
                                }
                                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="">Selecione uma câmera</option>
                                {availableCameras.map((camera) => (
                                    <option key={camera.camera_id} value={camera.camera_id}>
                                        {camera.name} - {camera.running ? 'Rodando' : 'Parado'}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Stream de vídeo */}
                        <VideoStream cameraId={selectedCameraId ?? undefined} />
                    </div>

                    {/* Coluna lateral */}
                    <div className="lg:col-span-1 space-y-6">
                        <StreamControls />

                        <ZonesSummaryCard
                            totalZones={zones.length}
                            activeZones={activeZonesCount}
                            onOpenMap={handleOpenMap}
                        />

                        <CamerasSummaryCard
                            totalCameras={cameras.length}
                            activeCameras={activeCamerasCount}
                            onManageCameras={handleManageCameras}
                        />
                    </div>
                </div>

                {/* Seção de gerenciamento de zonas */}
                <div className="space-y-4">
                    {/* Header + botão Gerenciar */}
                    <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
                        <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-blue-100">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                                        <Layers className="w-5 h-5 text-white" />
                                    </div>
                                    <div>
                                        <h2 className="text-lg font-bold text-gray-900">
                                            Zonas Monitoradas
                                        </h2>
                                        <p className="text-sm text-gray-600">
                                            {activeZonesCount} de {zones.length} ativas
                                        </p>
                                    </div>
                                </div>

                                <button
                                    onClick={handleManageZones}
                                    className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all shadow-md hover:shadow-lg font-medium"
                                >
                                    <Layers className="w-4 h-4" />
                                    <span>Gerenciar Zonas</span>
                                </button>
                            </div>
                        </div>

                        {/* Tabela de Zonas / Empty state */}
                        <div className="p-6">
                            {zones.length > 0 ? (
                                <ZoneTable zones={zoneTableData} />
                            ) : !zonesLoading ? (
                                <div className="bg-white rounded-lg border border-gray-200 p-12">
                                    <div className="text-center space-y-3">
                                        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
                                            <Layers className="w-8 h-8 text-gray-400" />
                                        </div>
                                        <h3 className="text-lg font-semibold text-gray-900">
                                            Nenhuma Zona Configurada
                                        </h3>
                                        <p className="text-gray-600">
                                            Configure zonas para monitorar áreas específicas no vídeo.
                                        </p>
                                        <button
                                            onClick={handleManageZones}
                                            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                                        >
                                            <Layers className="w-4 h-4" />
                                            <span>Ir para Zonas</span>
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <p className="text-sm text-gray-500">Carregando zonas...</p>
                            )}
                        </div>
                    </div>

                    {/* Atividade recente (placeholder) */}
                    <div className="bg-white rounded-lg shadow">
                        <div className="p-6 border-b border-gray-200">
                            <h2 className="text-lg font-semibold text-gray-900">
                                Atividade Recente
                            </h2>
                        </div>
                        <div className="p-6">
                            <p className="text-gray-500 text-center py-8">
                                Nenhuma atividade recente
                            </p>
                            {streamError && (
                                <p className="mt-2 text-xs text-red-500 text-center">
                                    Erro do stream: {streamError}
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Modal de visualização/criação de zonas */}
            {showZoneMap && (
                <ZoneDrawer
                    isOpen
                    mode="create"
                    zone={selectedZone ?? undefined}
                    streamUrl={
                        selectedCameraId
                            ? streamAPI.getStreamUrl(selectedCameraId)
                            : 'http://localhost:8000/api/v1/stream/video_feed'
                    }
                    cameraId={selectedCameraId ?? undefined}
                    onClose={() => {
                        setShowZoneMap(false);
                        setSelectedZone(null);
                    }}
                    onSave={async (data: CreateZonePayload | UpdateZonePayload) => {
                        try {
                            // Usa o createZone já instanciado no hook
                            const result = await createZone(data as CreateZonePayload);
                            if (result) {
                                console.log('Zona criada com sucesso', result);
                                setShowZoneMap(false);
                                setSelectedZone(null);
                                await fetchZones(false);
                            } else {
                                console.error('Falha ao criar zona - retorno null');
                            }
                        } catch (err) {
                            console.error('Erro ao criar zona', err);
                        }
                    }}
                />
            )}
        </MainLayout>
    );
}
