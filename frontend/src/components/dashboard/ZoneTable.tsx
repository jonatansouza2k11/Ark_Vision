/**
 * ============================================================================
 * ZoneTable.tsx v3.0 - Dashboard Zone Statistics Table
 * ============================================================================
 * ✅ Suporta todos os 7 modos do ZoneMode enum
 * ✅ 100% compatível com backend v3.0
 * ============================================================================
 */

import { ZoneMode, ZONE_MODE_LABELS, ZONE_MODE_COLORS } from '../../types/zones.types';
import {
    AlertCircle,
    TrendingUp,
    ShieldAlert,
    Users,
    Eye,
    Circle,
    CircleDot
} from 'lucide-react';

// ============================================================================
// TIPOS PARA ZONAS NA TABELA
// ============================================================================
interface ZoneTableItem {
    zone_id: number;
    zone_name: string;
    mode: ZoneMode;
    current_count: number;
    time_empty: number;
    time_full: number;
    state: 'empty' | 'normal' | 'warning' | 'alert' | 'critical';
}

interface ZoneTableProps {
    zones: ZoneTableItem[];
}

// ============================================================================
// CONFIGURAÇÕES VISUAIS v3.0 - TODOS OS 7 MODOS
// ============================================================================

/**
 * ✅ Mapeamento COMPLETO de ícones para todos os 7 modos
 */
const modeIcons: Record<ZoneMode, any> = {
    // v3.0 modes (novos)
    [ZoneMode.OCCUPANCY]: Users,
    [ZoneMode.COUNTING]: TrendingUp,
    [ZoneMode.ALERT]: ShieldAlert,
    [ZoneMode.TRACKING]: Eye,

    // v2.0 legacy (antigos)
    [ZoneMode.GENERIC]: AlertCircle,
    [ZoneMode.EMPTY]: Circle,
    [ZoneMode.FULL]: CircleDot,
};

/**
 * ✅ Função para gerar classes Tailwind COMPLETA para todos os 7 modos
 */
const getModeColorClasses = (mode: ZoneMode): string => {
    const colorMap: Record<ZoneMode, string> = {
        // v3.0 modes
        [ZoneMode.OCCUPANCY]: 'text-blue-600 bg-blue-50 border-blue-200',
        [ZoneMode.COUNTING]: 'text-green-600 bg-green-50 border-green-200',
        [ZoneMode.ALERT]: 'text-red-600 bg-red-50 border-red-200',
        [ZoneMode.TRACKING]: 'text-purple-600 bg-purple-50 border-purple-200',

        // v2.0 legacy
        [ZoneMode.GENERIC]: 'text-gray-600 bg-gray-50 border-gray-200',
        [ZoneMode.EMPTY]: 'text-teal-600 bg-teal-50 border-teal-200',
        [ZoneMode.FULL]: 'text-orange-600 bg-orange-50 border-orange-200',
    };

    // ✅ Fallback case o modo não seja reconhecido
    return colorMap[mode] || 'text-gray-600 bg-gray-50 border-gray-200';
};

/**
 * Estados da zona (baseado no backend)
 */
const stateColors: Record<ZoneTableItem['state'], string> = {
    empty: 'bg-gray-100 text-gray-700',
    normal: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    alert: 'bg-orange-100 text-orange-700',
    critical: 'bg-red-100 text-red-700',
};

const stateLabels: Record<ZoneTableItem['state'], string> = {
    empty: 'Vazia',
    normal: 'Normal',
    warning: 'Aviso',
    alert: 'Alerta',
    critical: 'Crítico',
};

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================
export default function ZoneTable({ zones }: ZoneTableProps) {
    /**
     * Formata segundos para formato legível (Xs ou Xm Ys)
     */
    const formatTime = (seconds: number): string => {
        if (seconds < 60) return `${seconds.toFixed(0)}s`;
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}m ${secs}s`;
    };

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-xl font-bold text-gray-900">Zonas Monitoradas</h2>
                {zones.length > 0 && (
                    <p className="text-sm text-gray-500 mt-1">
                        {zones.length} {zones.length === 1 ? 'zona ativa' : 'zonas ativas'}
                    </p>
                )}
            </div>

            {/* Empty State */}
            {zones.length === 0 ? (
                <div className="p-12 text-center">
                    <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500 font-medium mb-2">Nenhuma zona definida</p>
                    <p className="text-sm text-gray-400">
                        Configure zonas para começar o monitoramento
                    </p>
                </div>
            ) : (
                <>
                    {/* Table */}
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
                                    // ✅ Obter ícone com fallback
                                    const Icon = modeIcons[zone.mode] || AlertCircle;

                                    return (
                                        <tr key={zone.zone_id} className="hover:bg-gray-50 transition-colors">
                                            {/* Nome da Zona */}
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="flex items-center gap-3">
                                                    {/* Indicador de cor hex */}
                                                    <div
                                                        className="w-3 h-3 rounded-full flex-shrink-0 border-2 border-white shadow-sm"
                                                        style={{ backgroundColor: ZONE_MODE_COLORS[zone.mode] }}
                                                        title={`Cor: ${ZONE_MODE_COLORS[zone.mode]}`}
                                                    />
                                                    <div>
                                                        <span className="font-medium text-gray-900">
                                                            {zone.zone_name}
                                                        </span>
                                                        <div className="text-xs text-gray-500">
                                                            ID: {zone.zone_id}
                                                        </div>
                                                    </div>
                                                </div>
                                            </td>

                                            {/* Modo */}
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div
                                                    className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border ${getModeColorClasses(zone.mode)}`}
                                                >
                                                    <Icon className="w-4 h-4" />
                                                    <span className="text-sm font-medium">
                                                        {ZONE_MODE_LABELS[zone.mode]}
                                                    </span>
                                                </div>
                                            </td>

                                            {/* Contagem */}
                                            <td className="px-6 py-4 whitespace-nowrap text-center">
                                                <div>
                                                    <span className="text-lg font-semibold text-gray-900">
                                                        {zone.current_count}
                                                    </span>
                                                    <div className="text-xs text-gray-500">
                                                        {zone.current_count === 1 ? 'pessoa' : 'pessoas'}
                                                    </div>
                                                </div>
                                            </td>

                                            {/* Tempo Vazia */}
                                            <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-600">
                                                {formatTime(zone.time_empty)}
                                            </td>

                                            {/* Tempo Cheia */}
                                            <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-600">
                                                {formatTime(zone.time_full)}
                                            </td>

                                            {/* Estado */}
                                            <td className="px-6 py-4 whitespace-nowrap text-center">
                                                <span
                                                    className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${stateColors[zone.state]}`}
                                                >
                                                    {stateLabels[zone.state]}
                                                </span>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>

                    {/* Footer Summary */}
                    <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
                        <div className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-6">
                                <div>
                                    <span className="text-gray-600">Total de zonas:</span>
                                    <span className="font-semibold text-gray-900 ml-2">
                                        {zones.length}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-gray-600">Pessoas detectadas:</span>
                                    <span className="font-semibold text-gray-900 ml-2">
                                        {zones.reduce((sum, zone) => sum + zone.current_count, 0)}
                                    </span>
                                </div>
                            </div>

                            {/* Indicador de atualização em tempo real */}
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                <span>Atualização em tempo real</span>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
