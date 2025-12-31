// src/components/dashboard/VideoStream.tsx
import { useState } from 'react';
import { Play, Pause, Maximize2, RefreshCw } from 'lucide-react';

interface VideoStreamProps {
    streamUrl?: string;
}

export default function VideoStream({ streamUrl }: VideoStreamProps) {
    const [isPlaying, setIsPlaying] = useState(true);
    const [error, setError] = useState(false);
    const defaultStreamUrl = streamUrl || 'http://localhost:8000/video_feed';

    const handleRefresh = () => {
        setError(false);
        setIsPlaying(true);
        const img = document.getElementById('video-stream') as HTMLImageElement;
        if (img) {
            img.src = `${defaultStreamUrl}?t=${Date.now()}`;
        }
    };

    const handleFullscreen = () => {
        const container = document.getElementById('video-container');
        if (container) {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                container.requestFullscreen();
            }
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                    <span className="text-sm font-medium text-gray-700">
                        Stream YOLO em Tempo Real
                    </span>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setIsPlaying(!isPlaying)}
                        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition-colors"
                        title={isPlaying ? 'Pausar' : 'Reproduzir'}
                    >
                        {isPlaying ? (
                            <Pause className="w-4 h-4" />
                        ) : (
                            <Play className="w-4 h-4" />
                        )}
                    </button>

                    <button
                        onClick={handleRefresh}
                        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition-colors"
                        title="Atualizar"
                    >
                        <RefreshCw className="w-4 h-4" />
                    </button>

                    <button
                        onClick={handleFullscreen}
                        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition-colors"
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
                {isPlaying && !error ? (
                    <img
                        id="video-stream"
                        src={defaultStreamUrl}
                        alt="YOLO Video Stream"
                        className="w-full h-full object-contain"
                        onError={() => setError(true)}
                    />
                ) : error ? (
                    <div className="text-center text-white p-8">
                        <p className="text-lg font-semibold mb-2">
                            ⚠️ Erro ao carregar stream
                        </p>
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
                ) : (
                    <div className="text-center text-white p-8">
                        <Play className="w-16 h-16 mx-auto mb-4 opacity-50" />
                        <p className="text-lg font-semibold">Stream pausado</p>
                    </div>
                )}
            </div>

            {/* Footer Info */}
            <div className="px-4 py-2 bg-gray-50 border-t border-gray-200">
                <p className="text-xs text-gray-500 text-center">
                    Detecções em tempo real com YOLOv8
                </p>
            </div>
        </div>
    );
}
