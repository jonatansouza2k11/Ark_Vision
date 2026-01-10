// frontend/src/components/ToastContainer.tsx
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';
import { useToast } from '../hooks/useToast';
import type { ToastNotification } from '../contexts/ToastContext';

/**
 * Configurações de estilo por tipo de toast
 */
const toastStyles = {
    success: {
        bg: 'bg-green-50',
        border: 'border-green-500',
        text: 'text-green-800',
        icon: CheckCircle,
        iconColor: 'text-green-500',
    },
    error: {
        bg: 'bg-red-50',
        border: 'border-red-500',
        text: 'text-red-800',
        icon: XCircle,
        iconColor: 'text-red-500',
    },
    warning: {
        bg: 'bg-yellow-50',
        border: 'border-yellow-500',
        text: 'text-yellow-800',
        icon: AlertCircle,
        iconColor: 'text-yellow-500',
    },
    info: {
        bg: 'bg-blue-50',
        border: 'border-blue-500',
        text: 'text-blue-800',
        icon: Info,
        iconColor: 'text-blue-500',
    },
};

/**
 * Componente individual de Toast
 */
function ToastItem({ toast, onRemove }: { toast: ToastNotification; onRemove: (id: string) => void }) {
    const style = toastStyles[toast.type];
    const Icon = style.icon;

    return (
        <div
            className={`
        ${style.bg} ${style.border} ${style.text}
        flex items-start gap-3 p-4 rounded-lg shadow-lg border-l-4
        animate-in slide-in-from-right duration-300
        max-w-md w-full
      `}
            role="alert"
        >
            {/* Ícone */}
            <Icon className={`h-5 w-5 ${style.iconColor} flex-shrink-0 mt-0.5`} />

            {/* Mensagem */}
            <p className="flex-1 text-sm font-medium leading-relaxed">{toast.message}</p>

            {/* Botão fechar */}
            <button
                onClick={() => onRemove(toast.id)}
                className={`${style.iconColor} hover:opacity-70 transition-opacity flex-shrink-0`}
                aria-label="Fechar notificação"
            >
                <X className="h-4 w-4" />
            </button>
        </div>
    );
}

/**
 * Container de Toasts
 * Renderiza todas as notificações ativas no canto superior direito
 */
export default function ToastContainer() {
    const { toasts, removeToast } = useToast();

    // ✅ Proteção: não renderiza nada se não houver toasts
    if (!toasts || toasts.length === 0) return null;

    return (
        <div
            className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none"
            aria-live="polite"
            aria-atomic="true"
        >
            {toasts.map((toast) => (
                <div key={toast.id} className="pointer-events-auto">
                    <ToastItem toast={toast} onRemove={removeToast} />
                </div>
            ))}
        </div>
    );
}
