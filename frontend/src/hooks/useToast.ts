// frontend/src/hooks/useToast.ts

import { useContext } from 'react';
import { ToastContext, ToastContextType, ToastNotification } from '../contexts/ToastContext';

export interface UseToastReturn {
    toasts: ToastNotification[]; // ✅ ADICIONAR ESTA LINHA
    success: (message: string, duration?: number) => void;
    error: (message: string, duration?: number) => void;
    info: (message: string, duration?: number) => void;
    warning: (message: string, duration?: number) => void;
    showToast: (message: string, type?: 'success' | 'error' | 'warning' | 'info', duration?: number) => void;
    removeToast: (id: string) => void;
}

export function useToast(): UseToastReturn {
    const context = useContext(ToastContext);

    if (context === undefined) {
        throw new Error('useToast must be used within ToastProvider');
    }

    // ✅ HELPER METHODS
    const success = (message: string, duration?: number) => {
        context.showToast(message, 'success', duration);
    };

    const error = (message: string, duration?: number) => {
        context.showToast(message, 'error', duration);
    };

    const info = (message: string, duration?: number) => {
        context.showToast(message, 'info', duration);
    };

    const warning = (message: string, duration?: number) => {
        context.showToast(message, 'warning', duration);
    };

    return {
        toasts: context.toasts,
        success,
        error,
        info,
        warning,
        showToast: context.showToast,
        removeToast: context.removeToast,
    };
}
