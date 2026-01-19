/**
 * CamerasManager.tsx v2.0 - Cameras Manager Component
 * Main orchestrator for camera CRUD operations with streaming integration
 */

import { useState } from 'react';
import { Camera, Plus, RefreshCw, Search } from 'lucide-react';
import { toast } from 'sonner';

import { useCameras } from '../../hooks/useCameras';
import { CamerasList } from './CamerasList';
import { CameraForm } from './CameraForm';
import { streamAPI } from '../../services/streamApi';  // 🔥 NOVO
import type { Camera as CameraType, CameraFormData } from '../../types/cameras.types';

// ============================================
// COMPONENT
// ============================================

export function CamerasManager() {
    const {
        cameras,
        loading,
        error,
        createCamera,
        updateCamera,
        deleteCamera,
        toggleCamera,
        refresh
    } = useCameras();

    const [isFormOpen, setIsFormOpen] = useState(false);
    const [editingCamera, setEditingCamera] = useState<CameraType | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterEnabled, setFilterEnabled] = useState<'all' | 'active' | 'inactive'>('all');

    // ============================================
    // FILTERED CAMERAS
    // ============================================

    const filteredCameras = cameras.filter(camera => {
        // Search filter
        const matchesSearch =
            camera.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            camera.source.toLowerCase().includes(searchTerm.toLowerCase()) ||
            camera.location?.toLowerCase().includes(searchTerm.toLowerCase());

        // Status filter
        const matchesStatus =
            filterEnabled === 'all' ||
            (filterEnabled === 'active' && camera.enabled) ||
            (filterEnabled === 'inactive' && !camera.enabled);

        return matchesSearch && matchesStatus;
    });

    // ============================================
    // STATISTICS
    // ============================================

    const stats = {
        total: cameras.length,
        active: cameras.filter(c => c.enabled).length,
        inactive: cameras.filter(c => !c.enabled).length
    };

    // ============================================
    // HANDLERS
    // ============================================

    const handleCreateClick = () => {
        setEditingCamera(null);
        setIsFormOpen(true);
    };

    const handleEditClick = (camera: CameraType) => {
        setEditingCamera(camera);
        setIsFormOpen(true);
    };

    const handleFormCancel = () => {
        setIsFormOpen(false);
        setEditingCamera(null);
    };

    const handleFormSubmit = async (data: CameraFormData) => {
        try {
            if (editingCamera) {
                // Update
                const payload: any = {
                    name: data.name,
                    source: data.source,
                    location: data.location || null,
                    username: data.username || null,
                    enabled: data.enabled,
                    metadata: data.metadata
                };

                // Only include password if provided
                if (data.password) {
                    payload.password = data.password;
                }

                await updateCamera(editingCamera.id, payload);

                // 🔥 NOVO: Se mudou enabled, recarregar VisionSystem
                if (payload.enabled !== editingCamera.enabled) {
                    try {
                        await streamAPI.reloadCameras();
                        toast.success('VisionSystem atualizado!');
                    } catch (err) {
                        console.error('Error reloading cameras:', err);
                        toast.warning('Câmera atualizada, mas erro ao sincronizar streaming');
                    }
                }
            } else {
                // Create
                await createCamera({
                    name: data.name,
                    source: data.source,
                    location: data.location || null,
                    username: data.username || null,
                    password: data.password || null,
                    enabled: data.enabled,
                    metadata: data.metadata
                });

                // 🔥 NOVO: Se criou habilitada, recarregar VisionSystem
                if (data.enabled) {
                    try {
                        await streamAPI.reloadCameras();
                        toast.success('Câmera criada e carregada no VisionSystem!');
                    } catch (err) {
                        console.error('Error reloading cameras:', err);
                        toast.warning('Câmera criada, mas erro ao sincronizar streaming');
                    }
                }
            }

            setIsFormOpen(false);
            setEditingCamera(null);
        } catch (error) {
            // Error handled by form component
            throw error;
        }
    };

    const handleDelete = async (cameraId: number) => {
        await deleteCamera(cameraId);

        // 🔥 NOVO: Após deletar, recarregar VisionSystem
        try {
            await streamAPI.reloadCameras();
            toast.success('Câmera removida e VisionSystem atualizado!');
        } catch (err) {
            console.error('Error reloading cameras:', err);
            toast.warning('Câmera removida, mas erro ao sincronizar streaming');
        }
    };

    const handleToggle = async (cameraId: number) => {
        await toggleCamera(cameraId);

        // 🔥 NOVO: Após toggle, recarregar VisionSystem
        try {
            await streamAPI.reloadCameras();
            const camera = cameras.find(c => c.id === cameraId);
            const action = camera?.enabled ? 'desabilitada' : 'habilitada';
            toast.success(`Câmera ${action} e VisionSystem atualizado!`);
        } catch (err) {
            console.error('Error reloading cameras:', err);
            toast.warning('Status alterado, mas erro ao sincronizar streaming');
        }
    };

    const handleRefresh = async () => {
        try {
            await refresh();
            toast.success('Lista atualizada!');
        } catch (error) {
            toast.error('Erro ao atualizar lista');
        }
    };

    // ============================================
    // RENDER
    // ============================================

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <Camera className="w-8 h-8 text-blue-600" />
                        Câmeras
                    </h1>
                    <p className="text-gray-500 mt-1">
                        Gerencie as câmeras do sistema de monitoramento
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={handleRefresh}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        Atualizar
                    </button>

                    <button
                        onClick={handleCreateClick}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <Plus className="w-5 h-5" />
                        Nova Câmera
                    </button>
                </div>
            </div>

            {/* Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-600">Total de Câmeras</p>
                            <p className="text-3xl font-bold text-gray-900 mt-1">
                                {stats.total}
                            </p>
                        </div>
                        <Camera className="w-12 h-12 text-gray-400" />
                    </div>
                </div>

                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-600">Câmeras Ativas</p>
                            <p className="text-3xl font-bold text-green-600 mt-1">
                                {stats.active}
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-600">Câmeras Inativas</p>
                            <p className="text-3xl font-bold text-gray-400 mt-1">
                                {stats.inactive}
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                            <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex flex-col md:flex-row gap-4">
                    {/* Search */}
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Buscar câmeras..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>

                    {/* Status Filter */}
                    <div className="flex gap-2">
                        <button
                            onClick={() => setFilterEnabled('all')}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filterEnabled === 'all'
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            Todas
                        </button>

                        <button
                            onClick={() => setFilterEnabled('active')}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filterEnabled === 'active'
                                    ? 'bg-green-600 text-white'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            Ativas
                        </button>

                        <button
                            onClick={() => setFilterEnabled('inactive')}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filterEnabled === 'inactive'
                                    ? 'bg-gray-600 text-white'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            Inativas
                        </button>
                    </div>
                </div>

                {/* Results count */}
                {searchTerm && (
                    <div className="mt-3 text-sm text-gray-600">
                        {filteredCameras.length} câmera(s) encontrada(s)
                    </div>
                )}
            </div>

            {/* Error Display */}
            {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                    {error}
                </div>
            )}

            {/* Cameras List */}
            <CamerasList
                cameras={filteredCameras}
                onEdit={handleEditClick}
                onDelete={handleDelete}
                onToggle={handleToggle}
                loading={loading}
            />

            {/* Camera Form Modal */}
            <CameraForm
                camera={editingCamera}
                onSubmit={handleFormSubmit}
                onCancel={handleFormCancel}
                isOpen={isFormOpen}
            />
        </div>
    );
}

export default CamerasManager;
