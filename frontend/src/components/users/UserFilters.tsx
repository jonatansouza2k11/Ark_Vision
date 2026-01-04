// frontend/src/components/users/UserFilters.tsx
/**
 * ============================================================================
 * USER FILTERS - v3.0 NEW COMPONENT
 * ============================================================================
 * ➕ v3.0: Componente separado para filtros avançados
 * Features: Search, Role, Sort, Date ranges, Status filters
 */

import { useState, useEffect } from 'react';
import { X, Filter, RotateCcw, Search, Calendar } from 'lucide-react';
import { UserSearchParams, SortField, SortOrder } from '../../types/user';

// ============================================================================
// INTERFACE
// ============================================================================

interface UserFiltersProps {
    isOpen: boolean;
    onClose: () => void;
    onApply: (filters: Partial<UserSearchParams>) => void;
    onClear: () => void;
    initialFilters?: Partial<UserSearchParams>;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function UserFilters({
    isOpen,
    onClose,
    onApply,
    onClear,
    initialFilters = {},
}: UserFiltersProps) {
    // ============================================================================
    // STATE
    // ============================================================================

    const [filters, setFilters] = useState<Partial<UserSearchParams>>({
        search_term: '',
        role: undefined,
        sort_by: 'created_at' as SortField,
        sort_order: 'desc' as SortOrder,
        created_after: '',
        created_before: '',
        last_login_after: '',
        last_login_before: '',
        ...initialFilters,
    });

    const [hasChanges, setHasChanges] = useState(false);

    // ============================================================================
    // EFFECTS
    // ============================================================================

    /**
     * Detecta mudanças nos filtros
     */
    useEffect(() => {
        const changed = JSON.stringify(filters) !== JSON.stringify(initialFilters);
        setHasChanges(changed);
    }, [filters, initialFilters]);

    /**
     * Reset filtros quando fecha
     */
    useEffect(() => {
        if (!isOpen) {
            setFilters({ ...initialFilters });
        }
    }, [isOpen, initialFilters]);

    // ============================================================================
    // HANDLERS
    // ============================================================================

    /**
     * Atualiza campo específico
     */
    const updateFilter = <K extends keyof UserSearchParams>(
        key: K,
        value: UserSearchParams[K] | undefined
    ) => {
        setFilters((prev) => ({
            ...prev,
            [key]: value,
        }));
    };

    /**
     * Aplica filtros
     */
    const handleApply = () => {
        // Remove campos vazios
        const cleanedFilters = Object.entries(filters).reduce((acc, [key, value]) => {
            if (value !== '' && value !== undefined) {
                acc[key as keyof UserSearchParams] = value as any;
            }
            return acc;
        }, {} as Partial<UserSearchParams>);

        onApply(cleanedFilters);
        onClose();
    };

    /**
     * Limpa todos filtros
     */
    const handleClear = () => {
        setFilters({
            search_term: '',
            role: undefined,
            sort_by: 'created_at' as SortField,
            sort_order: 'desc' as SortOrder,
            created_after: '',
            created_before: '',
            last_login_after: '',
            last_login_before: '',
        });
        onClear();
    };

    /**
     * Conta filtros ativos
     */
    const getActiveFiltersCount = (): number => {
        let count = 0;
        if (filters.search_term) count++;
        if (filters.role) count++;
        if (filters.created_after) count++;
        if (filters.created_before) count++;
        if (filters.last_login_after) count++;
        if (filters.last_login_before) count++;
        return count;
    };

    const activeCount = getActiveFiltersCount();

    // ============================================================================
    // RENDER
    // ============================================================================

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 animate-fadeIn">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto animate-slideUp">
                {/* ========== HEADER ========== */}
                <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                            <Filter className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                            <h2 className="text-xl font-semibold text-gray-900">Filtros Avançados</h2>
                            {activeCount > 0 && (
                                <p className="text-sm text-blue-600">
                                    {activeCount} filtro(s) ativo(s)
                                </p>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* ========== CONTENT ========== */}
                <div className="p-6 space-y-6">
                    {/* ========== SECTION: BUSCA ========== */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                            <Search className="w-4 h-4" />
                            Busca Textual
                        </h3>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Pesquisar em nome ou email
                            </label>
                            <input
                                type="text"
                                value={filters.search_term || ''}
                                onChange={(e) => updateFilter('search_term', e.target.value)}
                                placeholder="Digite para buscar..."
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Busca por username ou email (case-insensitive)
                            </p>
                        </div>
                    </div>

                    <div className="border-t border-gray-200"></div>

                    {/* ========== SECTION: PERMISSÃO E ORDENAÇÃO ========== */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
                            Permissão e Ordenação
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Role */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Permissão
                                </label>
                                <select
                                    value={filters.role || ''}
                                    onChange={(e) =>
                                        updateFilter('role', e.target.value as 'user' | 'admin' | undefined)
                                    }
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                >
                                    <option value="">Todos</option>
                                    <option value="admin">🛡️ Admin</option>
                                    <option value="user">👤 User</option>
                                </select>
                            </div>

                            {/* Sort By */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Ordenar por
                                </label>
                                <select
                                    value={filters.sort_by || 'created_at'}
                                    onChange={(e) => updateFilter('sort_by', e.target.value as SortField)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                >
                                    <option value="created_at">Data de Criação</option>
                                    <option value="username">Username (A-Z)</option>
                                    <option value="email">Email (A-Z)</option>
                                    <option value="last_login">Último Login</option>
                                    <option value="updated_at">Última Atualização</option>
                                </select>
                            </div>

                            {/* Sort Order */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Ordem
                                </label>
                                <select
                                    value={filters.sort_order || 'desc'}
                                    onChange={(e) => updateFilter('sort_order', e.target.value as SortOrder)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                >
                                    <option value="asc">⬆️ Crescente</option>
                                    <option value="desc">⬇️ Decrescente</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <div className="border-t border-gray-200"></div>

                    {/* ========== SECTION: DATAS ========== */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                            <Calendar className="w-4 h-4" />
                            Filtros de Data
                        </h3>

                        {/* Data de Criação */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Data de Criação
                            </label>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs text-gray-600 mb-1">De:</label>
                                    <input
                                        type="date"
                                        value={filters.created_after || ''}
                                        onChange={(e) => updateFilter('created_after', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-gray-600 mb-1">Até:</label>
                                    <input
                                        type="date"
                                        value={filters.created_before || ''}
                                        onChange={(e) => updateFilter('created_before', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Data de Último Login */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Último Login
                            </label>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs text-gray-600 mb-1">De:</label>
                                    <input
                                        type="date"
                                        value={filters.last_login_after || ''}
                                        onChange={(e) => updateFilter('last_login_after', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-gray-600 mb-1">Até:</label>
                                    <input
                                        type="date"
                                        value={filters.last_login_before || ''}
                                        onChange={(e) => updateFilter('last_login_before', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* ========== PREVIEW ========== */}
                    {activeCount > 0 && (
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                            <h4 className="text-sm font-semibold text-blue-900 mb-2">
                                Filtros Ativos ({activeCount})
                            </h4>
                            <div className="flex flex-wrap gap-2">
                                {filters.search_term && (
                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white rounded-md text-xs text-gray-700 border border-blue-200">
                                        <Search className="w-3 h-3" />
                                        Busca: "{filters.search_term}"
                                    </span>
                                )}
                                {filters.role && (
                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white rounded-md text-xs text-gray-700 border border-blue-200">
                                        Role: {filters.role === 'admin' ? '🛡️ Admin' : '👤 User'}
                                    </span>
                                )}
                                {filters.created_after && (
                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white rounded-md text-xs text-gray-700 border border-blue-200">
                                        Criado após: {new Date(filters.created_after).toLocaleDateString('pt-BR')}
                                    </span>
                                )}
                                {filters.created_before && (
                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white rounded-md text-xs text-gray-700 border border-blue-200">
                                        Criado antes: {new Date(filters.created_before).toLocaleDateString('pt-BR')}
                                    </span>
                                )}
                                {filters.last_login_after && (
                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white rounded-md text-xs text-gray-700 border border-blue-200">
                                        Login após: {new Date(filters.last_login_after).toLocaleDateString('pt-BR')}
                                    </span>
                                )}
                                {filters.last_login_before && (
                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white rounded-md text-xs text-gray-700 border border-blue-200">
                                        Login antes: {new Date(filters.last_login_before).toLocaleDateString('pt-BR')}
                                    </span>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* ========== ACTIONS ========== */}
                <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center justify-between">
                    <button
                        onClick={handleClear}
                        disabled={activeCount === 0}
                        className="inline-flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <RotateCcw className="w-4 h-4" />
                        Limpar Filtros
                    </button>

                    <div className="flex gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleApply}
                            className="inline-flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                        >
                            <Filter className="w-4 h-4" />
                            Aplicar Filtros
                            {activeCount > 0 && (
                                <span className="ml-1 px-2 py-0.5 bg-blue-500 rounded-full text-xs">
                                    {activeCount}
                                </span>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
