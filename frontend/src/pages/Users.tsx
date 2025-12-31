// src/pages/Users.tsx
import { useState, useEffect } from 'react';
import { Plus, Search } from 'lucide-react';
import MainLayout from '../components/layout/MainLayout';
import UserTable from '../components/users/UserTable';
import UserModal from '../components/users/UserModal';
import DeleteUserDialog from '../components/users/DeleteUserDialog';
import { usersApi } from '../api/users';
import { User, UserCreate, UserUpdate } from '../types/user';
import { useAuthStore } from '../store/authStore';

export default function Users() {
  const currentUser = useAuthStore((state) => state.user);
  const [users, setUsers] = useState<User[]>([]);
  const [filteredUsers, setFilteredUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | 'admin' | 'user'>('all');

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);

  // Carregar usuários
  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await usersApi.getAll();
      setUsers(data);
      setFilteredUsers(data);
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  // Filtrar usuários
  useEffect(() => {
    let filtered = users;

    // Filtro de busca
    if (searchTerm) {
      filtered = filtered.filter(
        (user) =>
          user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
          user.email.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filtro de role
    if (roleFilter !== 'all') {
      filtered = filtered.filter((user) => user.role === roleFilter);
    }

    setFilteredUsers(filtered);
  }, [searchTerm, roleFilter, users]);

  // Criar usuário
  const handleCreate = async (data: UserCreate) => {
    try {
      await usersApi.create(data);
      await loadUsers();
      setIsCreateModalOpen(false);
    } catch (error) {
      console.error('Erro ao criar usuário:', error);
      throw error;
    }
  };

  // Editar usuário
  const handleEdit = async (id: number, data: UserUpdate) => {
    try {
      await usersApi.update(id, data);
      await loadUsers();
      setEditingUser(null);
    } catch (error) {
      console.error('Erro ao editar usuário:', error);
      throw error;
    }
  };

  // Deletar usuário
  const handleDelete = async (id: number) => {
    try {
      await usersApi.delete(id);
      await loadUsers();
      setDeletingUser(null);
    } catch (error) {
      console.error('Erro ao deletar usuário:', error);
      throw error;
    }
  };

  const isAdmin = currentUser?.role === 'admin';

  return (
    <MainLayout>
      <div className="space-y-6 animate-fadeIn">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Usuários</h1>
            <p className="text-gray-600 mt-1">Gerencie usuários do sistema</p>
          </div>

          {isAdmin && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Novo Usuário
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar por nome ou email..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                />
              </div>
            </div>

            {/* Role Filter */}
            <div className="sm:w-48">
              <select
                value={roleFilter}
                onChange={(e) =>
                  setRoleFilter(e.target.value as typeof roleFilter)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              >
                <option value="all">Todos os roles</option>
                <option value="admin">Admin</option>
                <option value="user">User</option>
              </select>
            </div>
          </div>

          {/* Results count */}
          <div className="mt-4 text-sm text-gray-600">
            Mostrando <span className="font-semibold">{filteredUsers.length}</span> de{' '}
            <span className="font-semibold">{users.length}</span> usuários
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <UserTable
            users={filteredUsers}
            loading={loading}
            currentUserId={currentUser?.id}
            isAdmin={isAdmin}
            onEdit={(user) => setEditingUser(user)}
            onDelete={(user) => setDeletingUser(user)}
          />
        </div>

        {/* Modals */}
        <UserModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSubmit={handleCreate}
          title="Novo Usuário"
        />

        <UserModal
          isOpen={!!editingUser}
          onClose={() => setEditingUser(null)}
          onSubmit={(data) => handleEdit(editingUser!.id, data)}
          user={editingUser || undefined}
          title="Editar Usuário"
        />

        <DeleteUserDialog
          isOpen={!!deletingUser}
          onClose={() => setDeletingUser(null)}
          onConfirm={() => handleDelete(deletingUser!.id)}
          user={deletingUser}
        />
      </div>
    </MainLayout>
  );
}
