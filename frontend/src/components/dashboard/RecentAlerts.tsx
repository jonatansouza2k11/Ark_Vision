// src/components/dashboard/RecentAlerts.tsx
import { Clock, AlertTriangle, Info, ShieldAlert } from 'lucide-react';
import type { YOLOStats, AlertRecent } from '../../types/dashboard';

interface RecentAlertsProps {
    stats: YOLOStats | null;
}

function RecentAlerts({ stats }: RecentAlertsProps) {
    // ✅ CORRETO: usar snake_case
    const alerts: AlertRecent[] = stats?.recent_alerts || [];

    const getIcon = (type: string) => {
        switch (type) {
            case 'critical': return <ShieldAlert className="text-red-500" />;
            case 'warning': return <AlertTriangle className="text-yellow-500" />;
            default: return <Info className="text-blue-500" />;
        }
    };

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4">Recent Alerts</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
                {alerts.length === 0 ? (
                    <p className="text-gray-500">No recent alerts</p>
                ) : (
                    alerts.map((alert, index) => (
                        <div key={index} className="flex items-start gap-3 p-3 bg-gray-50 rounded">
                            {getIcon(alert.type)}
                            <div className="flex-1">
                                <p className="text-sm font-medium">{alert.message}</p>
                                <p className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                                    <Clock size={12} />
                                    {alert.timestamp}
                                </p>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

export default RecentAlerts;
