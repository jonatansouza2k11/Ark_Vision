// frontend/src/components/users/UserBulkActions.tsx
/**
 * ============================================================================
 * USER BULK ACTIONS - v3.0 NEW COMPONENT
 * ============================================================================
 * ➕ v3.0: Componente para ações em lote
 * Features: Delete, Export, Role change, Status update
 */

import { Trash2, Download, Shield, UserX, CheckSquare, Square } from 'lucide-react';
import { User } from '../../types/user';

// ============================================================================
// INTERFACE
// ============================================================================

interface UserBulkActionsProps {
    selectedUsers: User[];
    selectedUserIds: number[];
    allUsers: User[];
    onDelete: () => void;
    onExport: (format: 'json' | 'csv') => void;
    onSelectAll: () => void;
    onDeselectAll: () => void;
    isDeleting?: boolean;
    isExporting?: boolean;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function UserBulkActions({
    selectedUsers,
    selectedUserIds,
    allUsers,
    onDelete,
    onExport,
    onSelectAll,
    onDeselectAll,
    isDeleting = false,
    isExporting = false,
}: UserBulkActionsProps) {
    // ============================================================================
    // COMPUTED VALUES
    // ============================================================================

    const selectedCount = selectedUserIds.length;
    const totalCount = allUsers.length;
    const isAllSelected = selectedCount === totalCount && totalCount > 0;
    const hasSelection = selectedCount > 0;

    /**
     * Calcula estatísticas dos usuários selecionados
     */
    const getSelectionStats = () => {
        const adminCount = selectedUsers.filter((u) => u.role === 'admin').length;
        const userCount = selectedUsers.filter((u) => u.role === 'user').length;

        return { adminCount, userCount };
    };

    const stats = getSelectionStats();

    // ============================================================================
    // RENDER
    // ============================================================================

    if (!hasSelection) return null;

    return (
        <div className="bg-purple-50 border-2 border-purple-300 rounded-lg shadow-lg animate-slideDown">
            {/* ========== HEADER BAR ========== */}
            <div className="px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                {/* Left: Selection Info */}
                <div className="flex items-center gap-4">
                    {/* Selection Icon */}
                    <div className="flex-shrink-0 w-12 h-12 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold shadow-md">
                        {selectedCount}
                    </div>

                    {/* Info Text */}
                    <div>
                        <h3 className="text-lg font-semibold text-purple-900">
                            {selectedCount} usuário(s) selecionado(s)
                        </h3>
                        <div className="flex items-center gap-3 text-sm text-purple-700 mt-1">
                            {stats.adminCount > 0 && (
                                <span className="flex items-center gap-1">
                                    <Shield className="w-3 h-3" />
                                    {stats.adminCount} admin(s)
                                </span>
                            )}
                            {stats.userCount > 0 && (
                                <span className="flex items-center gap-1">
                                    <UserX className="w-3 h-3" />
                                    {stats.userCount} user(s)
                                </span>
                            )}
                            <button
                                onClick={isAllSelected ? onDeselectAll : onSelectAll}
                                className="text-xs text-purple-600 hover:text-purple-800 underline font-medium ml-2"
                            >
                                {isAllSelected ? 'Desselecionar Todos' : `Selecionar Todos (${totalCount})`}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Right: Actions */}
                <div className="flex flex-wrap gap-2 w-full sm:w-auto">
                    {/* Export Dropdown */}
                    <div className="relative group">
                        <button
                            disabled={isExporting}
                            className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-purple-300 text-purple-700 rounded-lg hover:bg-purple-50 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                        >
                            <Download className="w-4 h-4" />
                            {isExporting ? 'Exportando...' : 'Exportar'}
                        </button>

                        {/* Dropdown Menu */}
                        {!isExporting && (
                            <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-20">
                                <button
                                    onClick={() => onExport('json')}
                                    className="w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-50 rounded-t-lg flex items-center gap-2 text-sm"
                                >
                                    <span>📄</span>
                                    Exportar como JSON
                                </button>
                                <button
                                    onClick={() => onExport('csv')}
                                    className="w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-50 rounded-b-lg flex items-center gap-2 text-sm"
                                >
                                    <span>📊</span>
                                    Exportar como CSV
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Delete Button */}
                    <button
                        onClick={onDelete}
                        disabled={isDeleting}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                        <Trash2 className="w-4 h-4" />
                        {isDeleting ? (
                            <span className="flex items-center gap-2">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                Deletando...
                            </span>
                        ) : (
                            'Deletar'
                        )}
                    </button>

                    {/* Cancel Button */}
                    <button
                        onClick={onDeselectAll}
                        disabled={isDeleting}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                        Cancelar
                    </button>
                </div>
            </div>

            {/* ========== DETAILS BAR (Opcional - mostra usuários selecionados) ========== */}
            {selectedCount <= 5 && (
                <div className="px-6 pb-4">
                    <div className="bg-white rounded-lg p-3 border border-purple-200">
                        <p className="text-xs font-medium text-gray-600 mb-2">Usuários selecionados:</p>
                        <div className="flex flex-wrap gap-2">
                            {selectedUsers.map((user) => (
                                <span
                                    key={user.id}
                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-100 text-purple-800 rounded-full text-xs font-medium"
                                >
                                    <div className="w-5 h-5 rounded-full bg-purple-600 flex items-center justify-center text-white text-xs font-bold">
                                        {user.username.charAt(0).toUpperCase()}
                                    </div>
                                    {user.username}
                                    {user.role === 'admin' && (
                                        <Shield className="w-3 h-3 text-purple-600" />
                                    )}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* ========== WARNING BAR ========== */}
            <div className="bg-purple-100 border-t-2 border-purple-200 px-6 py-3 rounded-b-lg">
                <div className="flex items-center justify-between text-xs">
                    <span className="text-purple-800 font-medium">
                        ⚠️ Ações em lote afetarão todos os usuários selecionados
                    </span>
                    <span className="text-purple-600">
                        {selectedCount} de {totalCount} selecionados ({Math.round((selectedCount / totalCount) * 100)}%)
                    </span>
                </div>
            </div>
        </div>
    );
}
