// frontend/src/contexts/ToastContext.tsx
import { createContext, useState, useCallback, ReactNode } from 'react';

// ============================================
// 📦 TYPES
// ============================================

/**
 * Interface para uma notificação toast individual
 */
export interface ToastNotification {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
    duration?: number;
}

/**
 * Interface do contexto de Toast
 */
export interface ToastContextType {
    toasts: ToastNotification[];
    showToast: (message: string, type?: ToastNotification['type'], duration?: number) => void;
    removeToast: (id: string) => void;
}

// ============================================
// 🎯 CONTEXT
// ============================================

export const ToastContext = createContext<ToastContextType | undefined>(undefined);

export interface ToastProviderProps {
    children: ReactNode;
}

// ============================================
// 🚀 PROVIDER
// ============================================

/**
 * Provider do contexto de Toast
 * Gerencia o estado global das notificações toast
 * 
 * @example
 * <ToastProvider>
 *   <App />
 * </ToastProvider>
 */
export function ToastProvider({ children }: ToastProviderProps) {
    const [toasts, setToasts] = useState<ToastNotification[]>([]);

    /**
     * Remove um toast específico pelo ID
     */
    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, []);

    /**
     * Exibe um novo toast
     * @param message - Mensagem a ser exibida
     * @param type - Tipo do toast (success, error, warning, info)
     * @param duration - Duração em ms (0 = sem auto-close)
     */
    const showToast = useCallback(
        (message: string, type: ToastNotification['type'] = 'info', duration = 3000) => {
            const id = `toast-${Date.now()}-${Math.random()}`;
            const newToast: ToastNotification = { id, message, type, duration };

            setToasts((prev) => [...prev, newToast]);

            // Auto-remove após a duração especificada
            if (duration > 0) {
                setTimeout(() => {
                    removeToast(id);
                }, duration);
            }
        },
        [removeToast]
    );

    const value: ToastContextType = {
        toasts,
        showToast,
        removeToast,
    };

    return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}
