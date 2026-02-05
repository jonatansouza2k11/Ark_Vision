/**
 * CamerasList.tsx v2.1 - Cameras List Component
 * Displays cameras in card grid with actions and streaming status
 */

import { useState, useEffect } from "react";
import {
    Camera as CameraIcon,
    Edit,
    Trash2,
    Power,
    MapPin,
    Video,
    Layers,
    Eye,
    Settings,
} from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

import type { Camera } from "../../types/cameras.types";
import {
    formatCameraSource,
    getCameraStatusText,
    isCameraStreamable,
} from "../../types/cameras.types";
import { useZones } from "../../hooks/useZones";

// ============================================
// TYPES
// ============================================

interface CameraTrackingStatus {
    tracker_type?: string;
    reid_profile?: string; // "edge" | "default" | "high"
    required_tracker_types?: string[];
}

interface CamerasListProps {
    cameras: Camera[];
    onEdit: (camera: Camera) => void;
    onDelete: (cameraId: number) => void;
    onToggle: (cameraId: number) => void;
    loading?: boolean;

    // Callback opcional para abrir view de streaming
    onViewStream?: (cameraId: number) => void;

    // Status de tracking/ReID por câmera (cameraId -> status)
    statusByCamera?: Record<number, CameraTrackingStatus>;
}

// ============================================
// COMPONENT
// ============================================

export function CamerasList({
    cameras,
    onEdit,
    onDelete,
    onToggle,
    loading = false,
    onViewStream,
    statusByCamera,
}: CamerasListProps) {
    const navigate = useNavigate();

    const [deletingId, setDeletingId] = useState<number | null>(null);
    const [togglingId, setTogglingId] = useState<number | null>(null);

    // Zonas para contar por câmera
    const { zones, fetchZones } = useZones();

    // Busca zonas no mount
    useEffect(() => {
        fetchZones(true); // includeDisabled = true para contar todas
    }, [fetchZones]);

    // Helper para contar zonas por câmera
    const getZoneCount = (cameraId: number): number => {
        return zones.filter((z) => z.camera_id === cameraId).length;
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
            toast.success("Câmera deletada com sucesso!");
        } catch (error) {
            toast.error("Erro ao deletar câmera");
        } finally {
            setDeletingId(null);
        }
    };

    const handleToggle = async (camera: Camera) => {
        setTogglingId(camera.id);
        try {
            await onToggle(camera.id);
            const newStatus = camera.enabled ? "desativada" : "ativada";
            toast.success(`Câmera ${newStatus} com sucesso!`);
        } catch (error) {
            toast.error("Erro ao alternar status da câmera");
        } finally {
            setTogglingId(null);
        }
    };

    // Visualizar stream
    const handleViewStream = (camera: Camera) => {
        if (!isCameraStreamable(camera)) {
            toast.error(
                "Câmera não disponível para streaming. Verifique se está ativa e configurada."
            );
            return;
        }

        if (onViewStream) {
            onViewStream(camera.id);
        } else {
            // Navegar para página de streaming com camera_id
            navigate(`/stream?camera=${camera.id}`);
        }
    };

    // Configurar zonas
    const handleConfigureZones = (cameraId: number) => {
        navigate(`/zones?camera=${cameraId}`);
    };

    // ============================================
    // TRACKING / REID BADGES
    // ============================================

    const renderTrackingBadges = (status?: CameraTrackingStatus) => {
        if (!status) return null;

        const tracker = (status.tracker_type || "desconhecido").toLowerCase();
        const profile = (status.reid_profile || "default").toLowerCase();

        const isStrongSort = tracker.includes("strongsort");

        let profileColor = "bg-blue-100 text-blue-800";
        if (profile === "high") {
            profileColor = "bg-purple-100 text-purple-800";
        } else if (profile === "edge") {
            profileColor = "bg-orange-100 text-orange-800";
        }

        return (
            <div className="flex items-center gap-2 mt-2">
                <span
                    className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${isStrongSort
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-gray-100 text-gray-700"
                        }`}
                >
                    {isStrongSort ? "StrongSORT + ReID" : tracker}
                </span>

                {isStrongSort && (
                    <span
                        className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${profileColor}`}
                    >
                        ReID {profile.toUpperCase()}
                    </span>
                )}
            </div>
        );
    };

    // ============================================
    // RENDER LOADING
    // ============================================

    if (loading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                    <div
                        key={i}
                        className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse"
                    >
                        <div className="h-6 bg-gray-200 rounded w-3/4 mb-4" />
                        <div className="h-4 bg-gray-200 rounded w-full mb-2" />
                        <div className="h-4 bg-gray-200 rounded w-2/3" />
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
            <div className="text-center py-12">
                <CameraIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Nenhuma câmera cadastrada
                </h3>
                <p className="text-gray-500">
                    Clique no botão &quot;Nova Câmera&quot; para adicionar sua primeira
                    câmera.
                </p>
            </div>
        );
    }

    // ============================================
    // RENDER LIST
    // ============================================

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cameras.map((camera) => {
                const trackingStatus = statusByCamera?.[camera.id];

                return (
                    <div
                        key={camera.id}
                        className="bg-white rounded-lg border border-gray-200 hover:shadow-lg transition-shadow"
                    >
                        {/* Header */}
                        <div className="p-6 border-b border-gray-200">
                            <div className="flex items-start justify-between mb-2">
                                <div className="flex items-center space-x-2 flex-1">
                                    <CameraIcon className="w-5 h-5 text-gray-400" />
                                    <h3 className="text-lg font-semibold text-gray-900 truncate">
                                        {camera.name}
                                    </h3>
                                </div>

                                {/* Status Badge */}
                                <span
                                    className={`px-2 py-1 text-xs font-medium rounded-full ${camera.enabled
                                            ? "bg-green-100 text-green-800"
                                            : "bg-gray-100 text-gray-800"
                                        }`}
                                >
                                    {getCameraStatusText(camera.enabled)}
                                </span>
                            </div>

                            {/* Badges de tracking/ReID */}
                            {renderTrackingBadges(trackingStatus)}
                        </div>

                        {/* Details */}
                        <div className="p-6 space-y-3">
                            {/* Source */}
                            <div className="flex items-start space-x-2 text-sm">
                                <Video className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                                <span className="text-gray-600 break-all">
                                    {formatCameraSource(camera.source)}
                                </span>
                            </div>

                            {/* Location */}
                            {camera.location && (
                                <div className="flex items-center space-x-2 text-sm">
                                    <MapPin className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                    <span className="text-gray-600">{camera.location}</span>
                                </div>
                            )}

                            {/* Zone Count */}
                            <div className="flex items-center space-x-2 text-sm">
                                <Layers className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                <div className="flex items-center justify-between w-full">
                                    <span className="text-gray-600">
                                        {getZoneCount(camera.id)} zona
                                        {getZoneCount(camera.id) !== 1 ? "s" : ""}
                                    </span>

                                    {/* Link para configurar zonas */}
                                    <button
                                        onClick={() => handleConfigureZones(camera.id)}
                                        className="text-blue-600 hover:text-blue-700 text-xs font-medium flex items-center space-x-1"
                                        title="Configurar zonas"
                                    >
                                        <Settings className="w-3 h-3" />
                                        <span>Configurar</span>
                                    </button>
                                </div>
                            </div>

                            {/* Metadata */}
                            {camera.metadata && Object.keys(camera.metadata).length > 0 && (
                                <div className="pt-3 border-t border-gray-100">
                                    <p className="text-xs text-gray-500 mb-2">Metadados:</p>
                                    <div className="space-y-1">
                                        {Object.entries(camera.metadata).map(([key, value]) => (
                                            <div key={key} className="text-xs text-gray-600">
                                                <span className="font-medium">{key}: </span>
                                                {String(value)}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Actions */}
                        <div className="p-4 bg-gray-50 border-t border-gray-200 flex flex-wrap gap-2 items-center justify-between">
                            <div className="flex flex-wrap gap-2">
                                {/* View Stream Button */}
                                {camera.enabled && (
                                    <button
                                        onClick={() => handleViewStream(camera)}
                                        className="flex items-center space-x-1 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                                        title="Visualizar Stream"
                                    >
                                        <Eye className="w-4 h-4" />
                                        <span>Ver Stream</span>
                                    </button>
                                )}

                                {/* Toggle Button */}
                                <button
                                    onClick={() => handleToggle(camera)}
                                    disabled={togglingId === camera.id}
                                    className={`flex items-center space-x-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${camera.enabled
                                            ? "bg-yellow-50 text-yellow-700 hover:bg-yellow-100"
                                            : "bg-green-50 text-green-700 hover:bg-green-100"
                                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                                    title={camera.enabled ? "Desativar" : "Ativar"}
                                >
                                    <Power className="w-4 h-4" />
                                    <span>
                                        {togglingId === camera.id
                                            ? "..."
                                            : camera.enabled
                                                ? "Desativar"
                                                : "Ativar"}
                                    </span>
                                </button>
                            </div>

                            <div className="flex gap-1">
                                {/* Edit Button */}
                                <button
                                    onClick={() => onEdit(camera)}
                                    className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                    title="Editar"
                                >
                                    <Edit className="w-4 h-4" />
                                </button>

                                {/* Delete Button */}
                                <button
                                    onClick={() => handleDelete(camera)}
                                    disabled={deletingId === camera.id}
                                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    title="Deletar"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        {/* Footer - Timestamps */}
                        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
                            Criada em:{" "}
                            {new Date(camera.created_at).toLocaleString("pt-BR")}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

export default CamerasList;
