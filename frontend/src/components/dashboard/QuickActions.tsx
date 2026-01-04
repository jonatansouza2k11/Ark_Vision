// frontend/src/components/dashboard/QuickActions.tsx
import { Link } from 'react-router-dom';
import { Settings, FileText } from 'lucide-react';

export default function QuickActions() {
    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <h3 className="font-semibold text-gray-900 mb-4 text-sm">Ações Rápidas</h3>
            <div className="space-y-2">
                <Link
                    to="/settings"
                    className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                    <Settings className="w-4 h-4" />
                    Configurações
                </Link>
                <Link
                    to="/logs"
                    className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-gray-700 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
                >
                    <FileText className="w-4 h-4" />
                    Ver Logs
                </Link>
            </div>
        </div>
    );
}
