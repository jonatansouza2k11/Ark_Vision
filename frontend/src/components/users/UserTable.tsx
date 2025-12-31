// src/components/users/UserTable.tsx
import { Edit, Trash2, Shield, User as UserIcon, Clock } from 'lucide-react';
import { User } from '../../types/user';

interface UserTableProps {
    users: User[];
    loading: boolean;
    currentUserId?: number;
    isAdmin: boolean;
    onEdit: (user: User) => void;
    onDelete: (user: User) => void;
}

export default function UserTable({
    users,
    loading,
    currentUserId,
    isAdmin,
    onEdit,
    onDelete,
}: UserTableProps) {
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

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (users.length === 0) {
        return (
            <div className="text-center py-12">
                <UserIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">Nenhum usuário encontrado</h3>
                <p className="mt-1 text-sm text-gray-500">Tente ajustar os filtros de busca</p>
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Usuário
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Email
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Role
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Criado em
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Último login
                        </th>
                        {isAdmin && (
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Ações
                            </th>
                        )}
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {users.map((user) => (
                        <tr
                            key={user.id}
                            className="hover:bg-gray-50 transition-colors duration-150"
                        >
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0 h-10 w-10 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center">
                                        <span className="text-white font-semibold text-sm">
                                            {user.username.charAt(0).toUpperCase()}
                                        </span>
                                    </div>
                                    <div className="ml-4">
                                        <div className="text-sm font-medium text-gray-900">
                                            {user.username}
                                            {user.id === currentUserId && (
                                                <span className="ml-2 text-xs text-blue-600 font-semibold">
                                                    (Você)
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-sm text-gray-500">ID: {user.id}</div>
                                    </div>
                                </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm text-gray-900">{user.email}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <span
                                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${user.role === 'admin'
                                        ? 'bg-purple-100 text-purple-800'
                                        : 'bg-gray-100 text-gray-800'
                                        }`}
                                >
                                    {user.role === 'admin' && <Shield className="w-3 h-3" />}
                                    {user.role === 'admin' ? 'Admin' : 'User'}
                                </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                <div className="flex items-center gap-1">
                                    <Clock className="w-4 h-4" />
                                    {formatDate(user.created_at)}
                                </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {formatDate(user.last_login)}
                            </td>
                            {isAdmin && (
                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                    <div className="flex items-center justify-end gap-2">
                                        <button
                                            onClick={() => onEdit(user)}
                                            className="text-blue-600 hover:text-blue-900 transition-colors p-1 hover:bg-blue-50 rounded"
                                            title="Editar"
                                        >
                                            <Edit className="w-4 h-4" />
                                        </button>
                                        {user.id !== currentUserId && (
                                            <button
                                                onClick={() => onDelete(user)}
                                                className="text-red-600 hover:text-red-900 transition-colors p-1 hover:bg-red-50 rounded"
                                                title="Deletar"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        )}
                                    </div>
                                </td>
                            )}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
