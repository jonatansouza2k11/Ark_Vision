// frontend/src/components/dashboard/StreamControls.tsx
// v3.0 - Controles de Stream (Start / Pause / Stop)
//
// RESPONSABILIDADE:
// - Mostrar botões corretos conforme system_status global
// - Proteger contra cliques repetidos (debounce + isProcessing)
// - Delegar ações para useStreamControl

import { useState, useRef, useEffect } from 'react';
import { Play, Pause, Square } from 'lucide-react';

import { useStreamControl } from '../../hooks/useStreamControl';
import { useYOLOStream } from '../../hooks/useYOLOStream';

export default function StreamControls() {
    // Stats globais do stream (vêm de /api/v1/stream/status)
    const { stats } = useYOLOStream(2000, true);

    // Ações de controle (start / pause / stop)
    const { startStream, pauseStream, stopStream, isProcessing } =
        useStreamControl();

    // Debounce simples para evitar cliques muito rápidos
    const [isDebouncing, setIsDebouncing] = useState(false);
    const debounceTimerRef = useRef<number | null>(null);

    useEffect(() => {
        return () => {
            if (debounceTimerRef.current) {
                window.clearTimeout(debounceTimerRef.current);
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

        debounceTimerRef.current = window.setTimeout(() => {
            setIsDebouncing(false);
        }, 500);
    };

    // Derivar estado global do sistema
    const systemStatus: string = stats?.system_status || 'stopped';
    const isRunning = systemStatus === 'running';
    const isPaused = systemStatus === 'paused';
    const isStopped = systemStatus === 'stopped';

    const isDisabled = isProcessing || isDebouncing;

    return (
        <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-800">
                Controles de Stream
            </h3>

            <div className="flex flex-col gap-2">
                {/* INICIAR - só aparece quando stopped */}
                {isStopped && (
                    <button
                        type="button"
                        onClick={() => handleAction(startStream)}
                        disabled={isDisabled}
                        className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${isDisabled
                                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                : 'bg-green-600 text-white hover:bg-green-700'
                            }`}
                    >
                        <Play className="h-4 w-4" />
                        {isProcessing ? 'Iniciando...' : 'Iniciar'}
                    </button>
                )}

                {/* PAUSAR/RETOMAR - aparece quando running ou paused */}
                {(isRunning || isPaused) && (
                    <button
                        type="button"
                        onClick={() => handleAction(pauseStream)}
                        disabled={isDisabled}
                        className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${isDisabled
                                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                : 'bg-yellow-600 text-white hover:bg-yellow-700'
                            }`}
                    >
                        <Pause className="h-4 w-4" />
                        {isPaused ? (
                            <span>{isProcessing ? 'Retomando...' : 'Retomar'}</span>
                        ) : (
                            <span>{isProcessing ? 'Pausando...' : 'Pausar'}</span>
                        )}
                    </button>
                )}

                {/* PARAR - aparece quando running ou paused */}
                {(isRunning || isPaused) && (
                    <button
                        type="button"
                        onClick={() => handleAction(stopStream)}
                        disabled={isDisabled}
                        className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${isDisabled
                                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                : 'bg-red-600 text-white hover:bg-red-700'
                            }`}
                    >
                        <Square className="h-4 w-4" />
                        {isProcessing ? 'Parando...' : 'Parar'}
                    </button>
                )}
            </div>

            {/* Status textual */}
            <div className="text-xs text-gray-600">
                <span className="font-medium">Status:</span>{' '}
                {systemStatus === 'running' && 'Rodando'}
                {systemStatus === 'paused' && 'Pausado'}
                {systemStatus === 'stopped' && 'Parado'}
            </div>
        </div>
    );
}
