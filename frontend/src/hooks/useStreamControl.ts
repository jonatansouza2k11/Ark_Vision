// frontend/src/hooks/useStreamControl.ts
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { streamAPI, StreamControlResponse } from '../services/streamApi';
import { useToast } from './useToast';

/**
 * Hook personalizado para controlar o stream YOLO
 * Gerencia os estados de iniciar, pausar/retomar e parar o stream
 */
export function useStreamControl() {
    const [isProcessing, setIsProcessing] = useState(false);
    const queryClient = useQueryClient();
    const { showToast } = useToast();

    // ========================================
    // START STREAM
    // ========================================
    const startMutation = useMutation({
        mutationFn: async () => {
            setIsProcessing(true);
            const response = await streamAPI.start();
            return response.data; // ✅ response.data é do tipo StreamControlResponse
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['yolo-stats'] });
            showToast('✅ Stream iniciado com sucesso!', 'success');
        },
        onError: (error: any) => {
            const errorMsg = error.response?.data?.detail || error.message || 'Erro ao iniciar stream';
            showToast(`❌ ${errorMsg}`, 'error');
            console.error('Erro ao iniciar stream:', error);
        },
        onSettled: () => {
            setIsProcessing(false);
        },
    });

    // ========================================
    // PAUSE/RESUME STREAM
    // ========================================
    const pauseMutation = useMutation({
        mutationFn: async () => {
            setIsProcessing(true);
            const response = await streamAPI.pause();
            return response.data; // ✅ response.data é do tipo StreamControlResponse
        },
        onSuccess: (data: StreamControlResponse) => {
            queryClient.invalidateQueries({ queryKey: ['yolo-stats'] });

            // ✅ AGORA FUNCIONA: data tem status e paused
            const isPaused = data.status === 'paused' || data.paused === true;
            const message = isPaused ? '⏸️ Stream pausado' : '▶️ Stream retomado';

            showToast(message, 'info');
        },
        onError: (error: any) => {
            const errorMsg = error.response?.data?.detail || error.message || 'Erro ao pausar/retomar stream';
            showToast(`❌ ${errorMsg}`, 'error');
            console.error('Erro ao pausar/retomar stream:', error);
        },
        onSettled: () => {
            setIsProcessing(false);
        },
    });

    // ========================================
    // STOP STREAM
    // ========================================
    const stopMutation = useMutation({
        mutationFn: async () => {
            setIsProcessing(true);
            const response = await streamAPI.stop();
            return response.data; // ✅ response.data é do tipo StreamControlResponse
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['yolo-stats'] });
            showToast('⏹️ Stream parado com sucesso!', 'success');
        },
        onError: (error: any) => {
            const errorMsg = error.response?.data?.detail || error.message || 'Erro ao parar stream';
            showToast(`❌ ${errorMsg}`, 'error');
            console.error('Erro ao parar stream:', error);
        },
        onSettled: () => {
            setIsProcessing(false);
        },
    });

    // ========================================
    
    // RETORNA API PÚBLICA DO HOOK
    // ========================================
    return {
        isProcessing,
        startStream: startMutation.mutate,
        pauseStream: pauseMutation.mutate,
        stopStream: stopMutation.mutate,
    };
}
