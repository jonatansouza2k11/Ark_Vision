// frontend/src/components/dashboard/ZoneTable.tsx

/**
 * ZoneTable.tsx v5.3
 * - Agrupamento por modo com seções colapsáveis
 * - Filtro por câmera
 * - Colunas dinâmicas por regra de negócio
 * - Animação de pulsação em alertas
 */

import React, { useState } from "react";
import {
    ZoneMode,
    ZONE_MODE_LABELS,
    ZONE_MODE_COLORS,
} from "../../types/zones.types";

import {
    AlertCircle,
    TrendingUp,
    ShieldAlert,
    Users,
    Eye,
    UserPlus,
    ChevronDown,
    ChevronUp,
    Camera as CameraIcon,
    RefreshCw,
} from "lucide-react";

import useCameras from "../../hooks/useCameras";
import type { Camera } from "../../types/cameras.types";

// ============================================
// CSS PARA ANIMAÇÃO DE ALERTA SUAVE
// ============================================

const alertAnimationStyles = `
@keyframes alertPulse {
  0%, 100% {
    background-color: rgba(239, 68, 68, 0.05);
    border-color: rgba(239, 68, 68, 0.2);
  }
  50% {
    background-color: rgba(239, 68, 68, 0.15);
    border-color: rgba(239, 68, 68, 0.4);
  }
}

.alert-pulse {
  animation: alertPulse 2s ease-in-out infinite;
}
`;

// Injetar estilos no document (apenas no browser)
if (typeof document !== "undefined") {
    const styleId = "zone-alert-animation";
    if (!document.getElementById(styleId)) {
        const style = document.createElement("style");
        style.id = styleId;
        style.textContent = alertAnimationStyles;
        document.head.appendChild(style);
    }
}

// ============================================
// TYPES
// ============================================

type ZoneState =
    | "empty"
    | "normal"
    | "warning"
    | "alert"
    | "critical"
    | "pending"
    | "emptypending"
    | "fullpending";

type CountDirection = "in" | "out" | "both";
type ResetInterval = "none" | "hourly" | "daily" | "weekly" | "monthly";

export interface ZoneTableItem {
    zoneid: number;
    zonename: string;
    mode: ZoneMode;

    currentcount: number;
    timeempty: number;
    timefull: number;

    state: ZoneState;

    // Capacity
    maxcapacity?: number;
    fulltimeout?: number;

    // Counting
    countin?: number;
    countout?: number;
    countdirection?: CountDirection;

    // Alert / metadata
    alert?: boolean;
    alertmessage?: string | null;
    resetinterval?: ResetInterval;
    lastreset?: string | null;

    // Relacionamento com câmera
    cameraid?: number | null;

    // Queue KPIs (modo fila)
    queue_length?: number;
    avg_wait_time?: number;
    max_wait_time?: number;
    abandon_count?: number;
    abandon_avg_wait?: number;
    last_abandon_wait?: number;
}


interface ZoneTableProps {
    zones: ZoneTableItem[];
}

// ============================================
// VISUAL CONFIG
// ============================================
type LucideIcon = React.ComponentType<React.SVGProps<SVGSVGElement>>;

const modeIcons: Record<ZoneMode, LucideIcon> = {
    [ZoneMode.OCCUPANCY]: Users,
    [ZoneMode.COUNTING]: TrendingUp,
    [ZoneMode.ALERT]: ShieldAlert,
    [ZoneMode.TRACKING]: Eye,
    [ZoneMode.CAPACITY]: UserPlus,
    [ZoneMode.QUEUE]: Users,
    [ZoneMode.GENERIC]: AlertCircle,
    [ZoneMode.EMPTY]: AlertCircle,
    [ZoneMode.FULL]: AlertCircle,
};;

const stateColors: Record<ZoneState, string> = {
    empty: "bg-gray-100 text-gray-700",
    normal: "bg-green-100 text-green-700",
    warning: "bg-yellow-100 text-yellow-700",
    alert: "bg-orange-100 text-orange-700",
    critical: "bg-red-100 text-red-700",
    pending: "bg-blue-100 text-blue-700",
    emptypending: "bg-gray-200 text-gray-600",
    fullpending: "bg-yellow-200 text-yellow-600",
};

const stateLabels: Record<ZoneState, string> = {
    empty: "Vazia",
    normal: "Normal",
    warning: "Aviso",
    alert: "Alerta",
    critical: "Crítico",
    pending: "Pendente",
    emptypending: "Vazia aguardando",
    fullpending: "Cheia aguardando",
};

// ============================================
// HELPER FUNCTIONS
// ============================================

// Governança única de label de estado
function getStateLabel(zone: ZoneTableItem): string {
    // Tracking tem texto especial
    if (zone.mode === ZoneMode.TRACKING) {
        const count = zone.currentcount;
        if (count === 0) return "Rastreando vazia";
        if (count === 1) return "1 objeto rastreado";
        return `${count} objetos rastreados`;
    }

    return stateLabels[zone.state] ?? "Normal";
}

function formatTime(seconds: number): string {
    if (!Number.isFinite(seconds) || seconds < 0) {
        return "--";
    }

    if (seconds < 60) {
        return `${seconds.toFixed(0)}s`;
    }

    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}m ${secs}s`;
}

function getOccupancyPercent(
    count: number,
    maxCapacity: number | undefined
): number {
    const cap = maxCapacity ?? 50;
    if (cap <= 0) return 0;
    return Math.round((count / cap) * 100);
}

function getProgressColor(percent: number): string {
    if (percent >= 100) return "bg-red-500";
    if (percent >= 90) return "bg-yellow-500";
    return "bg-green-500";
}

function getModeColorClasses(mode: ZoneMode): string {
    const colorMap: Record<ZoneMode, string> = {
        [ZoneMode.OCCUPANCY]: "text-blue-600 bg-blue-50 border-blue-200",
        [ZoneMode.COUNTING]: "text-green-600 bg-green-50 border-green-200",
        [ZoneMode.ALERT]: "text-red-600 bg-red-50 border-red-200",
        [ZoneMode.TRACKING]: "text-purple-600 bg-purple-50 border-purple-200",
        [ZoneMode.CAPACITY]: "text-amber-600 bg-amber-50 border-amber-200",
        [ZoneMode.QUEUE]: "text-indigo-600 bg-indigo-50 border-indigo-200",
        [ZoneMode.GENERIC]: "text-gray-600 bg-gray-50 border-gray-200",
        [ZoneMode.EMPTY]: "text-teal-600 bg-teal-50 border-teal-200",
        [ZoneMode.FULL]: "text-orange-600 bg-orange-50 border-orange-200",
    };

    return (
        colorMap[mode] || "text-gray-600 bg-gray-50 border-gray-200"
    );
}

// ============================================
// COMPONENT
// ============================================

const ZoneTable: React.FC<ZoneTableProps> = ({ zones }) => {
    // Hook de câmeras – desestrutura o array corretamente
    const { cameras } = useCameras();
    const [selectedCameraId, setSelectedCameraId] = useState<"all" | number>(
        "all"
    );
    const [expandedModes, setExpandedModes] = useState<Set<ZoneMode>>(
        () => new Set(Object.values(ZoneMode))
    );

    // Filtro por câmera
    const filteredZones = zones.filter((zone) => {
        if (selectedCameraId === "all") return true;
        return zone.cameraid === selectedCameraId;
    });

    // Agrupamento por modo
    const groupedByMode = filteredZones.reduce<
        Record<ZoneMode, ZoneTableItem[]>
    >(
        (acc, zone) => {
            const mode = zone.mode;
            if (!acc[mode]) {
                acc[mode] = [];
            }
            acc[mode].push(zone);
            return acc;
        },
        {} as Record<ZoneMode, ZoneTableItem[]>
    );

    const toggleModeExpansion = (mode: ZoneMode) => {
        setExpandedModes((prev) => {
            const newSet = new Set(prev);
            if (newSet.has(mode)) {
                newSet.delete(mode);
            } else {
                newSet.add(mode);
            }
            return newSet;
        });
    };

    // Cabeçalhos dinâmicos por modo
    const renderHeadersForMode = (mode: ZoneMode) => {
        switch (mode) {
            case ZoneMode.CAPACITY:
                return (
                    <th
                        className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider"
                        colSpan={3}
                    >
                        Ocupação
                    </th>
                );

            case ZoneMode.COUNTING:
                return (
                    <th
                        className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider"
                        colSpan={3}
                    >
                        Contagem
                    </th>
                );

            case ZoneMode.ALERT:
                return (
                    <>
                        <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                            Contagem
                        </th>
                        <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                            Tempo em alerta
                        </th>
                    </>
                );

            case ZoneMode.TRACKING:
                return (
                    <th
                        className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider"
                        colSpan={3}
                    >
                        Rastreamento
                    </th>
                );

            case ZoneMode.OCCUPANCY:
            case ZoneMode.GENERIC:
            case ZoneMode.EMPTY:
            case ZoneMode.FULL:
            default:
                return (
                    <>
                        <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                            Contagem
                        </th>
                        <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                            Tempo vazia
                        </th>
                        <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                            Tempo cheia
                        </th>
                    </>
                );
        }
    };

    // Célula de métricas por modo
    const renderMetricsCell = (zone: ZoneTableItem) => {
        switch (zone.mode) {
            case ZoneMode.CAPACITY: {
                const maxCap = zone.maxcapacity ?? 50;
                const percent = getOccupancyPercent(zone.currentcount, maxCap);

                const capacityTimeout = zone.fulltimeout ?? 10;
                const timeElapsed = zone.timefull;
                const timeRemaining = Math.max(0, capacityTimeout - timeElapsed);

                const isInPending =
                    percent >= 100 &&
                    timeRemaining > 0 &&
                    (zone.state === "pending" || zone.state === "fullpending");

                const showCritical =
                    percent >= 100 && !isInPending && zone.state === "critical";

                return (
                    <td className="px-6 py-4 whitespace-nowrap text-center" colSpan={3}>
                        <div className="space-y-2">
                            <div className="text-center">
                                <span className="text-2xl font-bold text-gray-900">
                                    {percent}%
                                </span>
                            </div>

                            <div className="w-full bg-gray-200 rounded-full h-2">
                                <div
                                    className={`h-2 rounded-full transition-all ${getProgressColor(
                                        percent
                                    )}`}
                                    style={{ width: `${Math.min(percent, 100)}%` }}
                                />
                            </div>

                            <div className="text-xs text-gray-500 text-center">
                                {zone.currentcount}/{maxCap} detecções
                            </div>

                            {isInPending && (
                                <div className="text-xs font-semibold text-amber-600 text-center animate-pulse">
                                    Alerta em {Math.ceil(timeRemaining)}s
                                </div>
                            )}

                            {showCritical && (
                                <div className="text-xs font-bold text-red-600 text-center">
                                    LOTAÇÃO MÁXIMA!
                                </div>
                            )}
                        </div>
                    </td>
                );
            }

            case ZoneMode.OCCUPANCY:
            case ZoneMode.GENERIC:
            case ZoneMode.EMPTY:
            case ZoneMode.FULL: {
                return (
                    <>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                            <div className="text-center">
                                <div className="text-2xl font-bold text-gray-900">
                                    {zone.currentcount}
                                </div>
                                <div className="text-xs text-gray-500">objetos</div>
                            </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                            <div className="text-center">
                                <div className="text-sm font-medium text-gray-900">
                                    {formatTime(zone.timeempty)}
                                </div>
                                <div className="text-xs text-gray-500">vazia</div>
                            </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                            <div className="text-center">
                                <div className="text-sm font-medium text-gray-900">
                                    {formatTime(zone.timefull)}
                                </div>
                                <div className="text-xs text-gray-500">cheia</div>
                            </div>
                        </td>
                    </>
                );
            }

            case ZoneMode.COUNTING: {
                const countIn = zone.countin ?? 0;
                const countOut = zone.countout ?? 0;
                const balance = countIn - countOut;
                const direction: CountDirection = zone.countdirection ?? "both";

                const hasAlert = zone.alert === true;
                const alertMessage = zone.alertmessage ?? null;

                const resetLabelMap: Record<ResetInterval, string> = {
                    none: "Sem reset automático",
                    hourly: "Reset horário",
                    daily: "Reset diário",
                    weekly: "Reset semanal",
                    monthly: "Reset mensal",
                };
                const resetLabel =
                    (zone.resetinterval && resetLabelMap[zone.resetinterval]) ||
                    "Reset padrão";

                return (
                    <td className="px-6 py-4 whitespace-nowrap text-center" colSpan={3}>
                        <div className="space-y-3">
                            {/* Grid de contadores */}
                            <div className="grid grid-cols-3 gap-4">
                                {/* Entradas */}
                                {(direction === "in" || direction === "both") && (
                                    <div className="text-center">
                                        <div className="flex items-center justify-center gap-1 mb-1">
                                            <svg
                                                className="w-4 h-4 text-green-600"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                            >
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M17 8l4 4m0 0l-4 4m4-4H3"
                                                />
                                            </svg>
                                            <span className="text-xs font-semibold text-gray-600 uppercase">
                                                IN
                                            </span>
                                        </div>
                                        <div className="text-2xl font-bold text-green-600">
                                            {countIn}
                                        </div>
                                    </div>
                                )}

                                {/* Saídas */}
                                {(direction === "out" || direction === "both") && (
                                    <div className="text-center">
                                        <div className="flex items-center justify-center gap-1 mb-1">
                                            <svg
                                                className="w-4 h-4 text-red-600"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                            >
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M7 16l-4-4m0 0l4-4m-4 4h18"
                                                />
                                            </svg>
                                            <span className="text-xs font-semibold text-gray-600 uppercase">
                                                OUT
                                            </span>
                                        </div>
                                        <div className="text-2xl font-bold text-red-600">
                                            {countOut}
                                        </div>
                                    </div>
                                )}

                                {/* Saldo (apenas both) */}
                                {direction === "both" && (
                                    <div className="text-center">
                                        <div className="flex items-center justify-center gap-1 mb-1">
                                            <svg
                                                className="w-4 h-4 text-blue-600"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                            >
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                                                />
                                            </svg>
                                            <span className="text-xs font-semibold text-gray-600 uppercase">
                                                Saldo
                                            </span>
                                        </div>
                                        <div
                                            className={`text-2xl font-bold ${balance > 0
                                                    ? "text-blue-600"
                                                    : balance < 0
                                                        ? "text-orange-600"
                                                        : "text-gray-600"
                                                }`}
                                        >
                                            {balance}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Modo in/out only – texto auxiliar */}
                            {direction === "in" && (
                                <div className="col-span-2 flex items-center justify-center">
                                    <div className="text-center">
                                        <div className="text-xs text-gray-500 mb-1">
                                            Modo <span className="font-semibold">Apenas Entradas</span>
                                        </div>
                                        <div className="text-sm text-gray-400">
                                            Saídas não são contabilizadas.
                                        </div>
                                    </div>
                                </div>
                            )}

                            {direction === "out" && (
                                <div className="col-span-2 flex items-center justify-center">
                                    <div className="text-center">
                                        <div className="text-xs text-gray-500 mb-1">
                                            Modo <span className="font-semibold">Apenas Saídas</span>
                                        </div>
                                        <div className="text-sm text-gray-400">
                                            Entradas não são contabilizadas.
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Linha divisória e texto do saldo */}
                            {direction === "both" && (
                                <div className="pt-2 border-t border-gray-100">
                                    <div className="text-xs text-gray-500 text-center">
                                        {balance > 0 &&
                                            `${balance} objetos dentro da zona (mais entradas que saídas).`}
                                        {balance === 0 &&
                                            "Entradas e saídas equilibradas (zona zerada)."}
                                        {balance < 0 &&
                                            "Mais saídas que entradas (pode indicar reset ou erro)."}
                                    </div>
                                </div>
                            )}

                            {/* Status de alerta & reset */}
                            <div className="pt-2 border-t border-gray-100">
                                {hasAlert && alertMessage ? (
                                    <div className="flex items-center justify-center gap-2 text-xs font-semibold text-red-600">
                                        <AlertCircle className="w-4 h-4" />
                                        <span>{alertMessage}</span>
                                    </div>
                                ) : (
                                    <div className="text-xs text-gray-500 text-center">
                                        Nenhum alerta ativo.
                                    </div>
                                )}

                                <div className="mt-1 text-[11px] text-gray-400 text-center">
                                    {resetLabel}
                                    {zone.lastreset && (
                                        <>
                                            {" · "}
                                            Último:{" "}
                                            {new Date(zone.lastreset).toLocaleString("pt-BR")}
                                        </>
                                    )}
                                </div>
                            </div>
                        </div>
                    </td>
                );
            }

            case ZoneMode.ALERT: {
                return (
                    <>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                            <div className="text-center">
                                <div className="text-2xl font-bold text-red-600">
                                    {zone.currentcount}
                                </div>
                                <div className="text-xs text-gray-500">em alerta</div>
                            </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                            <div className="text-center">
                                <div className="text-sm font-medium text-red-600">
                                    {formatTime(zone.timefull)}
                                </div>
                                <div className="text-xs text-gray-500">tempo em alerta</div>
                            </div>
                        </td>
                    </>
                );
            }

            case ZoneMode.TRACKING: {
                return (
                    <td className="px-6 py-4 whitespace-nowrap text-center" colSpan={3}>
                        <div className="text-center">
                            <div className="text-lg font-semibold text-purple-600">
                                {zone.currentcount}
                            </div>
                            <div className="text-xs text-gray-500">
                                {zone.currentcount === 1
                                    ? "objeto rastreado"
                                    : "objetos rastreados"}
                            </div>
                        </div>
                    </td>
                );
            }

            case ZoneMode.QUEUE: {
                // Implementação simples – pode ser expandida depois
                return (
                    <td className="px-6 py-4 whitespace-nowrap text-center" colSpan={3}>
                        <div className="text-center">
                            <div className="text-2xl font-bold text-gray-900">
                                {zone.currentcount}
                            </div>
                            <div className="text-xs text-gray-500">
                                pessoas na fila (implementação básica)
                            </div>
                        </div>
                    </td>
                );
            }

            default:
                return (
                    <>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                            {zone.currentcount}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                            {formatTime(zone.timeempty)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                            {formatTime(zone.timefull)}
                        </td>
                    </>
                );
        }
    };

    // ============================================
    // RENDER
    // ============================================

    const totalObjects = filteredZones.reduce(
        (sum, zone) => sum + zone.currentcount,
        0
    );

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            {/* Filtro de câmera */}
            <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 flex-1">
                        <CameraIcon className="w-5 h-5 text-gray-600 flex-shrink-0" />
                        <select
                            value={selectedCameraId}
                            onChange={(e) =>
                                setSelectedCameraId(
                                    e.target.value === "all"
                                        ? "all"
                                        : Number(e.target.value)
                                )
                            }
                            className="flex-1 max-w-xs px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white font-medium text-gray-700"
                        >
                            <option value="all">Todas as zonas</option>
                            {cameras.map((camera: Camera) => (
                                <option key={camera.id} value={camera.id}>
                                    {camera.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span>
                            <span className="font-semibold text-gray-900">
                                {filteredZones.length}
                            </span>{" "}
                            zonas
                        </span>
                        <span className="text-gray-400">|</span>
                        <span>
                            <span className="font-semibold text-gray-900">
                                {Object.keys(groupedByMode).length}
                            </span>{" "}
                            modos
                        </span>
                    </div>
                </div>
            </div>

            {/* Empty state */}
            {filteredZones.length === 0 ? (
                <div className="p-12 text-center">
                    <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500 font-medium mb-2">
                        {selectedCameraId === "all"
                            ? "Nenhuma zona definida."
                            : "Nenhuma zona para esta câmera."}
                    </p>
                    <p className="text-sm text-gray-400">
                        {selectedCameraId === "all"
                            ? "Configure zonas para começar o monitoramento."
                            : "Selecione outra câmera ou configure zonas para esta."}
                    </p>
                </div>
            ) : (
                <div className="p-4 space-y-4">
                    {Object.entries(groupedByMode).map(([modeKey, zonesInMode]) => {
                        const mode = modeKey as ZoneMode;
                        const Icon = modeIcons[mode] ?? AlertCircle;
                        const modeColor = `#${ZONE_MODE_COLORS[mode] ?? "6B7280"}`;
                        const isExpanded = expandedModes.has(mode);

                        const hasAlert = zonesInMode.some(
                            (z) => z.state === "alert" || z.state === "critical"
                        );

                        return (
                            <div
                                key={modeKey}
                                className={`overflow-hidden rounded-lg border-2 shadow-sm hover:shadow-md transition-shadow ${hasAlert ? "alert-pulse border-red-300" : "border-gray-200"
                                    }`}
                                style={{
                                    borderLeftWidth: 4,
                                    borderLeftColor: modeColor,
                                }}
                            >
                                {/* Header do grupo */}
                                <button
                                    type="button"
                                    onClick={() => toggleModeExpansion(mode)}
                                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                                    style={{
                                        backgroundColor: isExpanded ? `${modeColor}08` : "transparent",
                                    }}
                                >
                                    <div className="flex items-center gap-3">
                                        <div
                                            className="w-10 h-10 rounded-lg flex items-center justify-center shadow-sm"
                                            style={{ backgroundColor: `${modeColor}26` }}
                                        >
                                            <Icon
                                                className="w-5 h-5"
                                                style={{ color: modeColor }}
                                            />
                                        </div>
                                        <div className="text-left">
                                            <h3 className="text-lg font-bold text-gray-900">
                                                {ZONE_MODE_LABELS[mode]}
                                            </h3>
                                            <p className="text-sm text-gray-600">
                                                {zonesInMode.length}{" "}
                                                {zonesInMode.length === 1 ? "zona" : "zonas"}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3">
                                        {hasAlert && (
                                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold bg-red-50 text-red-600 border border-red-200">
                                                <AlertCircle className="w-3 h-3" />
                                                <span>Alerta ativo</span>
                                            </span>
                                        )}
                                        {isExpanded ? (
                                            <ChevronUp className="w-5 h-5 text-gray-400" />
                                        ) : (
                                            <ChevronDown className="w-5 h-5 text-gray-400" />
                                        )}
                                    </div>
                                </button>

                                {/* Tabela do grupo */}
                                {isExpanded && (
                                    <div className="border-t-2 border-gray-200">
                                        <div className="overflow-x-auto">
                                            <table className="w-full">
                                                <thead className="bg-gray-50">
                                                    <tr>
                                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                                                            Zona
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                                                            Modo
                                                        </th>
                                                        {renderHeadersForMode(mode)}
                                                        <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                                                            Estado
                                                        </th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-gray-200 bg-white">
                                                    {zonesInMode.map((zone) => {
                                                        const ZoneIcon = modeIcons[zone.mode] ?? AlertCircle;

                                                        return (
                                                            <tr
                                                                key={zone.zoneid}
                                                                className={`hover:bg-gray-50 transition-colors ${zone.state === "alert" ||
                                                                        zone.state === "critical"
                                                                        ? "alert-pulse"
                                                                        : ""
                                                                    }`}
                                                            >
                                                                {/* Zona */}
                                                                <td className="px-6 py-4 whitespace-nowrap">
                                                                    <div className="flex items-center gap-3">
                                                                        <div
                                                                            className="w-3 h-3 rounded-full flex-shrink-0 border-2 border-white shadow-sm"
                                                                            style={{ backgroundColor: modeColor }}
                                                                        />
                                                                        <div>
                                                                            <span className="font-medium text-gray-900">
                                                                                {zone.zonename}
                                                                            </span>
                                                                        </div>
                                                                    </div>
                                                                </td>

                                                                {/* Modo */}
                                                                <td className="px-6 py-4 whitespace-nowrap">
                                                                    <div
                                                                        className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border ${getModeColorClasses(
                                                                            zone.mode
                                                                        )}`}
                                                                    >
                                                                        <ZoneIcon className="w-4 h-4" />
                                                                        <span className="text-sm font-medium">
                                                                            {ZONE_MODE_LABELS[zone.mode]}
                                                                        </span>
                                                                    </div>
                                                                </td>

                                                                {/* Métricas */}
                                                                {renderMetricsCell(zone)}

                                                                {/* Estado */}
                                                                <td className="px-6 py-4 whitespace-nowrap text-center">
                                                                    <span
                                                                        className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${stateColors[zone.state]
                                                                            } ${zone.state === "alert" ||
                                                                                zone.state === "critical"
                                                                                ? "animate-pulse"
                                                                                : ""
                                                                            }`}
                                                                    >
                                                                        {getStateLabel(zone)}
                                                                    </span>
                                                                </td>
                                                            </tr>
                                                        );
                                                    })}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Footer summary */}
            {filteredZones.length > 0 && (
                <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
                    <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-6">
                            <div>
                                <span className="text-gray-600">Total de zonas</span>
                                <span className="font-semibold text-gray-900 ml-2">
                                    {filteredZones.length}
                                </span>
                            </div>
                            <div>
                                <span className="text-gray-600">Objetos detectados</span>
                                <span className="font-semibold text-gray-900 ml-2">
                                    {totalObjects}
                                </span>
                            </div>
                            {selectedCameraId !== "all" && (
                                <div>
                                    <span className="text-gray-600">Câmera</span>
                                    <span className="font-semibold text-blue-600 ml-2">
                                        {cameras.find(
                                            (c: Camera) => c.id === selectedCameraId
                                        )?.name ?? "N/A"}
                                    </span>
                                </div>
                            )}
                        </div>

                        <div className="flex items-center gap-2 text-xs text-gray-500">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                            <RefreshCw className="w-3.5 h-3.5 animate-spin text-green-600" />
                            <span>Atualização em tempo real</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ZoneTable;
