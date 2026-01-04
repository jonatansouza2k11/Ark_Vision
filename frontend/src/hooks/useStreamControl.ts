// frontend/src/hooks/useStreamControl.ts
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { streamAPI } from '../services/streamApi';
import { useToast } from './useToast';

export function useStreamControl() {
    const [isProcessing, setIsProcessing] = useState(false);
    const queryClient = useQueryClient();
    const { showToast } = useToast();

    // START
    const startMutation = useMutation({
        mutationFn: async () => {
            setIsProcessing(true);
            const response = await streamAPI.start();
            return response.data;
        },
        onSuccess: () => {
            // Força atualização do status
            queryClient.invalidateQueries({ queryKey: ['yolo-stats'] });
            showToast('Stream iniciado!', 'success');
        },
        onError: (error: any) => {
            showToast(error.message || 'Erro ao iniciar', 'error');
        },
        onSettled: () => {
            setIsProcessing(false);
        },
    });

    // PAUSE/RESUME
    const pauseMutation = useMutation({
        mutationFn: async () => {
            setIsProcessing(true);
            const response = await streamAPI.pause();
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['yolo-stats'] });
            showToast('Status alterado!', 'info');
        },
        onError: (error: any) => {
            showToast(error.message || 'Erro ao pausar/retomar', 'error');
        },
        onSettled: () => {
            setIsProcessing(false);
        },
    });

    // STOP
    const stopMutation = useMutation({
        mutationFn: async () => {
            setIsProcessing(true);
            const response = await streamAPI.stop();
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['yolo-stats'] });
            showToast('Stream parado!', 'success');
        },
        onError: (error: any) => {
            showToast(error.message || 'Erro ao parar', 'error');
        },
        onSettled: () => {
            setIsProcessing(false);
        },
    });

    return {
        isProcessing,
        startStream: startMutation.mutate,
        pauseStream: pauseMutation.mutate,
        stopStream: stopMutation.mutate,
    };
}
