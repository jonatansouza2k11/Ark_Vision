import { useContext } from 'react';
import { ToastContext, ToastContextType } from '../contexts/ToastContext';

export function useToast(): ToastContextType {
    const context = useContext(ToastContext);

    if (context === undefined) {
        throw new Error('useToast must be used within ToastProvider');
    }

    return context;
}
