// src/components/users/DeleteUserDialog.tsx
import { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { User } from '../../types/user';

interface DeleteUserDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => Promise<void>;
    user: User | null;
}

export default function DeleteUserDialog({
    isOpen,
    onClose,
    onConfirm,
    user,
}: DeleteUserDialogProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleConfirm = async () => {
        setError('');
        setLoading(true);

        try {
            await onConfirm();
            onClose();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Erro ao deletar usuário');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen || !user) return null;

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex min-h-screen items-center justify-center p-4">
                {/* Backdrop */}
                <div
                    className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
                    onClick={onClose}
                />

                {/* Dialog */}
                <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 animate-fadeIn">
                    {/* Icon */}
                    <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full mb-4">
                        <AlertTriangle className="w-6 h-6 text-red-600" />
                    </div>

                    {/* Content */}
                    <div className="text-center mb-6">
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                            Deletar Usuário
                        </h3>
                        <p className="text-sm text-gray-600">
                            Tem certeza que deseja deletar o usuário{' '}
                            <span className="font-semibold">{user.username}</span>?
                        </p>
                        <p className="text-sm text-gray-500 mt-2">
                            Esta ação não pode ser desfeita.
                        </p>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                            <p className="text-sm text-red-600">{error}</p>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                            disabled={loading}
                        >
                            Cancelar
                        </button>
                        <button
                            type="button"
                            onClick={handleConfirm}
                            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={loading}
                        >
                            {loading ? 'Deletando...' : 'Deletar'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
