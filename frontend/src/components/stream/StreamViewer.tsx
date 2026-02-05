/**
 * StreamViewer.tsx - Multi-Camera Stream Viewer
 * Component for viewing camera streams with real-time metrics
 */

import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
    Camera,
    Download,
    Maximize,
    Minimize,
    ChevronLeft,
    Activity,
    Eye,
    Layers,
    AlertCircle,
    RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import MainLayout from '../layout/MainLayout';
import { streamAPI, type CameraStreamStatus, type CameraRuntimeStatus } from '../../services/streamApi';
import StreamControls from '../dashboard/StreamControls'


// ============================================
// COMPONENT
// ============================================

export function StreamViewer() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    // Estado
    const [selectedCameraId, setSelectedCameraId] = useState<number | null>(null);
    const [availableCameras, setAvailableCameras] = useState<CameraRuntimeStatus[]>([]);
    const [status, setStatus] = useState<CameraStreamStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [streamError, setStreamError] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);

    // ============================================
    // LOAD CAMERAS
    // ============================================

    useEffect(() => {
        loadAvailableCameras();
    }, []);

    const loadAvailableCameras = async () => {
        try {
            // ✅ Recarrega câmeras do banco para pegar zonas atualizadas
            await streamAPI.reloadCameras().catch((err) => {
                console.warn("Failed to reload cameras:", err);
                // Não bloqueia se falhar
            });

            const response = await streamAPI.getCameras();
            setAvailableCameras(response.data);

            // Se não há câmera selecionada, pega da URL ou primeira disponível
            if (!selectedCameraId) {
                const cameraFromUrl = searchParams.get("camera");
                if (cameraFromUrl) {
                    setSelectedCameraId(Number(cameraFromUrl));
                } else if (response.data.length > 0) {
                    setSelectedCameraId(response.data[0].camera_id);
                }
            }
        } catch (error) {
            console.error("Error loading cameras:", error);
            toast.error("Erro ao carregar câmeras disponíveis");
        } finally {
            setLoading(false);
        }
    };
      

    // ============================================
    // LOAD CAMERA STATUS
    // ============================================

    useEffect(() => {
        if (!selectedCameraId) return;

        loadCameraStatus();

        // Poll status a cada 2 segundos
        const interval = setInterval(loadCameraStatus, 2000);

        return () => clearInterval(interval);
    }, [selectedCameraId]);

    const loadCameraStatus = async () => {
        if (!selectedCameraId) return;

        try {
            const response = await streamAPI.getStatus(selectedCameraId);
            setStatus(response.data);
            setStreamError(false);
        } catch (error) {
            console.error('Error loading status:', error);
            setStreamError(true);
        }
    };

    // ============================================
    // HANDLERS
    // ============================================

    const handleCameraChange = (cameraId: number) => {
        setSelectedCameraId(cameraId);
        navigate(`/stream?camera=${cameraId}`, { replace: true });
    };

    const handleSnapshot = async () => {
        if (!selectedCameraId) return;

        try {
            const camera = availableCameras.find(c => c.camera_id === selectedCameraId);
            const filename = `${camera?.name || 'camera'}-${Date.now()}.jpg`;

            await streamAPI.downloadSnapshot(selectedCameraId, filename);
            toast.success('Snapshot capturado com sucesso!');
        } catch (error) {
            console.error('Error capturing snapshot:', error);
            toast.error('Erro ao capturar snapshot');
        }
    };

    const handleToggleFullscreen = () => {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
            setIsFullscreen(true);
        } else {
            document.exitFullscreen();
            setIsFullscreen(false);
        }
    };

    const handleBack = () => {
        navigate('/cameras');
    };

    // ============================================
    // RENDER LOADING
    // ============================================

    if (loading) {
        return (
            <MainLayout>
                <div className="flex items-center justify-center h-96">
                    <div className="text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                        <p className="text-gray-600">Carregando câmeras...</p>
                    </div>
                </div>
            </MainLayout>
        );
    }

    // ============================================
    // RENDER NO CAMERAS
    // ============================================

    if (availableCameras.length === 0) {
        return (
            <MainLayout>
                <div className="text-center py-12">
                    <Camera className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                        Nenhuma câmera disponível
                    </h3>
                    <p className="text-gray-500 mb-6">
                        Não há câmeras habilitadas para streaming.
                    </p>
                    <button
                        onClick={handleBack}
                        className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                        <ChevronLeft className="w-4 h-4 mr-2" />
                        Voltar para Câmeras
                    </button>
                </div>
            </MainLayout>
        );
    }

    // ============================================
    // RENDER STREAM VIEWER
    // ============================================

    const streamUrl = selectedCameraId ? streamAPI.getStreamUrl(selectedCameraId) : null;
    const currentCamera = availableCameras.find(c => c.camera_id === selectedCameraId);

    return (
        <MainLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <button
                            onClick={handleBack}
                            className="flex items-center text-gray-600 hover:text-gray-900"
                        >
                            <ChevronLeft className="w-5 h-5 mr-1" />
                            Voltar
                        </button>

                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">
                                Visualização de Stream
                            </h1>
                            <p className="text-gray-500">
                                {currentCamera?.name || 'Selecione uma câmera'}
                            </p>
                        </div>
                    </div>

                    {/* Camera Selector */}
                    <div className="flex items-center space-x-3">
                        <label className="text-sm font-medium text-gray-700">
                            Câmera:
                        </label>
                        <select
                            value={selectedCameraId || ''}
                            onChange={(e) => handleCameraChange(Number(e.target.value))}
                            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                            {availableCameras.map(camera => (
                                <option key={camera.camera_id} value={camera.camera_id}>
                                    {camera.name} {camera.running ? '🟢' : '🔴'}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Main Content */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Stream Display */}
                    <div className="lg:col-span-2">
                        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                            {/* Stream Controls */}
                            <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 flex items-center justify-between">
                                <div className="flex items-center space-x-2">
                                    <Activity className="w-4 h-4 text-gray-500" />
                                    <span className="text-sm font-medium text-gray-700">
                                        Stream ao vivo
                                    </span>
                                    {status?.stream_active && (
                                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                            <span className="w-2 h-2 bg-green-500 rounded-full mr-1.5 animate-pulse"></span>
                                            Ao vivo
                                        </span>
                                    )}
                                </div>

                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={handleSnapshot}
                                        className="p-2 text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
                                        title="Capturar snapshot"
                                    >
                                        <Download className="w-4 h-4" />
                                    </button>

                                    <button
                                        onClick={handleToggleFullscreen}
                                        className="p-2 text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
                                        title={isFullscreen ? 'Sair de tela cheia' : 'Tela cheia'}
                                    >
                                        {isFullscreen ? (
                                            <Minimize className="w-4 h-4" />
                                        ) : (
                                            <Maximize className="w-4 h-4" />
                                        )}
                                    </button>

                                    <button
                                        onClick={loadCameraStatus}
                                        className="p-2 text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
                                        title="Atualizar"
                                    >
                                        <RefreshCw className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>

                            {/* Stream Image */}
                            <div className="relative bg-black aspect-video">
                                {streamUrl && !streamError ? (
                                    <img
                                        src={streamUrl}
                                        alt={`Stream da câmera ${currentCamera?.name}`}
                                        className="w-full h-full object-contain"
                                        onError={() => setStreamError(true)}
                                    />
                                ) : (
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <div className="text-center text-white">
                                            <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                                            <p className="text-lg font-medium mb-2">
                                                Stream não disponível
                                            </p>
                                            <p className="text-sm opacity-75">
                                                Verifique se a câmera está ativa e configurada corretamente
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Metrics Sidebar */}
                    <div className="space-y-6">

                        {/*  Stream Controls */}
                        <div className="bg-white rounded-lg border border-gray-200 p-6">
                            <StreamControls />
                        </div>

                        {/* FPS & Performance */}
                        <div className="bg-white rounded-lg border border-gray-200 p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">
                                Performance
                            </h3>

                            <div className="space-y-4">
                                <div>
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-sm text-gray-600">FPS Atual</span>
                                        <span className="text-2xl font-bold text-blue-600">
                                            {status?.fps_current.toFixed(1) || '0.0'}
                                        </span>
                                    </div>
                                    <div className="text-xs text-gray-500">
                                        Média: {status?.fps_avg.toFixed(1) || '0.0'} FPS
                                    </div>
                                </div>

                                <div className="pt-4 border-t border-gray-200">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-sm text-gray-600">Conexões Ativas</span>
                                        <span className="text-xl font-semibold text-gray-900">
                                            {status?.active_connections || 0}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Detections */}
                        <div className="bg-white rounded-lg border border-gray-200 p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                                <Eye className="w-5 h-5 mr-2 text-gray-500" />
                                Detecções
                            </h3>

                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Total Hoje</span>
                                    <span className="text-xl font-bold text-green-600">
                                        {status?.detected_count || 0}
                                    </span>
                                </div>

                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Na Zona</span>
                                    <span className="text-lg font-semibold text-blue-600">
                                        {status?.inzone || 0}
                                    </span>
                                </div>

                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Fora da Zona</span>
                                    <span className="text-lg font-semibold text-gray-600">
                                        {status?.outzone || 0}
                                    </span>
                                </div>

                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Rastreando</span>
                                    <span className="text-lg font-semibold text-purple-600">
                                        {status?.active_tracks || 0}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Zones */}
                        <div className="bg-white rounded-lg border border-gray-200 p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                                <Layers className="w-5 h-5 mr-2 text-gray-500" />
                                Zonas
                            </h3>

                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-600">Zonas Carregadas</span>
                                <span className="text-xl font-bold text-indigo-600">
                                    {status?.zones_loaded || 0}
                                </span>
                            </div>

                            <button
                                onClick={() => navigate(`/zones?camera=${selectedCameraId}`)}
                                className="mt-4 w-full px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 transition-colors text-sm font-medium"
                            >
                                Configurar Zonas
                            </button>
                        </div>

                        {/* Status */}
                        <div className="bg-white rounded-lg border border-gray-200 p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">
                                Status do Sistema
                            </h3>

                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Estado</span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${status?.system_status === 'running'
                                            ? 'bg-green-100 text-green-800'
                                            : status?.system_status === 'paused'
                                                ? 'bg-yellow-100 text-yellow-800'
                                                : 'bg-gray-100 text-gray-800'
                                        }`}>
                                        {status?.system_status || 'stopped'}
                                    </span>
                                </div>

                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Streaming</span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${status?.stream_active
                                            ? 'bg-green-100 text-green-800'
                                            : 'bg-gray-100 text-gray-800'
                                        }`}>
                                        {status?.stream_active ? 'Ativo' : 'Inativo'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </MainLayout>
    );
}

export default StreamViewer;
