// src/components/dashboard/ActivityTimeline.tsx
import { Activity } from '../../types/dashboard';
import { AlertTriangle, Activity as ActivityIcon, Settings, Clock } from 'lucide-react';

interface ActivityTimelineProps {
    activities: Activity[];
}

export default function ActivityTimeline({ activities }: ActivityTimelineProps) {
    const getIcon = (type: Activity['type']) => {
        switch (type) {
            case 'alert':
                return AlertTriangle;
            case 'detection':
                return ActivityIcon;
            case 'system_action':
                return Settings;
            default:
                return Clock;
        }
    };

    const getColor = (type: Activity['type']) => {
        switch (type) {
            case 'alert':
                return 'bg-red-100 text-red-600';
            case 'detection':
                return 'bg-blue-100 text-blue-600';
            case 'system_action':
                return 'bg-gray-100 text-gray-600';
            default:
                return 'bg-gray-100 text-gray-600';
        }
    };

    const formatDate = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

        if (diff < 60) return 'Agora';
        if (diff < 3600) return `${Math.floor(diff / 60)}m atrás`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
        return date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-xl font-bold text-gray-900">Atividade Recente</h2>
            </div>

            {activities.length === 0 ? (
                <div className="p-12 text-center">
                    <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">Nenhuma atividade recente</p>
                </div>
            ) : (
                <div className="divide-y divide-gray-200">
                    {activities.map((activity) => {
                        const Icon = getIcon(activity.type);
                        const colorClass = getColor(activity.type);

                        return (
                            <div key={activity.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                                <div className="flex items-start gap-4">
                                    <div className={`p-2 rounded-lg ${colorClass}`}>
                                        <Icon className="w-5 h-5" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-gray-900">{activity.message}</p>
                                        {activity.zone_name && (
                                            <p className="text-xs text-gray-500 mt-1">Zona: {activity.zone_name}</p>
                                        )}
                                    </div>
                                    <div className="text-xs text-gray-500 whitespace-nowrap">
                                        {formatDate(activity.timestamp)}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
