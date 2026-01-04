import { createContext, useState, useCallback, ReactNode } from 'react';

// ============================================
// 📦 TYPES
// ============================================
export interface ToastNotification {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
    duration?: number;
}

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
export function ToastProvider({ children }: ToastProviderProps) {
    const [toasts, setToasts] = useState<ToastNotification[]>([]);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, []);

    const showToast = useCallback(
        (message: string, type: ToastNotification['type'] = 'info', duration = 3000) => {
            const id = `toast-${Date.now()}-${Math.random()}`;
            const newToast: ToastNotification = { id, message, type, duration };

            setToasts((prev) => [...prev, newToast]);

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
