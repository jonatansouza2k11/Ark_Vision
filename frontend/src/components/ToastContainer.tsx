import { useToast } from '../hooks/useToast';
import type { ToastNotification } from '../contexts/ToastContext';

export default function ToastContainer() {
    const { toasts, removeToast } = useToast();

    if (toasts.length === 0) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-md">
            {toasts.map((toast: ToastNotification) => (
                <div
                    key={toast.id}
                    className={`
            min-w-[300px] p-4 rounded-lg shadow-lg flex items-center gap-3
            animate-slide-in transition-all
            ${toast.type === 'success'
                            ? 'bg-green-600'
                            : toast.type === 'error'
                                ? 'bg-red-600'
                                : toast.type === 'warning'
                                    ? 'bg-yellow-600'
                                    : 'bg-blue-600'
                        }
            text-white
          `}
                    role="alert"
                >
                    <span className="text-2xl" aria-hidden="true">
                        {toast.type === 'success' && '✅'}
                        {toast.type === 'error' && '❌'}
                        {toast.type === 'warning' && '⚠️'}
                        {toast.type === 'info' && 'ℹ️'}
                    </span>
                    <span className="flex-1 text-sm font-medium">{toast.message}</span>
                    <button
                        onClick={() => removeToast(toast.id)}
                        className="text-white hover:text-gray-200 font-bold text-xl leading-none"
                        aria-label="Fechar notificação"
                    >
                        ×
                    </button>
                </div>
            ))}
        </div>
    );
}
