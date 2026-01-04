// src/components/dashboard/VideoStream.tsx
import { useState, useEffect, useMemo, useCallback } from 'react';
import { Play, Pause, Maximize2, RefreshCw } from 'lucide-react';
import { useYOLOStream } from '../../hooks/useYOLOStream';

interface VideoStreamProps {
    streamUrl?: string;
}

export default function VideoStream({ streamUrl }: VideoStreamProps) {
    const { stats } = useYOLOStream(2000, true);
    const [error, setError] = useState(false);
    const [streamKey, setStreamKey] = useState(Date.now());

    // ✅ OTIMIZAÇÃO 1: Centralização - URL única calculada uma vez
    const streamUrl_final = useMemo(
        () => streamUrl || 'http://localhost:8000/video_feed',
        [streamUrl]
    );

    // ✅ OTIMIZAÇÃO 2: Cache de estados derivados (evita recálculos)
    const streamState = useMemo(() => {
        const status = stats?.system_status || 'stopped';
        return {
            status,
            isRunning: status === 'running',
            isPaused: status === 'paused',
            isStopped: status === 'stopped',
            isActive: status === 'running' || status === 'paused',
            statusLabel: status === 'running' ? 'Rodando' :
                status === 'paused' ? 'Pausado' : 'Parado',
            dotColor: status === 'running' ? 'bg-green-500 animate-pulse' :
                status === 'paused' ? 'bg-yellow-500' : 'bg-gray-400'
        };
    }, [stats?.system_status]);

    // ✅ OTIMIZAÇÃO 3: Auto-reload consolidado com cleanup de erro
    useEffect(() => {
        if (streamState.isRunning) {
            setError(false);
            setStreamKey(Date.now());
        } else if (streamState.isPaused && error) {
            setError(false); // Limpa erro ao pausar
        }
    }, [streamState.isRunning, streamState.isPaused]);

    // ✅ OTIMIZAÇÃO 4: Handlers memoizados (evita re-criação)
    const handleRefresh = useCallback(() => {
        setError(false);
        setStreamKey(Date.now());
    }, []);

    const handleFullscreen = useCallback(() => {
        const container = document.getElementById('video-container');
        if (!container) return;

        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            container.requestFullscreen();
        }
    }, []);

    const handleImageError = useCallback(() => {
        if (!streamState.isPaused) {
            setError(true);
        }
    }, [streamState.isPaused]);

    // ✅ OTIMIZAÇÃO 5: Renderização condicional consolidada
    const renderContent = useMemo(() => {
        // Estado: Erro
        if (error) {
            return (
                <div className="text-center text-white p-8">
                    <div className="w-16 h-16 mx-auto mb-4 bg-yellow-500/20 rounded-full flex items-center justify-center">
                        <span className="text-3xl">⚠️</span>
                    </div>
                    <p className="text-lg font-semibold mb-2">Erro ao carregar stream</p>
                    <p className="text-sm text-gray-400 mb-4">
                        Verifique se o backend está rodando
                    </p>
                    <button
                        onClick={handleRefresh}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        Tentar novamente
                    </button>
                </div>
            );
        }

        // Estado: Pausado
        if (streamState.isPaused) {
            return (
                <div className="text-center text-white p-8">
                    <div className="w-16 h-16 mx-auto mb-4 bg-gray-700 rounded-full flex items-center justify-center">
                        <Pause className="w-8 h-8 text-gray-300" />
                    </div>
                    <p className="text-lg font-semibold mb-2">Stream pausado</p>
                    <p className="text-sm text-gray-400">
                        Clique em "Retomar" para continuar
                    </p>
                </div>
            );
        }

        // Estado: Parado
        if (streamState.isStopped) {
            return (
                <div className="text-center text-white p-8">
                    <div className="w-16 h-16 mx-auto mb-4 bg-gray-700 rounded-full flex items-center justify-center">
                        <Play className="w-8 h-8 text-gray-300" />
                    </div>
                    <p className="text-lg font-semibold mb-2">Stream desligado</p>
                    <p className="text-sm text-gray-400">
                        Clique em "Iniciar" para começar
                    </p>
                </div>
            );
        }

        // Estado: Running (stream ativo)
        return (
            <img
                key={streamKey}
                id="video-stream"
                src={`${streamUrl_final}?t=${streamKey}`}
                alt="YOLO Video Stream"
                className="w-full h-full object-contain"
                onError={handleImageError}
            />
        );
    }, [error, streamState, streamKey, streamUrl_final, handleRefresh, handleImageError]);

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${streamState.dotColor}`} />
                    <span className="text-sm font-medium text-gray-700">
                        Stream YOLO em Tempo Real
                        <span className="ml-2 text-xs text-gray-500">
                            ({streamState.statusLabel})
                        </span>
                    </span>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={handleRefresh}
                        disabled={streamState.isPaused || streamState.isStopped}
                        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Atualizar"
                    >
                        <RefreshCw className="w-4 h-4" />
                    </button>

                    <button
                        onClick={handleFullscreen}
                        disabled={!streamState.isActive}
                        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Tela cheia"
                    >
                        <Maximize2 className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Video Container */}
            <div
                id="video-container"
                className="relative bg-gray-900 aspect-video flex items-center justify-center"
            >
                {renderContent}
            </div>

            {/* Footer Info */}
            <div className="px-4 py-2 bg-gray-50 border-t border-gray-200">
                <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>Detecções em tempo real com YOLOv8</span>
                    {stats?.fps && (
                        <span className="font-mono">
                            {stats.fps_avg?.toFixed(1) || stats.fps} FPS
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}
