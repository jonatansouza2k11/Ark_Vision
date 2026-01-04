// src/components/dashboard/StatsCard.tsx
import type { YOLOStats } from '../../types/dashboard';

interface StatsCardProps {
    stats: YOLOStats | null;
}

const StatsCard = ({ stats }: StatsCardProps) => {
    const cards = [
        {
            label: 'In Zone',
            value: stats?.in_zone || 0,
            color: 'text-green-600',
            bgColor: 'bg-green-50',
        },
        {
            label: 'Out Zone',
            value: stats?.out_zone || 0,
            color: 'text-yellow-600',
            bgColor: 'bg-yellow-50',
        },
        {
            label: 'Total Detections',
            value: stats?.detected_count || 0,
            color: 'text-blue-600',
            bgColor: 'bg-blue-50',
        },
        {
            label: 'FPS',
            value: (stats?.fps_avg || 0).toFixed(1),
            color: 'text-purple-600',
            bgColor: 'bg-purple-50',
        },
    ];

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {cards.map((card, index) => (
                <div key={index} className={`${card.bgColor} rounded-lg shadow-md p-6`}>
                    <p className="text-sm text-gray-600 mb-2">{card.label}</p>
                    <p className={`text-3xl font-bold ${card.color}`}>{card.value}</p>
                </div>
            ))}
        </div>
    );
};

export default StatsCard;
