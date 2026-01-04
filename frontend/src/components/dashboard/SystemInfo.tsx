// frontend/src/components/dashboard/SystemInfo.tsx
import { useYOLOStream } from '../../hooks/useYOLOStream';

export default function SystemInfo() {
    const { stats } = useYOLOStream();

    const getStatusInfo = () => {
        const status = stats?.system_status || 'stopped'; // ✅ COM underscore
        
        const statusMap = {
            'running': { 
                text: 'Rodando', 
                color: 'text-green-500',
                dotColor: 'bg-green-500'
            },
            'paused': { 
                text: 'Pausado', 
                color: 'text-yellow-500',
                dotColor: 'bg-yellow-500'
            },
            'stopped': { 
                text: 'Parado', 
                color: 'text-red-500',
                dotColor: 'bg-red-500'
            }
        };

        return statusMap[status as keyof typeof statusMap] || statusMap.stopped;
    };

    const statusInfo = getStatusInfo();

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <h3 className="font-semibold text-gray-900 mb-4 text-sm">Informações do Sistema</h3>
            <div className="space-y-3">
                <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">Modelo</span>
                    <span className="text-sm font-medium text-gray-900">
                        {stats?.preset ? `YOLOv8 (${stats.preset})` : 'YOLOv8n'}
                    </span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">Detecções</span>
                    <span className="text-sm font-medium text-gray-900">
                        {stats?.detected_count || 0} {/* ✅ COM underscore */}
                    </span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">Status</span>
                    <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${statusInfo.dotColor} ${stats?.system_status === 'running' ? 'animate-pulse' : ''}`} />
                        <span className={`text-sm font-semibold ${statusInfo.color}`}>
                            {statusInfo.text}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
