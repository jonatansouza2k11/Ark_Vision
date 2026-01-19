// src/components/dashboard/VideoStream.tsx - v4.1
// MULTI-CAMERA READY + COMPATÍVEL COM /status/{camera_id}

import {
    useState,
    useEffect,
    useMemo,
    useCallback,
    useRef,
} from 'react';

import {
    Play,
    Pause,
    Maximize2,
    RefreshCw,
    Camera as CameraIcon,
} from 'lucide-react';

import { streamAPI, type CameraStreamStatus } from '../../services/streamApi';

// Props
interface VideoStreamProps {
    cameraId?: number; // permite especificar câmera via rota (?camera=8)
}

// Componente principal
export default function VideoStream({ cameraId }: VideoStreamProps) {
    // Status detalhado da câmera (vindo de /api/v1/stream/status/{camera_id})
    const [status, setStatus] = useState<CameraStreamStatus | null>(null);

    // Flags de erro/carregamento
    const [error, setError] = useState(false);

    // Câmera selecionada (se não vier por props, busca primeira ativa)
    const [selectedCameraId, setSelectedCameraId] = useState<number | null>(
        cameraId ?? null,
    );

    // Refs para <img> MJPEG e controle de conexão
    const imgRef = useRef<HTMLImageElement | null>(null);
    const timestampRef = useRef<number>(Date.now());
    const connectionAttempted = useRef(false);

    // ---------------------------------------------------------------------------
    // Sincroniza prop cameraId com state interno
    // ---------------------------------------------------------------------------
    useEffect(() => {
        if (cameraId !== undefined && cameraId !== selectedCameraId) {
            setSelectedCameraId(cameraId);
            setError(false);
            connectionAttempted.current = false;
        }
    }, [cameraId, selectedCameraId]);
    
    // ---------------------------------------------------------------------------
    // Selecionar câmera automaticamente se não vier via props
    // ---------------------------------------------------------------------------
    useEffect(() => {
        if (selectedCameraId) return;

        let cancelled = false;

        async function loadFirstCamera() {
            try {
                const response = await streamAPI.getCameras();
                const cameras = response.data as any[];

                if (!cancelled && cameras.length > 0) {
                    // backend retorna camera_id em CameraRuntimeStatus
                    setSelectedCameraId(cameras[0].camera_id);
                }
            } catch (err) {
                console.error('Erro ao buscar câmeras para stream:', err);
            }
        }

        loadFirstCamera();

        return () => {
            cancelled = true;
        };
    }, [selectedCameraId]);

    // ---------------------------------------------------------------------------
    // URL do stream MJPEG para a câmera selecionada
    // ---------------------------------------------------------------------------
    const streamUrl = useMemo(() => {
        return selectedCameraId ? streamAPI.getStreamUrl(selectedCameraId) : null;
    }, [selectedCameraId]);

    // ---------------------------------------------------------------------------
    // Polling de status da câmera selecionada
    // ---------------------------------------------------------------------------
    useEffect(() => {
        if (!selectedCameraId) return;

        let cancelled = false;

        const loadStatus = async () => {
            try {
                const response = await streamAPI.getStatus(selectedCameraId);
                if (!cancelled) {
                    setStatus(response.data as CameraStreamStatus);
                }
            } catch (error) {
                if (!cancelled) {
                    console.error('Error loading camera status:', error);
                }
            }
        };

        loadStatus();
        const interval = setInterval(loadStatus, 2000);

        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, [selectedCameraId]);

    // ---------------------------------------------------------------------------
    // Derivação de estado de execução (running/paused/stopped)
    // ---------------------------------------------------------------------------
    const streamState = useMemo(() => {
        const systemStatus = status?.system_status || 'stopped';

        return {
            status: systemStatus,
            isRunning: systemStatus === 'running',
            isPaused: systemStatus === 'paused',
            isStopped: systemStatus === 'stopped',
            isActive: systemStatus === 'running' || systemStatus === 'paused',
            statusLabel:
                systemStatus === 'running'
                    ? 'Rodando'
                    : systemStatus === 'paused'
                        ? 'Pausado'
                        : 'Parado',
            dotColor:
                systemStatus === 'running'
                    ? 'bg-green-500 animate-pulse'
                    : systemStatus === 'paused'
                        ? 'bg-yellow-500'
                        : 'bg-gray-400',
        };
    }, [status?.system_status]);

    // ---------------------------------------------------------------------------
    // Init / cleanup do elemento <img>
    // ---------------------------------------------------------------------------
    useEffect(() => {
        timestampRef.current = Date.now();

        return () => {
            if (imgRef.current) {
                imgRef.current.src = '';
            }
            connectionAttempted.current = false;
        };
    }, []);

    // ---------------------------------------------------------------------------
    // Carregar ou limpar o stream na <img> conforme estado
    // ---------------------------------------------------------------------------
    useEffect(() => {
        if (streamState.isRunning && !connectionAttempted.current && imgRef.current && streamUrl) {
            setError(false);
            imgRef.current.src = `${streamUrl}?t=${timestampRef.current}`;
            connectionAttempted.current = true;
        } else if (!streamState.isRunning) {
            connectionAttempted.current = false;
            if (imgRef.current) {
                imgRef.current.src = '';
            }
        }
    }, [streamState.isRunning, streamUrl]);

    // ---------------------------------------------------------------------------
    // Handlers auxiliares
    // ---------------------------------------------------------------------------
    const handleRefresh = useCallback(() => {
        setError(false);
        timestampRef.current = Date.now();
        connectionAttempted.current = false;

        if (imgRef.current && streamState.isRunning && streamUrl) {
            imgRef.current.src = `${streamUrl}?t=${timestampRef.current}`;
            connectionAttempted.current = true;
        }
    }, [streamUrl, streamState.isRunning]);

    const handleFullscreen = useCallback(() => {
        const container = document.getElementById('video-container');
        if (!container) return;

        if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => undefined);
        } else {
            container.requestFullscreen().catch(() => undefined);
        }
    }, []);

    const handleImageError = useCallback(() => {
        if (!streamState.isPaused && streamState.isRunning) {
            console.error('❌ Stream error');
            setError(true);
            connectionAttempted.current = false;
        }
    }, [streamState.isPaused, streamState.isRunning]);

    const handleImageLoad = useCallback(() => {
        setError(false);
    }, []);

    // ---------------------------------------------------------------------------
    // Renderização do conteúdo conforme estado
    // ---------------------------------------------------------------------------
    const renderContent = useMemo(() => {
        if (!selectedCameraId) {
            return (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <CameraIcon className="h-16 w-16 text-gray-300 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-800">
                        Nenhuma câmera disponível
                    </h3>
                    <p className="text-gray-500 mt-1">
                        Não há câmeras habilitadas para streaming. Configure uma câmera nas
                        configurações.
                    </p>
                </div>
            );
        }

        if (error) {
            return (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="text-yellow-500 text-4xl mb-2">⚠️</div>
                    <h3 className="text-lg font-semibold text-gray-800">
                        Erro ao carregar stream
                    </h3>
                    <p className="text-gray-500 mt-1">
                        Verifique se o backend está rodando e se o stream está iniciado.
                    </p>
                    <button
                        onClick={handleRefresh}
                        className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 text-sm font-medium"
                    >
                        <RefreshCw className="h-4 w-4" />
                        Tentar novamente
                    </button>
                </div>
            );
        }

        if (streamState.isPaused) {
            return (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <Pause className="h-12 w-12 text-yellow-500 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-800">
                        Stream pausado
                    </h3>
                    <p className="text-gray-500 mt-1">
                        Clique em &quot;Retomar&quot; nos controles para continuar.
                    </p>
                </div>
            );
        }

        if (streamState.isStopped) {
            return (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <Play className="h-12 w-12 text-green-500 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-800">
                        Stream desligado
                    </h3>
                    <p className="text-gray-500 mt-1">
                        Clique em &quot;Iniciar&quot; nos controles para começar.
                    </p>
                </div>
            );
        }

        if (streamState.isRunning && streamUrl) {
            return (
                <div
                    id="video-container"
                    className="relative bg-black rounded-xl overflow-hidden shadow-inner"
                >
                    <img
                        ref={imgRef}
                        alt="YOLO Stream"
                        onError={handleImageError}
                        onLoad={handleImageLoad}
                        className="w-full h-full object-contain bg-black"
                    />
                    <button
                        type="button"
                        onClick={handleFullscreen}
                        className="absolute top-3 right-3 inline-flex items-center justify-center rounded-full bg-black/60 hover:bg-black/80 text-white p-2 transition-colors"
                        title="Tela cheia"
                    >
                        <Maximize2 className="h-4 w-4" />
                    </button>
                </div>
            );
        }

        return null;
    }, [
        error,
        streamState,
        selectedCameraId,
        streamUrl,
        handleRefresh,
        handleImageError,
        handleImageLoad,
        handleFullscreen,
    ]);

    // ---------------------------------------------------------------------------
    // FPS exibido
    // ---------------------------------------------------------------------------
    const displayFps = useMemo(() => {
        if (status?.fps_current) return status.fps_current.toFixed(1);
        if (status?.fps_avg) return status.fps_avg.toFixed(1);
        return null;
    }, [status?.fps_current, status?.fps_avg]);

    // ---------------------------------------------------------------------------
    // Render final
    // ---------------------------------------------------------------------------
    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-bold text-gray-900">
                        Stream YOLO em Tempo Real
                        {status?.camera_name && (
                            <span className="ml-2 text-sm font-medium text-gray-600">
                                ({status.camera_name})
                            </span>
                        )}
                    </h2>
                    <p className="text-sm text-gray-500">
                        Detecções em tempo real com YOLO, por câmera.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                        <span
                            className={`inline-block w-2.5 h-2.5 rounded-full ${streamState.dotColor}`}
                        />
                        <span className="text-sm text-gray-700">
                            {streamState.statusLabel}
                        </span>
                    </div>
                    {displayFps && streamState.isRunning && (
                        <div className="px-3 py-1 rounded-full bg-gray-100 text-xs font-medium text-gray-700">
                            {displayFps} FPS
                        </div>
                    )}
                </div>
            </div>

            <div className="border rounded-xl bg-white shadow-sm overflow-hidden">
                {renderContent}
            </div>
        </div>
    );
}
