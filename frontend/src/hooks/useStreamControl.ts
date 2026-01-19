// frontend/src/hooks/useStreamControl.ts
// v2.1 - Stream Control Hook (start / pause / stop)
//
// RESPONSABILIDADE:
// - Encapsular chamadas ao backend de stream
// - Gerenciar estado de "processando" para evitar cliques repetidos
// - Integrar com React Query para invalidar stats após mudanças

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { streamAPI, type StreamControlResponse } from '../services/streamApi';
import { useToast } from './useToast';

/**
 * Hook personalizado para controlar o stream YOLO.
 * Gerencia os estados de iniciar, pausar/retomar e parar o stream.
 */
export function useStreamControl() {
    const [isProcessing, setIsProcessing] = useState(false);
    const queryClient = useQueryClient();
    const { showToast } = useToast();

    // ========================================================================
    // START STREAM
    // ========================================================================
    const startMutation = useMutation({
        mutationFn: async () => {
            setIsProcessing(true);
            const response = await streamAPI.start();
            return response.data as StreamControlResponse;
        },
        onSuccess: () => {
            // Stats globais (useYOLOStream) usam a key 'yolo-stats'
            queryClient.invalidateQueries({ queryKey: ['yolo-stats'] });
            showToast('✅ Stream iniciado com sucesso!', 'success');
        },
        onError: (error: any) => {
            const errorMsg =
                error?.response?.data?.detail ||
                error?.message ||
                'Erro ao iniciar stream';
            showToast(`❌ ${errorMsg}`, 'error');
            console.error('Erro ao iniciar stream:', error);
        },
        onSettled: () => {
            setIsProcessing(false);
        },
    });
    

    // ========================================================================
    // PAUSE / RESUME STREAM
    // ========================================================================
    const pauseMutation = useMutation({
        mutationFn: async () => {
            setIsProcessing(true);
            const response = await streamAPI.pause();
            return response.data as StreamControlResponse;
        },
        onSuccess: (data: StreamControlResponse) => {
            queryClient.invalidateQueries({ queryKey: ['yolo-stats'] });

            // data.status e data.paused vêm do backend (/pause)
            const isPaused = data.status === 'paused' || data.paused === true;
            const message = isPaused ? '⏸️ Stream pausado' : '▶️ Stream retomado';

            showToast(message, 'info');
        },
        onError: (error: any) => {
            const errorMsg =
                error?.response?.data?.detail ||
                error?.message ||
                'Erro ao pausar/retomar stream';
            showToast(`❌ ${errorMsg}`, 'error');
            console.error('Erro ao pausar/retomar stream:', error);
        },
        onSettled: () => {
            setIsProcessing(false);
        },
    });


    // ========================================================================
    // STOP STREAM
    // ========================================================================
    const stopMutation = useMutation({
        mutationFn: async () => {
            setIsProcessing(true);
            const response = await streamAPI.stop();
            return response.data as StreamControlResponse;
        },
        onSuccess: () => {
            // ✅ Invalida queries imediatamente
            queryClient.invalidateQueries({ queryKey: ['yolo-stats'] });

            // ✅ Força um refetch adicional após 1 segundo (aguarda backend atualizar)
            setTimeout(() => {
                queryClient.invalidateQueries({ queryKey: ['yolo-stats'] });
                queryClient.refetchQueries({
                    queryKey: ['yolo-stats'],
                    type: 'active'
                });
            }, 1000);

            showToast('⏹️ Stream parado com sucesso!', 'success');
        },
        onError: (error: any) => {
            const errorMsg =
                error?.response?.data?.detail ||
                error?.message ||
                'Erro ao parar stream';
            showToast(`❌ ${errorMsg}`, 'error');
            console.error('Erro ao parar stream:', error);
        },
        onSettled: () => {
            setIsProcessing(false);
        },
    });
    

    // ========================================================================
    // API PÚBLICA DO HOOK
    // ========================================================================
    return {
        isProcessing,
        startStream: startMutation.mutate,
        pauseStream: pauseMutation.mutate,
        stopStream: stopMutation.mutate,
    };
}

export default useStreamControl;
