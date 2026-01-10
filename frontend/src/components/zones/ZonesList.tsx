/**
 * ============================================================================
 * ZonesList.tsx - Zones List Component v3.1
 * ============================================================================
 * Lista de zonas com cards, filtros, ações rápidas E SELEÇÃO MÚLTIPLA
 * ============================================================================
 */

import { useState } from 'react';
import {
    Edit2,
    Trash2,
    Eye,
    Power,
    Search,
    Filter,
    AlertCircle,
    CheckCircle2,
    XCircle
} from 'lucide-react';
import type { Zone, ZoneMode } from '../../types/zones.types';
import { ZONE_MODE_LABELS, ZONE_MODE_COLORS } from '../../types/zones.types';

// ============================================================================
// TYPES
// ============================================================================

interface ZonesListProps {
    zones: Zone[];
    loading: boolean;
    onEdit: (zone: Zone) => void;
    onDelete: (zoneId: number) => void;
    onToggle: (zoneId: number, enabled: boolean) => void;
    onView?: (zone: Zone) => void;
    // ✅ ADICIONAR: Props para seleção múltipla
    selectedZones?: number[];
    onSelectionChange?: (selectedIds: number[]) => void;
}

interface DeleteConfirmDialogProps {
    isOpen: boolean;
    zoneName: string;
    onConfirm: () => void;
    onCancel: () => void;
}

// ============================================================================
// DELETE CONFIRMATION DIALOG
// ============================================================================

function DeleteConfirmDialog({
    isOpen,
    zoneName,
    onConfirm,
    onCancel
}: DeleteConfirmDialogProps) {
    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 z-50 backdrop-blur-sm"
                onClick={onCancel}
            />

            {/* Dialog */}
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 space-y-4">
                    {/* Icon */}
                    <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto">
                        <AlertCircle className="w-6 h-6 text-red-600" />
                    </div>

                    {/* Title */}
                    <h3 className="text-xl font-bold text-gray-900 text-center">
                        Confirmar Exclusão
                    </h3>

                    {/* Message */}
                    <p className="text-gray-600 text-center">
                        Tem certeza que deseja deletar a zona{' '}
                        <span className="font-semibold text-gray-900">"{zoneName}"</span>?
                        <br />
                        <span className="text-sm">Esta ação não pode ser desfeita.</span>
                    </p>

                    {/* Actions */}
                    <div className="flex gap-3 pt-2">
                        <button
                            onClick={onCancel}
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium text-gray-700"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={onConfirm}
                            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
                        >
                            Deletar
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}

// ============================================================================
// ZONE CARD COMPONENT
// ============================================================================

interface ZoneCardProps {
    zone: Zone;
    onEdit: () => void;
    onDelete: () => void;
    onToggle: () => void;
    onView?: () => void;
    // ✅ ADICIONAR: Props de seleção
    isSelected?: boolean;
    onSelect?: (selected: boolean) => void;
    showSelection?: boolean;
}

function ZoneCard({
    zone,
    onEdit,
    onDelete,
    onToggle,
    onView,
    isSelected = false,
    onSelect,
    showSelection = false
}: ZoneCardProps) {
    const modeColor = zone.color || ZONE_MODE_COLORS[zone.mode];

    return (
        <div className={`bg-white rounded-xl border-2 hover:shadow-lg transition-all duration-200 overflow-hidden ${isSelected ? 'border-blue-500 shadow-lg' : 'border-gray-200 hover:border-blue-300'
            }`}>
            {/* Header com cor do modo */}
            <div
                className="h-2"
                style={{ backgroundColor: modeColor }}
            />

            <div className="p-5 space-y-4">
                {/* ✅ ADICIONAR: Checkbox de seleção */}
                {showSelection && onSelect && (
                    <div className="flex items-center gap-3 pb-3 border-b border-gray-100">
                        <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => onSelect(e.target.checked)}
                            className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 cursor-pointer"
                        />
                        <label className="text-sm font-medium text-gray-700 cursor-pointer select-none">
                            Selecionar zona
                        </label>
                    </div>
                )}

                {/* Título e Status */}
                <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-bold text-gray-900 truncate">
                            {zone.name}
                        </h3>
                        <div className="flex items-center gap-2 mt-1">
                            <span
                                className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium"
                                style={{
                                    backgroundColor: `${modeColor}15`,
                                    color: modeColor
                                }}
                            >
                                {ZONE_MODE_LABELS[zone.mode]}
                            </span>

                            {zone.enabled ? (
                                <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-green-50 text-green-700">
                                    <CheckCircle2 className="w-3 h-3" />
                                    Ativa
                                </span>
                            ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
                                    <XCircle className="w-3 h-3" />
                                    Inativa
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Toggle Button */}
                    <button
                        onClick={onToggle}
                        className={`flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-lg transition-colors ${zone.enabled
                                ? 'bg-green-50 text-green-600 hover:bg-green-100'
                                : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                            }`}
                        title={zone.enabled ? 'Desabilitar zona' : 'Habilitar zona'}
                    >
                        <Power className="w-5 h-5" />
                    </button>
                </div>

                {/* Descrição */}
                {zone.description && (
                    <p className="text-sm text-gray-600 line-clamp-2">
                        {zone.description}
                    </p>
                )}

                {/* Informações */}
                <div className="grid grid-cols-2 gap-3 pt-3 border-t border-gray-100">
                    <div>
                        <p className="text-xs text-gray-500">Pontos</p>
                        <p className="text-sm font-semibold text-gray-900">
                            {zone.points.length} vértices
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-500">Threshold</p>
                        <p className="text-sm font-semibold text-gray-900">
                            {zone.empty_threshold} - {zone.full_threshold}
                        </p>
                    </div>
                </div>

                {/* Tags */}
                {zone.tags && zone.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                        {zone.tags.slice(0, 3).map((tag, index) => (
                            <span
                                key={index}
                                className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs"
                            >
                                {tag}
                            </span>
                        ))}
                        {zone.tags.length > 3 && (
                            <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                                +{zone.tags.length - 3}
                            </span>
                        )}
                    </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
                    {onView && (
                        <button
                            onClick={onView}
                            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors text-sm font-medium"
                        >
                            <Eye className="w-4 h-4" />
                            Ver
                        </button>
                    )}

                    <button
                        onClick={onEdit}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors text-sm font-medium"
                    >
                        <Edit2 className="w-4 h-4" />
                        Editar
                    </button>

                    <button
                        onClick={onDelete}
                        className="flex items-center justify-center gap-2 px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors text-sm font-medium"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function ZonesList({
    zones,
    loading,
    onEdit,
    onDelete,
    onToggle,
    onView,
    selectedZones = [],
    onSelectionChange
}: ZonesListProps) {
    // ==========================================================================
    // STATE
    // ==========================================================================

    const [searchTerm, setSearchTerm] = useState('');
    const [filterMode, setFilterMode] = useState<ZoneMode | 'ALL'>('ALL');
    const [filterStatus, setFilterStatus] = useState<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL');
    const [deleteDialog, setDeleteDialog] = useState<{
        isOpen: boolean;
        zone: Zone | null;
    }>({ isOpen: false, zone: null });

    // ✅ Modo de seleção ativo quando há callback
    const isSelectionMode = !!onSelectionChange;

    // ==========================================================================
    // FILTERING
    // ==========================================================================

    const filteredZones = zones.filter(zone => {
        // Search filter
        if (searchTerm && !zone.name.toLowerCase().includes(searchTerm.toLowerCase())) {
            return false;
        }

        // Mode filter
        if (filterMode !== 'ALL' && zone.mode !== filterMode) {
            return false;
        }

        // Status filter
        if (filterStatus === 'ACTIVE' && !zone.enabled) {
            return false;
        }
        if (filterStatus === 'INACTIVE' && zone.enabled) {
            return false;
        }

        return true;
    });

    // ==========================================================================
    // SELECTION HANDLERS
    // ==========================================================================

    const handleZoneSelect = (zoneId: number, selected: boolean) => {
        if (!onSelectionChange) return;

        if (selected) {
            onSelectionChange([...selectedZones, zoneId]);
        } else {
            onSelectionChange(selectedZones.filter(id => id !== zoneId));
        }
    };

    const handleSelectAll = () => {
        if (!onSelectionChange) return;

        if (selectedZones.length === filteredZones.length) {
            // Desmarcar todos
            onSelectionChange([]);
        } else {
            // Marcar todos os filtrados
            onSelectionChange(filteredZones.map(z => z.id));
        }
    };

    // ==========================================================================
    // HANDLERS
    // ==========================================================================

    const handleDeleteClick = (zone: Zone) => {
        setDeleteDialog({ isOpen: true, zone });
    };

    const handleDeleteConfirm = () => {
        if (deleteDialog.zone) {
            onDelete(deleteDialog.zone.id);
            setDeleteDialog({ isOpen: false, zone: null });
        }
    };

    const handleDeleteCancel = () => {
        setDeleteDialog({ isOpen: false, zone: null });
    };

    // ==========================================================================
    // RENDER
    // ==========================================================================

    return (
        <div className="space-y-4">
            {/* Filters Bar */}
            <div className="bg-white rounded-xl border-2 border-gray-200 p-4">
                <div className="flex flex-col sm:flex-row gap-3">
                    {/* Search */}
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="Buscar por nome..."
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>

                    {/* Mode Filter */}
                    <div className="relative">
                        <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <select
                            value={filterMode}
                            onChange={(e) => setFilterMode(e.target.value as ZoneMode | 'ALL')}
                            className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
                        >
                            <option value="ALL">Todos os modos</option>
                            {Object.entries(ZONE_MODE_LABELS).map(([value, label]) => (
                                <option key={value} value={value}>
                                    {label}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Status Filter */}
                    <select
                        value={filterStatus}
                        onChange={(e) => setFilterStatus(e.target.value as 'ALL' | 'ACTIVE' | 'INACTIVE')}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
                    >
                        <option value="ALL">Todos status</option>
                        <option value="ACTIVE">Ativas</option>
                        <option value="INACTIVE">Inativas</option>
                    </select>
                </div>

                {/* Results Count + Select All */}
                <div className="mt-3 flex items-center justify-between">
                    <div className="text-sm text-gray-600">
                        {filteredZones.length === zones.length ? (
                            <span>
                                Total: <span className="font-semibold text-gray-900">{zones.length}</span> zona(s)
                            </span>
                        ) : (
                            <span>
                                Mostrando <span className="font-semibold text-gray-900">{filteredZones.length}</span> de{' '}
                                <span className="font-semibold text-gray-900">{zones.length}</span> zona(s)
                            </span>
                        )}
                    </div>

                    {/* ✅ Select All Button */}
                    {isSelectionMode && filteredZones.length > 0 && (
                        <button
                            onClick={handleSelectAll}
                            className="text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
                        >
                            {selectedZones.length === filteredZones.length && filteredZones.length > 0
                                ? 'Desmarcar Todas'
                                : 'Selecionar Todas'}
                        </button>
                    )}
                </div>
            </div>

            {/* Loading State */}
            {loading && (
                <div className="flex items-center justify-center py-12">
                    <div className="flex items-center gap-3 text-gray-600">
                        <div className="w-6 h-6 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
                        <span className="font-medium">Carregando zonas...</span>
                    </div>
                </div>
            )}

            {/* Empty State */}
            {!loading && filteredZones.length === 0 && (
                <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-300 p-12">
                    <div className="text-center space-y-3">
                        <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto">
                            <AlertCircle className="w-8 h-8 text-gray-400" />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900">
                            {searchTerm || filterMode !== 'ALL' || filterStatus !== 'ALL'
                                ? 'Nenhuma zona encontrada'
                                : 'Nenhuma zona criada'}
                        </h3>
                        <p className="text-gray-600">
                            {searchTerm || filterMode !== 'ALL' || filterStatus !== 'ALL'
                                ? 'Tente ajustar os filtros de busca.'
                                : 'Clique no botão "Nova Zona" para começar.'}
                        </p>
                    </div>
                </div>
            )}

            {/* Zones Grid */}
            {!loading && filteredZones.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredZones.map(zone => (
                        <ZoneCard
                            key={zone.id}
                            zone={zone}
                            onEdit={() => onEdit(zone)}
                            onDelete={() => handleDeleteClick(zone)}
                            onToggle={() => onToggle(zone.id, !zone.enabled)}
                            onView={onView ? () => onView(zone) : undefined}
                            isSelected={selectedZones.includes(zone.id)}
                            onSelect={(selected) => handleZoneSelect(zone.id, selected)}
                            showSelection={isSelectionMode}
                        />
                    ))}
                </div>
            )}

            {/* Delete Confirmation Dialog */}
            <DeleteConfirmDialog
                isOpen={deleteDialog.isOpen}
                zoneName={deleteDialog.zone?.name || ''}
                onConfirm={handleDeleteConfirm}
                onCancel={handleDeleteCancel}
            />
        </div>
    );
}
