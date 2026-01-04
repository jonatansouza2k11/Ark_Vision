// src/components/dashboard/SystemInfoBanner.tsx
import { CheckCircle2, AlertCircle, XCircle, Pause } from 'lucide-react';

interface SystemInfoBannerProps {
    modelName: string;
    videoSource: string;
    status: 'online' | 'offline' | 'paused' | 'stopped';
}

export default function SystemInfoBanner({
    modelName,
    videoSource,
    status,
}: SystemInfoBannerProps) {
    const statusConfig = {
        online: {
            icon: CheckCircle2,
            color: 'text-green-600',
            bgColor: 'bg-green-50',
            borderColor: 'border-green-200',
            label: 'Online',
        },
        offline: {
            icon: XCircle,
            color: 'text-red-600',
            bgColor: 'bg-red-50',
            borderColor: 'border-red-200',
            label: 'Offline',
        },
        paused: {
            icon: Pause,
            color: 'text-yellow-600',
            bgColor: 'bg-yellow-50',
            borderColor: 'border-yellow-200',
            label: 'Pausado',
        },
        stopped: {
            icon: AlertCircle,
            color: 'text-gray-600',
            bgColor: 'bg-gray-50',
            borderColor: 'border-gray-200',
            label: 'Parado',
        },
    };

    const config = statusConfig[status];
    const Icon = config.icon;

    return (
        <div
            className={`${config.bgColor} ${config.borderColor} border rounded-lg p-4 flex items-center justify-between`}
        >
            <div className="flex items-center gap-4">
                <Icon className={`w-6 h-6 ${config.color}`} />
                <div>
                    <p className="text-sm font-medium text-gray-700">
                        <span className="font-semibold">Modelo:</span> {modelName}
                        <span className="mx-2">•</span>
                        <span className="font-semibold">Fonte:</span> {videoSource}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                        A zona é definida no modal Safe Zone Map → Map
                    </p>
                </div>
            </div>

            <div className="flex items-center gap-2">
                <span className={`text-sm font-semibold ${config.color}`}>
                    {config.label}
                </span>
            </div>
        </div>
    );
}
