// src/components/dashboard/ZoneTable.tsx
import { ZoneStatus } from '../../types/dashboard';
import { AlertCircle, TrendingUp, Activity, ShieldAlert } from 'lucide-react';

interface ZoneTableProps {
    zones: ZoneStatus[];
}

const modeIcons = {
    FLOW: TrendingUp,
    QUEUE: Activity,
    CRITICAL: ShieldAlert,
    GENERIC: AlertCircle,
};

const modeColors = {
    FLOW: 'text-blue-600 bg-blue-50',
    QUEUE: 'text-yellow-600 bg-yellow-50',
    CRITICAL: 'text-red-600 bg-red-50',
    GENERIC: 'text-gray-600 bg-gray-50',
};

const stateColors = {
    empty: 'bg-gray-100 text-gray-700',
    normal: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    alert: 'bg-orange-100 text-orange-700',
    critical: 'bg-red-100 text-red-700',
};

export default function ZoneTable({ zones }: ZoneTableProps) {
    const formatTime = (seconds: number) => {
        if (seconds < 60) return `${seconds.toFixed(0)}s`;
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}m ${secs}s`;
    };

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-xl font-bold text-gray-900">Zonas Monitoradas</h2>
            </div>

            {zones.length === 0 ? (
                <div className="p-12 text-center">
                    <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500 font-medium mb-2">Nenhuma zona definida</p>
                    <p className="text-sm text-gray-400">
                        Configure zonas em Configurações → Safe Zones
                    </p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                                    Zona
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                                    Modo
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                                    Contagem
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                                    Tempo Vazia
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                                    Tempo Cheia
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                                    Estado
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                            {zones.map((zone) => {
                                const Icon = modeIcons[zone.mode];
                                return (
                                    <tr key={zone.zone_id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="font-medium text-gray-900">{zone.zone_name}</span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full ${modeColors[zone.mode]}`}>
                                                <Icon className="w-4 h-4" />
                                                <span className="text-sm font-medium">{zone.mode}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-center">
                                            <span className="text-lg font-semibold text-gray-900">
                                                {zone.current_count}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-600">
                                            {formatTime(zone.time_empty)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-600">
                                            {formatTime(zone.time_full)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-center">
                                            <span
                                                className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${stateColors[zone.state]
                                                    }`}
                                            >
                                                {zone.state.toUpperCase()}
                                            </span>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
