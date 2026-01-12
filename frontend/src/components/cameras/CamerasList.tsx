/**
 * CamerasList.tsx - Cameras List Component
 * Displays cameras in card grid with actions
 */

import { useState } from 'react';
import { Camera as CameraIcon, Edit, Trash2, Power, MapPin, Video, Layers } from 'lucide-react';
import { toast } from 'sonner';
import type { Camera } from '../../types/cameras.types';
import {
    formatCameraSource,
    getCameraStatusText
} from '../../types/cameras.types';
import { useZones } from '../../hooks/useZones';

// ============================================
// TYPES
// ============================================

interface CamerasListProps {
    cameras: Camera[];
    onEdit: (camera: Camera) => void;
    onDelete: (cameraId: number) => void;
    onToggle: (cameraId: number) => void;
    loading?: boolean;
}

// ============================================
// COMPONENT
// ============================================

export function CamerasList({
    cameras,
    onEdit,
    onDelete,
    onToggle,
    loading = false
}: CamerasListProps) {
    const [deletingId, setDeletingId] = useState<number | null>(null);
    const [togglingId, setTogglingId] = useState<number | null>(null);

    // ✅ NEW v3.1: Zonas para contar por câmera
    const { zones } = useZones();    
    // Helper para contar zonas por câmera
    const getZoneCount = (cameraId: number): number => {
        return zones.filter(z => z.camera_id === cameraId).length;
    };

    // ============================================
    // HANDLERS
    // ============================================

    const handleDelete = async (camera: Camera) => {
        const confirmed = window.confirm(
            `Tem certeza que deseja deletar a câmera "${camera.name}"?\n\nEsta ação não pode ser desfeita.`
        );

        if (!confirmed) return;

        setDeletingId(camera.id);
        try {
            await onDelete(camera.id);
            toast.success('Câmera deletada com sucesso!');
        } catch (error) {
            toast.error('Erro ao deletar câmera');
        } finally {
            setDeletingId(null);
        }
    };

    const handleToggle = async (camera: Camera) => {
        setTogglingId(camera.id);
        try {
            await onToggle(camera.id);
            const newStatus = camera.enabled ? 'desativada' : 'ativada';
            toast.success(`Câmera ${newStatus} com sucesso!`);
        } catch (error) {
            toast.error('Erro ao alternar status da câmera');
        } finally {
            setTogglingId(null);
        }
    };

    // ============================================
    // RENDER LOADING
    // ============================================

    if (loading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3].map(i => (
                    <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
                        <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
                        <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
                        <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                    </div>
                ))}
            </div>
        );
    }

    // ============================================
    // RENDER EMPTY
    // ============================================

    if (cameras.length === 0) {
        return (
            <div className="bg-white rounded-lg shadow p-12 text-center">
                <CameraIcon size={48} className="mx-auto text-gray-400 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Nenhuma câmera cadastrada
                </h3>
                <p className="text-gray-600">
                    Clique no botão "Nova Câmera" para adicionar sua primeira câmera.
                </p>
            </div>
        );
    }

    // ============================================
    // RENDER LIST
    // ============================================

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cameras.map(camera => (
                <div
                    key={camera.id}
                    className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6 border-l-4"
                    style={{
                        borderLeftColor: camera.enabled ? '#10b981' : '#6b7280'
                    }}
                >
                    {/* Header */}
                    <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-gray-900 mb-1">
                                {camera.name}
                            </h3>
                            <div className="flex items-center space-x-2">
                                <span
                                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${camera.enabled
                                            ? 'bg-green-100 text-green-800'
                                            : 'bg-gray-100 text-gray-800'
                                        }`}
                                >
                                    {getCameraStatusText(camera.enabled)}
                                </span>
                            </div>
                        </div>
                        <CameraIcon
                            size={24}
                            className={camera.enabled ? 'text-green-600' : 'text-gray-400'}
                        />
                    </div>

                    {/* Details */}
                    <div className="space-y-2 mb-4">
                        {/* Source */}
                        <div className="flex items-start space-x-2 text-sm">
                            <Video size={16} className="text-gray-400 mt-0.5 flex-shrink-0" />
                            <span className="text-gray-600 break-all">
                                {formatCameraSource(camera.source)}
                            </span>
                        </div>

                        {/* Location */}
                        {camera.location && (
                            <div className="flex items-start space-x-2 text-sm">
                                <MapPin size={16} className="text-gray-400 mt-0.5 flex-shrink-0" />
                                <span className="text-gray-600">{camera.location}</span>
                            </div>
                        )}
                    </div>

                    {/* ✅ NEW v3.1: Zone Count */}
                    <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-lg border border-blue-100">
                        <Layers size={18} className="text-blue-600 flex-shrink-0" />
                        <div className="flex-1">
                            <p className="text-xs text-blue-600 font-medium">Zonas Configuradas</p>
                            <p className="text-lg font-bold text-blue-700">
                                {getZoneCount(camera.id)} zona{getZoneCount(camera.id) !== 1 ? 's' : ''}
                            </p>
                        </div>
                    </div>

                    {/* Metadata */}
                    {camera.metadata && Object.keys(camera.metadata).length > 0 && (
                        <div className="mb-4 p-3 bg-gray-50 rounded text-xs">
                            <div className="font-medium text-gray-700 mb-1">Metadados:</div>
                            <div className="space-y-1">
                                {Object.entries(camera.metadata).map(([key, value]) => (
                                    <div key={key} className="text-gray-600">
                                        <span className="font-mono">{key}:</span> {String(value)}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center justify-between pt-4 border-t space-x-2">
                        {/* Toggle Button */}
                        <button
                            onClick={() => handleToggle(camera)}
                            disabled={togglingId === camera.id}
                            className={`flex items-center space-x-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${camera.enabled
                                    ? 'bg-yellow-50 text-yellow-700 hover:bg-yellow-100'
                                    : 'bg-green-50 text-green-700 hover:bg-green-100'
                                } disabled:opacity-50 disabled:cursor-not-allowed`}
                            title={camera.enabled ? 'Desativar' : 'Ativar'}
                        >
                            <Power size={16} />
                            <span>{togglingId === camera.id ? '...' : camera.enabled ? 'Desativar' : 'Ativar'}</span>
                        </button>

                        <div className="flex items-center space-x-2">
                            {/* Edit Button */}
                            <button
                                onClick={() => onEdit(camera)}
                                className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                title="Editar"
                            >
                                <Edit size={18} />
                            </button>

                            {/* Delete Button */}
                            <button
                                onClick={() => handleDelete(camera)}
                                disabled={deletingId === camera.id}
                                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                title="Deletar"
                            >
                                <Trash2 size={18} />
                            </button>
                        </div>
                    </div>

                    {/* Footer - Timestamps */}
                    <div className="mt-3 pt-3 border-t text-xs text-gray-500">
                        Criada em: {new Date(camera.created_at).toLocaleString('pt-BR')}
                    </div>
                </div>
            ))}
        </div>
    );
}

export default CamerasList;
