// frontend/src/hooks/useToast.ts
import { useContext } from 'react';
import { ToastContext, ToastContextType, ToastNotification } from '../contexts/ToastContext';

/**
 * Interface de retorno do hook useToast
 * Define todas as funções disponíveis para gerenciar notificações
 */
export interface UseToastReturn {
    toasts: ToastNotification[];
    success: (message: string, duration?: number) => void;
    error: (message: string, duration?: number) => void;
    info: (message: string, duration?: number) => void;
    warning: (message: string, duration?: number) => void;
    showToast: (message: string, type?: 'success' | 'error' | 'warning' | 'info', duration?: number) => void;
    removeToast: (id: string) => void;
}

/**
 * Hook personalizado para gerenciar notificações Toast
 * 
 * @returns {UseToastReturn} Objeto com funções e estado de toasts
 * @throws {Error} Se usado fora do ToastProvider
 * 
 * @example
 * const { success, error, info, warning } = useToast();
 * success('Operação bem-sucedida!');
 * error('Algo deu errado!');
 */
export function useToast(): UseToastReturn {
    const context = useContext(ToastContext);

    if (context === undefined) {
        throw new Error('useToast must be used within ToastProvider');
    }

    // ========================================
    // HELPER METHODS - Atalhos para tipos específicos
    // ========================================

    /**
     * Exibe toast de sucesso
     */
    const success = (message: string, duration?: number) => {
        context.showToast(message, 'success', duration);
    };

    /**
     * Exibe toast de erro
     */
    const error = (message: string, duration?: number) => {
        context.showToast(message, 'error', duration);
    };

    /**
     * Exibe toast informativo
     */
    const info = (message: string, duration?: number) => {
        context.showToast(message, 'info', duration);
    };

    /**
     * Exibe toast de aviso
     */
    const warning = (message: string, duration?: number) => {
        context.showToast(message, 'warning', duration);
    };

    // ========================================
    // RETORNA API PÚBLICA DO HOOK
    // ========================================
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
