// frontend/src/components/users/DeleteUserDialog.tsx
/**
 * ============================================================================
 * DELETE USER DIALOG - v2.0 MANTIDO + UX IMPROVEMENTS
 * ============================================================================
 * ✅ v2.0: Funcionalidade original mantida
 * ➕ Melhorias: Better UX, animations, confirmação por digitação
 */

import { useState } from 'react';
import { X, AlertTriangle, Trash2 } from 'lucide-react';
import { User } from '../../types/user';

// ============================================================================
// INTERFACE
// ============================================================================

interface DeleteUserDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => Promise<void>;
    user: User | null;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function DeleteUserDialog({
    isOpen,
    onClose,
    onConfirm,
    user,
}: DeleteUserDialogProps) {
    // ============================================================================
    // STATE
    // ============================================================================

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // ➕ NEW: Confirmação por digitação (opcional, desabilitado por padrão)
    const [confirmText, setConfirmText] = useState('');
    const [requireTyping, setRequireTyping] = useState(true); // Toggle para ativar

    // ============================================================================
    // HANDLERS
    // ============================================================================

    /**
     * ✅ v2.0: Handle confirm (mantido + melhorias)
     */
    const handleConfirm = async () => {
        if (loading) return;

        // ➕ Validação de digitação (se ativada)
        if (requireTyping && confirmText.toLowerCase() !== 'deletar') {
            setError('Digite "deletar" para confirmar');
            return;
        }

        try {
            setLoading(true);
            setError('');

            await onConfirm();

            // ✅ Reset e fechar após sucesso
            setTimeout(() => {
                setLoading(false);
                setConfirmText('');
                onClose();
            }, 500);
        } catch (err: any) {
            const errorMessage =
                err?.response?.data?.detail || err?.message || 'Erro ao deletar usuário';
            setError(errorMessage);
            setLoading(false);
        }
    };

    /**
     * ➕ NEW: Handle close (reset state)
     */
    const handleClose = () => {
        if (!loading) {
            setConfirmText('');
            setError('');
            onClose();
        }
    };

    // ============================================================================
    // RENDER
    // ============================================================================

    if (!isOpen || !user) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 animate-fadeIn">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-md animate-slideUp">
                {/* ========== HEADER ========== */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                            <AlertTriangle className="w-5 h-5 text-red-600" />
                        </div>
                        <h2 className="text-xl font-semibold text-gray-900">Confirmar Exclusão</h2>
                    </div>
                    <button
                        onClick={handleClose}
                        disabled={loading}
                        className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* ========== CONTENT ========== */}
                <div className="p-6 space-y-4">
                    {/* Warning Message */}
                    <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
                        <p className="text-gray-800">
                            Tem certeza que deseja deletar o usuário{' '}
                            <span className="font-bold text-red-600">{user.username}</span>?
                        </p>
                        <p className="text-sm text-gray-600 mt-2">
                            <strong className="text-red-700">⚠️ Atenção:</strong> Esta ação não pode ser
                            desfeita. Todos os dados associados a este usuário serão permanentemente removidos.
                        </p>
                    </div>

                    {/* User Info Card */}
                    <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                        <div className="flex justify-between">
                            <span className="text-gray-600">Username:</span>
                            <span className="font-medium text-gray-900">{user.username}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-600">Email:</span>
                            <span className="font-medium text-gray-900">{user.email}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-600">Permissão:</span>
                            <span
                                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${user.role === 'admin'
                                        ? 'bg-purple-100 text-purple-800'
                                        : 'bg-blue-100 text-blue-800'
                                    }`}
                            >
                                {user.role === 'admin' ? 'Admin' : 'User'}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-600">Criado em:</span>
                            <span className="font-medium text-gray-900">
                                {new Date(user.created_at).toLocaleDateString('pt-BR')}
                            </span>
                        </div>
                    </div>

                    {/* ➕ Optional: Confirmation by typing (disabled by default) */}
                    {requireTyping && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Digite <span className="font-bold text-red-600">"deletar"</span> para confirmar:
                            </label>
                            <input
                                type="text"
                                value={confirmText}
                                onChange={(e) => {
                                    setConfirmText(e.target.value);
                                    setError('');
                                }}
                                disabled={loading}
                                placeholder="deletar"
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
                            />
                        </div>
                    )}

                    {/* Error Alert */}
                    {error && (
                        <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm animate-shake">
                            <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Loading Alert */}
                    {loading && (
                        <div className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-sm">
                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 flex-shrink-0"></div>
                            <div>
                                <strong>⚙️ DELETANDO USUÁRIO</strong>
                                <p className="text-xs mt-1">Aguarde... Não feche esta janela</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* ========== ACTIONS ========== */}
                <div className="flex gap-3 px-6 pb-6">
                    <button
                        type="button"
                        onClick={handleClose}
                        disabled={loading}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                    >
                        Cancelar
                    </button>

                    <button
                        type="button"
                        onClick={handleConfirm}
                        disabled={loading || (requireTyping && confirmText.toLowerCase() !== 'deletar')}
                        className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                    >
                        {loading ? (
                            <span className="flex items-center justify-center gap-2">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                DELETANDO...
                            </span>
                        ) : (
                            <span className="flex items-center justify-center gap-2">
                                <Trash2 className="w-4 h-4" />
                                Deletar Usuário
                            </span>
                        )}
                    </button>
                </div>

                {/* ========== FOOTER WARNING ========== */}
                <div className="bg-gray-50 px-6 py-3 rounded-b-lg border-t border-gray-200">
                    <p className="text-xs text-center text-gray-600">
                        ⚠️ Esta ação é <span className="font-semibold text-red-600">irreversível</span>
                    </p>
                </div>
            </div>
        </div>
    );
}
