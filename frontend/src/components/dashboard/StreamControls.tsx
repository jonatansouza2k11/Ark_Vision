// frontend/src/components/dashboard/StreamControls.tsx
import { useState, useRef, useEffect } from 'react';
import { Play, Pause, Square, RotateCcw } from 'lucide-react';
import { useStreamControl } from '../../hooks/useStreamControl';
import { useYOLOStream } from '../../hooks/useYOLOStream';

export default function StreamControls() {
    const { stats } = useYOLOStream(2000, true);
    const { startStream, pauseStream, stopStream, isProcessing } = useStreamControl();

    const [isDebouncing, setIsDebouncing] = useState(false);
    const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, []);

    const handleAction = (action: () => void) => {
        if (isDebouncing || isProcessing) {
            console.log('🚫 Ação bloqueada (debounce ou processando)');
            return;
        }

        setIsDebouncing(true);
        action();

        debounceTimerRef.current = setTimeout(() => {
            setIsDebouncing(false);
        }, 500);
    };

    const systemStatus = stats?.system_status || 'stopped';
    const isRunning = systemStatus === 'running';
    const isPaused = systemStatus === 'paused';
    const isStopped = systemStatus === 'stopped';
    const isDisabled = isProcessing || isDebouncing;

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-4">
                <RotateCcw className="w-5 h-5 text-purple-600" />
                <h3 className="font-semibold text-gray-900 text-sm">Controles de Stream</h3>
            </div>

            <div className="space-y-2">
                {/* INICIAR - só aparece quando stopped */}
                {isStopped && (
                    <button
                        onClick={() => handleAction(startStream)}
                        disabled={isDisabled}
                        className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${isDisabled
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-green-600 text-white hover:bg-green-700'
                            }`}
                    >
                        <Play className="w-4 h-4" />
                        {isProcessing ? 'Iniciando...' : 'Iniciar'}
                    </button>
                )}

                {/* PAUSAR/RETOMAR - aparece quando running ou paused */}
                {(isRunning || isPaused) && (
                    <button
                        onClick={() => handleAction(pauseStream)}
                        disabled={isDisabled}
                        className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${isDisabled
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-yellow-600 text-white hover:bg-yellow-700'
                            }`}
                    >
                        {isPaused ? (
                            <>
                                <Play className="w-4 h-4" />
                                {isProcessing ? 'Retomando...' : 'Retomar'}
                            </>
                        ) : (
                            <>
                                <Pause className="w-4 h-4" />
                                {isProcessing ? 'Pausando...' : 'Pausar'}
                            </>
                        )}
                    </button>
                )}

                {/* PARAR - aparece quando running ou paused */}
                {(isRunning || isPaused) && (
                    <button
                        onClick={() => handleAction(stopStream)}
                        disabled={isDisabled}
                        className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${isDisabled
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-red-600 text-white hover:bg-red-700'
                            }`}
                    >
                        <Square className="w-4 h-4" />
                        {isProcessing ? 'Parando...' : 'Parar'}
                    </button>
                )}
            </div>

            {/* Status visual */}
            <div className="mt-4 pt-3 border-t border-gray-200">
                <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Status:</span>
                    <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${systemStatus === 'running' ? 'bg-green-500 animate-pulse' :
                            systemStatus === 'paused' ? 'bg-yellow-500' :
                                'bg-red-500'
                            }`} />
                        <span className="font-medium text-gray-900">
                            {systemStatus === 'running' && 'Rodando'}
                            {systemStatus === 'paused' && 'Pausado'}
                            {systemStatus === 'stopped' && 'Parado'}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
