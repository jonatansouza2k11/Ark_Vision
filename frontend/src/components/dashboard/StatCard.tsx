// src/components/dashboard/StatCard.tsx
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
    icon: LucideIcon;
    iconColor: string;
    title: string;
    value: number;
    subtitle?: string;
    trend?: {
        value: number;
        isPositive: boolean;
    };
}

export default function StatCard({
    icon: Icon,
    iconColor,
    title,
    value,
    subtitle,
    trend,
}: StatCardProps) {
    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-lg ${iconColor}`}>
                    <Icon className="w-6 h-6 text-white" />
                </div>
                {trend && (
                    <div
                        className={`text-sm font-semibold ${trend.isPositive ? 'text-green-600' : 'text-red-600'
                            }`}
                    >
                        {trend.isPositive ? '+' : '-'}
                        {Math.abs(trend.value)}%
                    </div>
                )}
            </div>
            <div className="space-y-1">
                <p className="text-3xl font-bold text-gray-900">{value.toLocaleString()}</p>
                <p className="text-sm font-medium text-gray-600">{title}</p>
                {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
            </div>
        </div>
    );
}
