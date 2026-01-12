/**
 * CamerasManager.tsx - Cameras Manager Component
 * Main orchestrator for camera CRUD operations
 */

import { useState } from 'react';
import { Camera, Plus, RefreshCw, Search } from 'lucide-react';
import { toast } from 'sonner';
import { useCameras } from '../../hooks/useCameras';
import { CamerasList } from './CamerasList';
import { CameraForm } from './CameraForm';
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
    };

    const handleToggle = async (cameraId: number) => {
        await toggleCamera(cameraId);
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
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center space-x-3">
                        <Camera size={32} />
                        <span>Câmeras</span>
                    </h1>
                    <p className="text-gray-600 mt-1">
                        Gerencie as câmeras do sistema de monitoramento
                    </p>
                </div>



                <div className="flex items-center space-x-3">
                    <button
                        onClick={handleRefresh}
                        disabled={loading}
                        className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                        title="Atualizar"
                    >
                        <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                        <span className="hidden sm:inline">Atualizar</span>
                    </button>

                    <button
                        onClick={handleCreateClick}
                        className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <Plus size={18} />
                        <span>Nova Câmera</span>
                    </button>
                </div>
            </div>

            {/* Statistics */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
                    <div className="text-sm text-gray-600 mb-1">Total de Câmeras</div>
                    <div className="text-3xl font-bold text-gray-900">{stats.total}</div>
                </div>

                <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
                    <div className="text-sm text-gray-600 mb-1">Câmeras Ativas</div>
                    <div className="text-3xl font-bold text-green-600">{stats.active}</div>
                </div>

                <div className="bg-white rounded-lg shadow p-6 border-l-4 border-gray-500">
                    <div className="text-sm text-gray-600 mb-1">Câmeras Inativas</div>
                    <div className="text-3xl font-bold text-gray-600">{stats.inactive}</div>
                </div>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg shadow p-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                    {/* Search */}
                    <div className="flex-1 w-full sm:w-auto">
                        <div className="relative">
                            <Search size={18} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Buscar câmeras..."
                                value={searchTerm}
                                onChange={e => setSearchTerm(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>
                    </div>

                    {/* Status Filter */}
                    <div className="flex items-center space-x-2">
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
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-red-700">{error}</p>
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
