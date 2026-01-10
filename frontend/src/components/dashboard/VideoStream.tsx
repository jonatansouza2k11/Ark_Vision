// src/components/dashboard/VideoStream.tsx - v3.3.1 (CORRIGIDO)
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Play, Pause, Maximize2, RefreshCw } from 'lucide-react';
import { useYOLOStream } from '../../hooks/useYOLOStream';

interface VideoStreamProps {
    streamUrl?: string;
}

/**
 * ✅ v3.3.1 FIXES + CORREÇÃO DE URL:
 * - Timestamp fixo por sessão (evita reconexões duplicadas)
 * - Cleanup adequado ao desmontar
 * - Melhor controle de recarregamento
 * - Previne memory leaks
 * - Corrigido URL do stream para backend FastAPI
 */
export default function VideoStream({ streamUrl }: VideoStreamProps) {
    const { stats } = useYOLOStream(2000, true);
    const [error, setError] = useState(false);

    // ✅ Refs para controlar conexão única
    const imgRef = useRef<HTMLImageElement>(null);
    const timestampRef = useRef<number>(Date.now()); // Timestamp fixo por sessão
    const connectionAttempted = useRef(false);

    // ✅ URL corrigido para FastAPI
    const streamUrl_final = useMemo(
        () => streamUrl || 'http://localhost:8000/api/v1/stream/video_feed',
        [streamUrl]
    );

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

    // ✅ Initialize timestamp only once on mount
    useEffect(() => {
        timestampRef.current = Date.now();

        return () => {
            // ✅ Cleanup on unmount
            if (imgRef.current) {
                imgRef.current.src = '';
            }
            connectionAttempted.current = false;
        };
    }, []);

    // ✅ Load stream APENAS quando iniciar
    useEffect(() => {
        if (streamState.isRunning && !connectionAttempted.current && imgRef.current) {
            setError(false);
            imgRef.current.src = `${streamUrl_final}?t=${timestampRef.current}`;
            connectionAttempted.current = true;
        } else if (!streamState.isRunning) {
            connectionAttempted.current = false;
            if (imgRef.current) {
                imgRef.current.src = '';
            }
        }
    }, [streamState.isRunning, streamUrl_final]);

    const handleRefresh = useCallback(() => {
        setError(false);
        timestampRef.current = Date.now();
        connectionAttempted.current = false;

        if (imgRef.current && streamState.isRunning) {
            imgRef.current.src = `${streamUrl_final}?t=${timestampRef.current}`;
            connectionAttempted.current = true;
        }
    }, [streamUrl_final, streamState.isRunning]);

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
        if (!streamState.isPaused && streamState.isRunning) {
            console.error('❌ Stream error');
            setError(true);
            connectionAttempted.current = false;
        }
    }, [streamState.isPaused, streamState.isRunning]);

    const handleImageLoad = useCallback(() => {
        setError(false);
    }, []);

    const renderContent = useMemo(() => {
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

        if (streamState.isRunning) {
            return (
                <img
                    ref={imgRef}
                    id="video-stream"
                    alt="YOLO Video Stream"
                    className="w-full h-full object-contain"
                    onError={handleImageError}
                    onLoad={handleImageLoad}
                />
            );
        }

        return null;
    }, [error, streamState, handleRefresh, handleImageError, handleImageLoad]);

    const displayFps = useMemo(() => {
        if (stats?.fpsavg) return stats.fpsavg.toFixed(1);
        if (stats?.fps_avg) return stats.fps_avg.toFixed(1);
        if (stats?.fps_current) return stats.fps_current.toFixed(1);
        return null;
    }, [stats?.fpsavg, stats?.fps_avg, stats?.fps_current]);

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
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

            <div
                id="video-container"
                className="relative bg-gray-900 aspect-video flex items-center justify-center"
            >
                {renderContent}
            </div>

            <div className="px-4 py-2 bg-gray-50 border-t border-gray-200">
                <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>Detecções em tempo real com YOLOv8</span>
                    {displayFps && streamState.isRunning && (
                        <span
                            className="font-mono"
                            title={`FPS médio: ${stats?.fpsavg?.toFixed(1) || 'N/A'} | FPS atual: ${stats?.fps_current?.toFixed(1) || 'N/A'}`}
                        >
                            {displayFps} FPS
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}
