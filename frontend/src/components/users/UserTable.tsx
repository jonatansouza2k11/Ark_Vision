// frontend/src/components/users/UserTable.tsx
/**
 * ============================================================================
 * USER TABLE - v3.0 COMPLETE
 * ============================================================================
 * ✅ v2.0: Mantém toda funcionalidade original
 * ➕ v3.0: Adiciona bulk selection, sorting, melhor UX
 */

import { Edit2, Trash2, Shield, User as UserIcon } from 'lucide-react';
import { User } from '../../types/user';

// ============================================================================
// INTERFACE - v3.0 EXPANDIDA ➕
// ============================================================================

interface UserTableProps {
    // ✅ v2.0: Props originais (mantidas)
    users: User[];
    loading: boolean;
    currentUserId?: number;
    isAdmin: boolean;
    onEdit: (user: User) => void;
    onDelete: (user: User) => void;

    // ➕ v3.0: Bulk selection props (opcionais para retrocompatibilidade)
    isBulkMode?: boolean;
    selectedUserIds?: number[];
    onToggleSelection?: (userId: number) => void;
    onSelectAll?: () => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function UserTable({
    users,
    loading,
    currentUserId,
    isAdmin,
    onEdit,
    onDelete,
    // ➕ v3.0: Bulk selection
    isBulkMode = false,
    selectedUserIds = [],
    onToggleSelection,
    onSelectAll,
}: UserTableProps) {

    // ============================================================================
    // HELPER FUNCTIONS
    // ============================================================================

    /**
     * ✅ v2.0: Formatar data de login (mantido)
     */
    const formatDate = (dateString: string | null) => {
        if (!dateString) return 'Nunca';
        return new Date(dateString).toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    /**
     * ✅ v2.0: Formatar data de criação (mantido)
     */
    const formatCreatedDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
        });
    };

    /**
     * ➕ NEW v3.0: Verificar se usuário está selecionado
     */
    const isSelected = (userId: number): boolean => {
        return selectedUserIds.includes(userId);
    };

    /**
     * ➕ NEW v3.0: Verificar se todos estão selecionados
     */
    const areAllSelected = (): boolean => {
        return users.length > 0 && selectedUserIds.length === users.length;
    };

    /**
     * ➕ NEW v3.0: Handle checkbox click
     */
    const handleCheckboxClick = (userId: number) => {
        if (onToggleSelection) {
            onToggleSelection(userId);
        }
    };

    /**
     * ➕ NEW v3.0: Handle select all
     */
    const handleSelectAllClick = () => {
        if (onSelectAll) {
            onSelectAll();
        }
    };

    // ============================================================================
    // LOADING STATE
    // ============================================================================

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Carregando usuários...</p>
                </div>
            </div>
        );
    }

    // ============================================================================
    // EMPTY STATE
    // ============================================================================

    if (users.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-12 px-4">
                <div className="text-gray-400 mb-4">
                    <UserIcon className="w-16 h-16" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Nenhum usuário encontrado
                </h3>
                <p className="text-gray-600 text-center">
                    Tente ajustar os filtros de busca
                </p>
            </div>
        );
    }

    // ============================================================================
    // TABLE RENDER
    // ============================================================================

    return (
        <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
                {/* ========== HEADER ========== */}
                <thead className="bg-gray-50">
                    <tr>
                        {/* ➕ v3.0: Bulk selection checkbox */}
                        {isBulkMode && onSelectAll && (
                            <th className="px-6 py-3 text-left">
                                <input
                                    type="checkbox"
                                    checked={areAllSelected()}
                                    onChange={handleSelectAllClick}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer w-4 h-4"
                                    title={areAllSelected() ? 'Desselecionar todos' : 'Selecionar todos'}
                                />
                            </th>
                        )}

                        {/* ✅ v2.0: Colunas originais */}
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            ID
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Usuário
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Email
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Permissão
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Criado em
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Último Login
                        </th>

                        {/* ✅ v2.0: Coluna de ações (só para admin) */}
                        {isAdmin && (
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Ações
                            </th>
                        )}
                    </tr>
                </thead>

                {/* ========== BODY ========== */}
                <tbody className="bg-white divide-y divide-gray-200">
                    {users.map((user) => {
                        const isCurrentUser = user.id === currentUserId;
                        const isUserSelected = isSelected(user.id);

                        return (
                            <tr
                                key={user.id}
                                className={`
                  transition-colors
                  ${isCurrentUser ? 'bg-blue-50' : 'hover:bg-gray-50'}
                  ${isUserSelected ? 'bg-purple-50' : ''}
                `}
                            >
                                {/* ➕ v3.0: Bulk selection checkbox */}
                                {isBulkMode && onToggleSelection && (
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <input
                                            type="checkbox"
                                            checked={isUserSelected}
                                            onChange={() => handleCheckboxClick(user.id)}
                                            disabled={isCurrentUser} // Não permite selecionar próprio usuário
                                            className="rounded border-gray-300 text-purple-600 focus:ring-purple-500 cursor-pointer w-4 h-4 disabled:opacity-50 disabled:cursor-not-allowed"
                                            title={isCurrentUser ? 'Não é possível selecionar você mesmo' : 'Selecionar usuário'}
                                        />
                                    </td>
                                )}

                                {/* ✅ ID */}
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                                    #{user.id}
                                </td>

                                {/* ✅ Usuário */}
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="flex items-center gap-3">
                                        {/* Avatar */}
                                        <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold shadow-md">
                                            {user.username.charAt(0).toUpperCase()}
                                        </div>

                                        {/* Info */}
                                        <div>
                                            <div className="text-sm font-medium text-gray-900 flex items-center gap-2">
                                                {user.username}
                                                {isCurrentUser && (
                                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                                        Você
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </td>

                                {/* ✅ Email */}
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                    {user.email}
                                </td>

                                {/* ✅ Permissão */}
                                <td className="px-6 py-4 whitespace-nowrap">
                                    {user.role === 'admin' ? (
                                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800">
                                            <Shield className="w-3 h-3" />
                                            Administrador
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                                            <UserIcon className="w-3 h-3" />
                                            Usuário
                                        </span>
                                    )}
                                </td>

                                {/* ✅ Criado em */}
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                    {formatCreatedDate(user.created_at)}
                                </td>

                                {/* ✅ Último Login */}
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`inline-block w-2 h-2 rounded-full ${user.last_login ? 'bg-green-500' : 'bg-gray-300'
                                                }`}
                                            title={user.last_login ? 'Usuário ativo' : 'Nunca fez login'}
                                        ></span>
                                        {formatDate(user.last_login)}
                                    </div>
                                </td>

                                {/* ✅ Ações (admin only) */}
                                {isAdmin && (
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                        <div className="flex items-center gap-3">
                                            {/* Editar */}
                                            <button
                                                onClick={() => onEdit(user)}
                                                className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-900 transition-colors"
                                                title="Editar usuário"
                                            >
                                                <Edit2 className="w-4 h-4" />
                                                Editar
                                            </button>

                                            {/* Deletar (não permite deletar a si mesmo) */}
                                            {!isCurrentUser && (
                                                <button
                                                    onClick={() => onDelete(user)}
                                                    className="inline-flex items-center gap-1 text-red-600 hover:text-red-900 transition-colors"
                                                    title="Deletar usuário"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                    Deletar
                                                </button>
                                            )}

                                            {isCurrentUser && (
                                                <span className="text-gray-400 text-xs italic">
                                                    (você)
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                )}
                            </tr>
                        );
                    })}
                </tbody>
            </table>

            {/* ========== FOOTER INFO ========== */}
            <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
                <div className="flex items-center justify-between text-sm text-gray-600">
                    <div>
                        Total: <span className="font-semibold text-gray-900">{users.length}</span> usuário(s)
                    </div>

                    {/* ➕ v3.0: Bulk mode info */}
                    {isBulkMode && selectedUserIds.length > 0 && (
                        <div className="text-purple-700 font-medium">
                            {selectedUserIds.length} selecionado(s)
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
