// frontend/src/pages/Users.tsx

/**
 * ============================================================================
 * USERS PAGE - v3.1 COMPLETE ✅
 * ============================================================================
 * ✅ v2.0: Mantém toda funcionalidade original
 * ➕ v3.0: Adiciona busca avançada, bulk operations, export
 * 🔧 FIX: Props v3.0 adicionadas ao UserTable
 * 🔄 OPÇÃO 2: Usando componente UserBulkActions separado
 * 🎨 v3.1: Toast notifications em vez de alerts
 */

import { useState, useEffect } from 'react';
import { Plus, Search, Download, Filter, X } from 'lucide-react';
import MainLayout from '../components/layout/MainLayout';
import UserTable from '../components/users/UserTable';
import UserModal from '../components/users/UserModal';
import DeleteUserDialog from '../components/users/DeleteUserDialog';
import UserBulkActions from '../components/users/UserBulkActions';
import { useToast } from '../hooks/useToast';

import { usersApi } from '../api/users';
import { User, UserCreate, UserUpdate, UserSearchParams, ExportFormat } from '../types/user';
import { useAuthStore } from '../store/authStore';

export default function Users() {
  const currentUser = useAuthStore((state) => state.user);
  const { showToast } = useToast();

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================

  // Users data
  const [users, setUsers] = useState<User[]>([]);
  const [filteredUsers, setFilteredUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  // ✅ v2.0: Filtros simples (mantidos)
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | 'admin' | 'user'>('all');

  // ➕ v3.0: Advanced filters
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [advancedFilters, setAdvancedFilters] = useState<Partial<UserSearchParams>>({});

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);

  // ➕ v3.0: Bulk operations
  const [isBulkMode, setIsBulkMode] = useState(false);
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([]);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // ➕ v3.0: Export
  const [isExporting, setIsExporting] = useState(false);

  const isAdmin = currentUser?.role === 'admin';

  // ============================================================================
  // DATA FETCHING
  // ============================================================================

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await usersApi.getAll();
      setUsers(data);
      setFilteredUsers(data);
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
      showToast('❌ Erro ao carregar usuários', 'error', 4000);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  // ============================================================================
  // FILTERS
  // ============================================================================

  useEffect(() => {
    let filtered = users;

    if (searchTerm) {
      filtered = filtered.filter(
        (user) =>
          user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
          user.email.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (roleFilter !== 'all') {
      filtered = filtered.filter((user) => user.role === roleFilter);
    }

    setFilteredUsers(filtered);
  }, [searchTerm, roleFilter, users]);

  const applyAdvancedFilters = async () => {
    try {
      setLoading(true);
      const params: UserSearchParams = {
        ...advancedFilters,
        limit: 1000,
      };

      const response = await usersApi.searchUsers(params);
      setUsers(response.users);
      setFilteredUsers(response.users);
      setShowAdvancedFilters(false);
      showToast('✅ Filtros aplicados com sucesso', 'success', 3000);
    } catch (error) {
      console.error('Erro ao aplicar filtros:', error);
      showToast('❌ Erro ao aplicar filtros', 'error', 4000);
    } finally {
      setLoading(false);
    }
  };

  const clearAdvancedFilters = () => {
    setAdvancedFilters({});
    setSearchTerm('');
    setRoleFilter('all');
    loadUsers();
    showToast('🔄 Filtros limpos', 'info', 2000);
  };

  // ============================================================================
  // CRUD OPERATIONS
  // ============================================================================

  const handleCreate = async (data: UserCreate | UserUpdate) => {
    try {
      if (!('username' in data)) {
        throw new Error('Username é obrigatório para criar usuário');
      }

      await usersApi.create(data as UserCreate);
      await loadUsers();
      setIsCreateModalOpen(false);
      showToast('✅ Usuário criado com sucesso!', 'success', 3000);
    } catch (error) {
      console.error('Erro ao criar usuário:', error);
      showToast('❌ Erro ao criar usuário', 'error', 4000);
      throw error;
    }
  };

  const handleEdit = async (data: UserCreate | UserUpdate) => {
    try {
      if (!editingUser) {
        throw new Error('Nenhum usuário selecionado para edição');
      }

      await usersApi.update(editingUser.id, data as UserUpdate);
      await loadUsers();
      setEditingUser(null);
      showToast('✅ Usuário atualizado com sucesso!', 'success', 3000);
    } catch (error) {
      console.error('Erro ao editar usuário:', error);
      showToast('❌ Erro ao editar usuário', 'error', 4000);
      throw error;
    }
  };

  const handleDelete = async () => {
    try {
      if (!deletingUser) {
        throw new Error('Nenhum usuário selecionado para exclusão');
      }

      await usersApi.delete(deletingUser.id);
      await loadUsers();
      setDeletingUser(null);
      showToast('✅ Usuário deletado com sucesso!', 'success', 3000);
    } catch (error) {
      console.error('Erro ao deletar usuário:', error);
      showToast('❌ Erro ao deletar usuário', 'error', 4000);
      throw error;
    }
  };

  // ============================================================================
  // BULK OPERATIONS
  // ============================================================================

  const handleToggleBulkMode = () => {
    setIsBulkMode(!isBulkMode);
    setSelectedUserIds([]);
  };

  const handleToggleUserSelection = (userId: number) => {
    setSelectedUserIds((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]
    );
  };

  const handleSelectAll = () => {
    if (selectedUserIds.length === filteredUsers.length) {
      setSelectedUserIds([]);
    } else {
      setSelectedUserIds(filteredUsers.map((u) => u.id));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedUserIds.length === 0) return;

    const confirmed = window.confirm(
      `Tem certeza que deseja deletar ${selectedUserIds.length} usuário(s)?\n\n⚠️ Esta ação não pode ser desfeita!`
    );

    if (!confirmed) return;

    try {
      setBulkDeleting(true);
      const response = await usersApi.bulkDelete(selectedUserIds);

      console.log('✅ Bulk delete resultado:', response);

      await loadUsers();
      setSelectedUserIds([]);
      setIsBulkMode(false);

      // ✅ TOAST NOTIFICATIONS - Mais profissional!
      if (response.successful && response.deleted > 0) {
        showToast(
          `✅ ${response.deleted} usuário(s) deletado(s) com sucesso!`,
          'success',
          4000
        );

        // Se houver falhas, mostrar aviso adicional
        if (response.failed > 0) {
          showToast(
            `⚠️ ${response.failed} usuário(s) não pôde(ram) ser deletado(s)`,
            'warning',
            5000
          );
        }
      } else if (response.failed > 0) {
        showToast(
          `❌ Não foi possível deletar ${response.failed} usuário(s)`,
          'error',
          5000
        );
      }
    } catch (error) {
      console.error('Erro ao deletar usuários em lote:', error);
      showToast(
        '❌ Erro ao deletar usuários. Verifique o console para detalhes.',
        'error',
        5000
      );
    } finally {
      setBulkDeleting(false);
    }
  };

  // ============================================================================
  // EXPORT
  // ============================================================================

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      setIsExporting(true);
      await usersApi.exportAndDownload(format as ExportFormat);
      showToast(
        `✅ Usuários exportados com sucesso em formato ${format.toUpperCase()}!`,
        'success',
        4000
      );
    } catch (error) {
      console.error('Erro ao exportar usuários:', error);
      showToast('❌ Erro ao exportar usuários', 'error', 4000);
    } finally {
      setIsExporting(false);
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <MainLayout>
      <div className="space-y-6 animate-fadeIn">
        {/* HEADER */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Usuários</h1>
            <p className="text-gray-600 mt-1">
              Gerencie usuários do sistema
              {filteredUsers.length !== users.length && (
                <span className="ml-2 text-blue-600 font-medium">
                  ({filteredUsers.length} filtrados)
                </span>
              )}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${showAdvancedFilters
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
            >
              <Filter className="w-4 h-4" />
              Filtros Avançados
            </button>

            {isAdmin && (
              <button
                onClick={handleToggleBulkMode}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${isBulkMode
                  ? 'bg-purple-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                  }`}
              >
                {isBulkMode ? '✓ Modo Seleção' : 'Selecionar Múltiplos'}
              </button>
            )}

            {isAdmin && (
              <div className="relative group">
                <button
                  disabled={isExporting}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-white text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Download className="w-4 h-4" />
                  {isExporting ? 'Exportando...' : 'Exportar'}
                </button>

                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                  <button
                    onClick={() => handleExport('json')}
                    disabled={isExporting}
                    className="w-full px-4 py-2 text-left hover:bg-gray-50 rounded-t-lg disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    📄 Exportar JSON
                  </button>
                  <button
                    onClick={() => handleExport('csv')}
                    disabled={isExporting}
                    className="w-full px-4 py-2 text-left hover:bg-gray-50 rounded-b-lg disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    📊 Exportar CSV
                  </button>
                </div>
              </div>
            )}

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
        </div>

        {/* ADVANCED FILTERS */}
        {showAdvancedFilters && (
          <div className="bg-white rounded-lg shadow-lg p-6 border-2 border-blue-200 animate-fadeIn">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">🔍 Filtros Avançados</h3>
              <button onClick={() => setShowAdvancedFilters(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Buscar</label>
                <input
                  type="text"
                  placeholder="Nome ou email..."
                  value={advancedFilters.search_term || ''}
                  onChange={(e) => setAdvancedFilters({ ...advancedFilters, search_term: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Permissão</label>
                <select
                  value={advancedFilters.role || ''}
                  onChange={(e) =>
                    setAdvancedFilters({ ...advancedFilters, role: e.target.value as 'user' | 'admin' | undefined })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Todos</option>
                  <option value="admin">Admin</option>
                  <option value="user">User</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ordenar por</label>
                <select
                  value={advancedFilters.sort_by || 'created_at'}
                  onChange={(e) => setAdvancedFilters({ ...advancedFilters, sort_by: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="created_at">Data de Criação</option>
                  <option value="username">Username</option>
                  <option value="email">Email</option>
                  <option value="last_login">Último Login</option>
                </select>
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <button onClick={applyAdvancedFilters} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Aplicar Filtros
              </button>
              <button onClick={clearAdvancedFilters} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
                Limpar Tudo
              </button>
            </div>
          </div>
        )}

        {/* BULK ACTIONS BAR */}
        {isBulkMode && selectedUserIds.length > 0 && (
          <UserBulkActions
            selectedUsers={filteredUsers.filter((u) => selectedUserIds.includes(u.id))}
            selectedUserIds={selectedUserIds}
            allUsers={filteredUsers}
            onDelete={handleBulkDelete}
            onExport={handleExport}
            onSelectAll={handleSelectAll}
            onDeselectAll={() => setSelectedUserIds([])}
            isDeleting={bulkDeleting}
            isExporting={isExporting}
          />
        )}

        {/* FILTERS BAR */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar por nome ou email..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="sm:w-48">
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value as typeof roleFilter)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">Todos os roles</option>
                <option value="admin">Admin</option>
                <option value="user">User</option>
              </select>
            </div>
          </div>

          <div className="mt-4 text-sm text-gray-600">
            Mostrando <span className="font-semibold">{filteredUsers.length}</span> de{' '}
            <span className="font-semibold">{users.length}</span> usuários
          </div>
        </div>

        {/* TABLE */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <UserTable
            users={filteredUsers}
            loading={loading}
            currentUserId={currentUser?.id}
            isAdmin={isAdmin}
            onEdit={(user) => setEditingUser(user)}
            onDelete={(user) => setDeletingUser(user)}
            isBulkMode={isBulkMode}
            selectedUserIds={selectedUserIds}
            onToggleSelection={handleToggleUserSelection}
            onSelectAll={handleSelectAll}
          />
        </div>

        {/* MODALS */}
        <UserModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSubmit={handleCreate}
          title="Novo Usuário"
        />

        <UserModal
          isOpen={!!editingUser}
          onClose={() => setEditingUser(null)}
          onSubmit={handleEdit}
          user={editingUser || undefined}
          title="Editar Usuário"
        />

        <DeleteUserDialog
          isOpen={!!deletingUser}
          onClose={() => setDeletingUser(null)}
          onConfirm={handleDelete}
          user={deletingUser}
        />
      </div>
    </MainLayout>
  );
}
