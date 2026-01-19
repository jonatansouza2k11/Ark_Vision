// frontend/src/pages/Dashboard.tsx
import { useState, useEffect } from 'react';
import { Users, RefreshCw, CheckCircle2, Zap, TrendingUp, Map, Layers, Camera, Video } from 'lucide-react';

import MainLayout from '../components/layout/MainLayout';
import { useAuthStore } from '../store/authStore';
import VideoStream from '../components/dashboard/VideoStream';
import StreamControls from '../components/dashboard/StreamControls';
import SystemInfoBanner from '../components/dashboard/SystemInfoBanner';
import { useYOLOStream } from '../hooks/useYOLOStream';
import { streamAPI, type CameraRuntimeStatus } from '../services/streamApi';


// ✅ NOVO: Imports para Zonas
import { useZones } from '../hooks/useZones';
import ZoneTable from '../components/dashboard/ZoneTable';
import ZoneDrawer from '../components/zones/ZoneDrawer';
import type { Zone, CreateZonePayload, UpdateZonePayload } from '../types/zones.types';

// ✅ NOVO: Imports para Câmeras
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
// ✅ NOVO: CamerasSummaryCard Component (Mini Card de Resumo)
// ============================================================================
interface CamerasSummaryCardProps {
    totalCameras: number;
    activeCameras: number;
    onManageCameras: () => void;
}


function CamerasSummaryCard({ totalCameras, activeCameras, onManageCameras }: CamerasSummaryCardProps) {
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


                {/* Manage Button */}
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
// Dashboard Page
// ============================================================================

//  Normalizar status do backend para frontend
const normalizeState = (backendState: string): 'empty' | 'normal' | 'warning' | 'alert' | 'critical' | 'pending' | 'empty_pending' | 'full_pending' => {
    const stateMap: Record<string, any> = {
        'NORMAL': 'normal',
        'EMPTY': 'empty',
        'EMPTY_PENDING': 'empty_pending',
        'OCCUPIED': 'normal',
        'FULL': 'critical',
        'FULL_PENDING': 'full_pending',
        'WARNING': 'warning',
        'CRITICAL': 'critical',
        'ALERT': 'alert',
        'PENDING': 'pending',
        'DETECTED': 'alert',
        'IDLE': 'normal',
        'TRACKING': 'normal',
    };
    return stateMap[backendState.toUpperCase()] || 'normal';
};

export default function Dashboard() {
    const { user } = useAuthStore();
    const { stats } = useYOLOStream(2000, true);


    // Zonas State e Hook
    const { zones, loading: zonesLoading, fetchZones, createZone } = useZones();
    const [showZoneMap, setShowZoneMap] = useState(false);
    const [selectedZone, setSelectedZone] = useState<Zone | null>(null);

    // Métricas de zonas em tempo real
    const [zoneMetrics, setZoneMetrics] = useState<any[]>([]);

    // Câmeras Hook
    const { cameras } = useCameras();

    // State para seleção de câmera no dashboard
    const [selectedCameraId, setSelectedCameraId] = useState<number | null>(null);
    const [availableCameras, setAvailableCameras] = useState<CameraRuntimeStatus[]>([]);

    const [dashboardStats] = useState({
        status: 'Sistema Operacional',
    });


    // Calcular status baseado no stream
    const systemStatus: 'online' | 'offline' | 'paused' | 'stopped' =
        stats?.system_status === 'running' ? 'online' :
            stats?.system_status === 'paused' ? 'paused' :
                stats?.system_status === 'stopped' ? 'stopped' : 'offline';


    // Formatar FPS atual (com fallback para fpsavg)
    const fpsCurrentDisplay = stats?.fps_current !== undefined
        ? Math.round(stats.fps_current)
        : Math.round(stats?.fpsavg || 0);


    // Formatar FPS médio (com fallback para fpsavg)
    const fpsAvgDisplay = stats?.fps_avg !== undefined
        ? Math.round(stats.fps_avg)
        : Math.round(stats?.fpsavg || 0);


    // Calcular zonas ativas
    const activeZonesCount = zones.filter(z => z.enabled).length;


    // Calcular câmeras ativas
    const activeCamerasCount = cameras.filter(c => c.enabled).length;


    // Buscar zonas ao montar
    useEffect(() => {
        fetchZones(false); // false = apenas ativas
    }, [fetchZones]);


    // Carregar câmeras disponíveis no VisionSystem
    useEffect(() => {
        loadAvailableCameras();

        // Recarrega quando a página ganha foco (volta de outra aba/página)
        const handleFocus = () => {
            loadAvailableCameras();
        };

        window.addEventListener('focus', handleFocus);
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                loadAvailableCameras();
            }
        });

        return () => {
            window.removeEventListener('focus', handleFocus);
        };
    }, []);

    const loadAvailableCameras = async () => {
        try {
            // Recarrega do banco para pegar zonas atualizadas
            await streamAPI.reloadCameras().catch((err: unknown) => {
                console.warn("Failed to reload cameras:", err);
            });
            

            const response = await streamAPI.getCameras();
            setAvailableCameras(response.data);

            // Seleciona primeira câmera por padrão
            if (!selectedCameraId && response.data.length > 0) {
                setSelectedCameraId(response.data[0].camera_id);
            }
        } catch (error) {
            console.error("Error loading cameras:", error);
        }
    };


    // Carregar métricas de zonas
    useEffect(() => {
        if (!selectedCameraId) return;

        const loadZoneMetrics = async () => {
            try {
                const response = await fetch(
                    `http://localhost:8000/api/v1/stream/zone_metrics/${selectedCameraId}`,
                    {
                        headers: {
                            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                        }
                    }
                );
                if (response.ok) {
                    const data = await response.json();
                    setZoneMetrics(data);
                }
            } catch (error) {
                console.error('Error loading zone metrics:', error);
            }
        };

        loadZoneMetrics();
        const interval = setInterval(loadZoneMetrics, 2000);

        return () => clearInterval(interval);
    }, [selectedCameraId]);


    // Handler para abrir mapa
    const handleOpenMap = () => {
        setShowZoneMap(true);
        setSelectedZone(null);
    };


    // Handler para gerenciar câmeras
    const handleManageCameras = () => {
        window.location.href = '/cameras';
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
                        onClick={() => {
                            fetchZones(false);
                            loadAvailableCameras();
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <RefreshCw className="h-4 w-4" />
                        Atualizar
                    </button>

                </div>


                {/* System Info Banner */}
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


                {/* Grid Video Stream + Controles + Zonas */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Video Stream - ocupa 2 colunas */}
                    <div className="lg:col-span-2 space-y-4">
                        {/* Seletor de Câmera */}
                        {availableCameras.length > 0 && (
                            <div className="bg-white rounded-lg shadow border border-gray-200 p-4">
                                <div className="flex items-center gap-3">
                                    <Video className="w-5 h-5 text-gray-500" />
                                    <label className="text-sm font-medium text-gray-700">
                                        Câmera:
                                    </label>
                                    <select
                                        value={selectedCameraId || ""}
                                        onChange={(e) => setSelectedCameraId(Number(e.target.value))}
                                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    >
                                        {availableCameras.map((camera) => (
                                            <option key={camera.camera_id} value={camera.camera_id}>
                                                {camera.name} - {camera.running ? "Rodando" : "Parado"}
                                            </option>
                                        ))}


                                    </select>
                                </div>
                            </div>
                        )}

                        <VideoStream cameraId={selectedCameraId ?? undefined} />
                    </div>

                    {/* Coluna lateral com StreamControls + ZonesSummary + CamerasSummary */}
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
                


                    {/* ========================================== */}
                    {/* ✅ NOVO: SEÇÃO DE GERENCIAMENTO DE ZONAS  */}
                    {/* ========================================== */}

                    {/* Tabela de Zonas com Header e Botão */}
                    {zones.length > 0 && (
                        <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
                            {/* Header com Botão Gerenciar */}
                            <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-blue-100">
                                <div className="flex items-center justify-between">
                                    {/* Título e Info */}
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                                            <Layers className="w-5 h-5 text-white" />
                                        </div>
                                        <div>
                                            <h2 className="text-lg font-bold text-gray-900">Zonas Monitoradas</h2>
                                            <p className="text-sm text-gray-600">
                                                {activeZonesCount} de {zones.length} ativas
                                            </p>
                                        </div>
                                    </div>

                                    {/* Botão Gerenciar Zonas */}
                                    <button
                                        onClick={() => window.location.href = '/zones'}
                                        className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all shadow-md hover:shadow-lg font-medium"
                                    >
                                        <Layers className="w-4 h-4" />
                                        <span>Gerenciar Zonas</span>
                                    </button>
                                </div>
                            </div>

                            {/* Tabela de Zonas */}
                            <div className="p-6">
                                <ZoneTable
                                    zones={zones
                                        .filter((z) => z.enabled)
                                        .map((zone) => {
                                            // ✅ Busca métricas em tempo real
                                            const metrics = zoneMetrics.find(m => m.zone_id === zone.id);

                                            return {
                                                zone_id: zone.id,
                                                zone_name: zone.name,
                                                mode: zone.mode,
                                                current_count: metrics?.current_count ?? 0,
                                                time_empty: metrics?.time_empty ?? 0,
                                                time_full: metrics?.time_full ?? 0,
                                                //state: metrics?.state ?? 'normal',
                                                state: normalizeState(metrics?.state ?? 'normal'),
                                                max_capacity: metrics?.max_capacity,
                                                camera_id: zone.camera_id,
                                                full_timeout: zone.full_timeout,
                                            };
                                        })}
                                />
                            </div>
                        </div>
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


            {/* Modal de Visualização/Criação de Zonas */}
            {showZoneMap && (
                <ZoneDrawer
                    isOpen={true}
                    mode="create"
                    zone={selectedZone || undefined}
                    streamUrl={selectedCameraId ? streamAPI.getStreamUrl(selectedCameraId) : "http://localhost:8000/api/v1/stream/video_feed"}
                    cameraId={selectedCameraId ?? undefined}
                    onClose={() => {
                        setShowZoneMap(false);
                        setSelectedZone(null);
                    }}
                    onSave={async (data: CreateZonePayload | UpdateZonePayload) => {
                        try {
                            // ✅ USA O createZone JÁ INSTANCIADO NO TOPO
                            const result = await createZone(data as CreateZonePayload);

                            if (result) {
                                console.log('✅ Zona criada com sucesso:', result);
                                setShowZoneMap(false);
                                setSelectedZone(null);
                                await fetchZones(false);  // Atualiza lista
                            } else {
                                console.error('❌ Falha ao criar zona (retornou null)');
                            }
                        } catch (err) {
                            console.error('❌ Erro ao criar zona:', err);
                        }
                    }}
                />
            )}

        </MainLayout>
    );
}
