// src/pages/Dashboard.tsx
import { useState } from 'react';
import { Users, Activity, RefreshCw, CheckCircle2 } from 'lucide-react';
import MainLayout from '../components/layout/MainLayout';
import { useAuthStore } from '../store/authStore';
import VideoStream from '../components/dashboard/VideoStream';
import SystemInfoBanner from '../components/dashboard/SystemInfoBanner';

// Componente StatCard inline
interface StatCardProps {
    icon: React.ElementType;
    iconColor: string;
    title: string;
    value: number;
    subtitle?: string;
}

function StatCard({ icon: Icon, iconColor, title, value, subtitle }: StatCardProps) {
    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-lg ${iconColor}`}>
                    <Icon className="w-6 h-6 text-white" />
                </div>
            </div>
            <div className="space-y-1">
                <p className="text-3xl font-bold text-gray-900">{value.toLocaleString()}</p>
                <p className="text-sm font-medium text-gray-600">{title}</p>
                {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
            </div>
        </div>
    );
}

export default function Dashboard() {
    const { user } = useAuthStore();
    const [loading, setLoading] = useState(false);

    // Mock data
    const stats = {
        cameras: 12,
        detections: 348,
        status: 'Online',
    };

    const systemInfo = {
        modelName: 'YOLOv8n',
        videoSource: 'Webcam (0)',
        status: 'online' as const,
    };

    const handleRefresh = async () => {
        setLoading(true);
        try {
            // TODO: Buscar dados da API
            await new Promise((resolve) => setTimeout(resolve, 1000));
        } catch (error) {
            console.error('Erro ao atualizar dashboard:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <MainLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
                        <p className="text-gray-600 mt-1">
                            Bem-vindo, <span className="font-semibold">{user?.username}</span>!
                        </p>
                    </div>

                    <button
                        onClick={handleRefresh}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        Atualizar
                    </button>
                </div>

                {/* System Info Banner */}
                <SystemInfoBanner
                    modelName={systemInfo.modelName}
                    videoSource={systemInfo.videoSource}
                    status={systemInfo.status}
                />

                {/* Video Stream */}
                <VideoStream />

                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <StatCard
                        icon={Users}
                        iconColor="bg-blue-500"
                        title="Total de Câmeras"
                        value={stats.cameras}
                    />

                    <StatCard
                        icon={Activity}
                        iconColor="bg-green-500"
                        title="Detecções Hoje"
                        value={stats.detections}
                    />

                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <div className="flex items-center justify-between mb-4">
                            <div className="p-3 rounded-lg bg-green-500">
                                <CheckCircle2 className="w-6 h-6 text-white" />
                            </div>
                        </div>
                        <div className="space-y-1">
                            <p className="text-3xl font-bold text-green-600">{stats.status}</p>
                            <p className="text-sm font-medium text-gray-600">Status Sistema</p>
                        </div>
                    </div>
                </div>

                {/* Atividade Recente */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Atividade Recente</h2>
                    <div className="text-center py-12">
                        <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                        <p className="text-gray-500">Nenhuma atividade recente</p>
                    </div>
                </div>
            </div>
        </MainLayout>
    );
}
