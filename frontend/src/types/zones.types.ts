/**
 * ============================================================================
 * zones.types.ts - Zone Types v3.0 (Backend Aligned)
 * ============================================================================
 * 100% compatível com backend/models/zones.py v3.0
 * Suporta novos modos: occupancy, counting, alert, tracking
 * Mantém compatibilidade v2.0: GENERIC, EMPTY, FULL
 * ============================================================================
 */

// ============================================================================
// ENUMS (Alinhados com backend v3.0)
// ============================================================================

/**
 * Modos de operação das zonas v3.0
 * ✅ Alinhado 100% com backend/models/zones.py
 */
export enum ZoneMode {
    // ✅ v3.0 Modes (lowercase - novos)
    OCCUPANCY = "occupancy",      // Detecção de ocupação (vagas, áreas)
    COUNTING = "counting",        // Contagem de pessoas/objetos
    ALERT = "alert",             // Alerta de intrusão
    TRACKING = "tracking",       // Rastreamento de movimento

    // 🔙 Backward compatibility v2.0 (uppercase - legado)
    GENERIC = "GENERIC",
    EMPTY = "EMPTY",
    FULL = "FULL"
}

/**
 * Sistema de coordenadas
 */
export enum CoordinateSystem {
    NORMALIZED = "normalized",  // 0-1 range
    ABSOLUTE = "absolute",       // Pixel coordinates (deprecated)
    AUTO = "auto"               // Auto-detect
}

// ============================================================================
// TYPES
// ============================================================================

/**
 * Ponto 2D
 */
export type Point = [number, number];

/**
 * Polígono (array de pontos)
 */
export type Polygon = Point[];

// ============================================================================
// ZONE INTERFACES (Do Backend)
// ============================================================================

/**
 * Zona completa (ZoneResponse do backend)
 */
export interface Zone {
    // Identificação
    id: number;
    name: string;

    // Geometria
    points: Polygon;
    mode: ZoneMode;

    // Parâmetros
    max_out_time?: number;
    email_cooldown?: number;
    empty_timeout: number;
    full_timeout: number;
    empty_threshold: number;
    full_threshold: number;

    // Sistema de coordenadas
    coordinate_system: CoordinateSystem;

    // Status
    enabled: boolean;
    active: boolean;

    // Metadata v3.0
    description?: string;
    color?: string;
    tags?: string[];

    // Timestamps
    created_at: string;
    updated_at: string;
    deleted_at?: string | null;
}

/**
 * Payload para criar zona (ZoneCreate do backend)
 */
export interface CreateZonePayload {
    name: string;
    points: Polygon;
    mode: ZoneMode;

    // Opcionais com defaults
    max_out_time?: number;
    email_cooldown?: number;
    empty_timeout?: number;
    full_timeout?: number;
    empty_threshold?: number;
    full_threshold?: number;

    // Sistema de coordenadas
    coordinate_system?: CoordinateSystem;

    // Status
    enabled?: boolean;
    active?: boolean;

    // Metadata
    description?: string;
    color?: string;
    tags?: string[];
}

/**
 * Payload para atualizar zona (ZoneUpdate do backend)
 */
export interface UpdateZonePayload extends Partial<CreateZonePayload> { }

/**
 * Resposta de validação de polígono
 */
export interface PolygonValidation {
    valid: boolean;
    area?: number;
    perimeter?: number;
    centroid?: Point;
    issues: string[];
}

/**
 * Estatísticas de zonas
 */
export interface ZoneStatistics {
    total_zones: number;
    enabled_zones: number;
    disabled_zones: number;
    active_zones: number;
    zones_by_mode: Record<string, number>;
    average_area?: number;
    total_detections?: number;
    most_active_zones: Array<{
        id: number;
        name: string;
        detections: number;
    }>;
    timestamp: string;
}

/**
 * Clone de zona
 */
export interface CloneZonePayload {
    new_name: string;
    offset_x?: number;
    offset_y?: number;
}

/**
 * Bulk create
 */
export interface BulkCreatePayload {
    zones: CreateZonePayload[];
}

export interface BulkCreateResponse {
    created: number;
    failed: number;
    errors: Array<Record<string, string>>;
    zones: Zone[];
}

/**
 * Bulk delete
 */
export interface BulkDeletePayload {
    zone_ids: number[];
}

// ============================================================================
// UI STATE TYPES
// ============================================================================

/**
 * Estado do drawer/modal
 */
export interface ZoneDrawerState {
    isOpen: boolean;
    mode: "create" | "edit" | "view";
    zone: Zone | null;
    isDirty: boolean;
}

/**
 * Estado do canvas de desenho
 */
export interface CanvasState {
    points: Polygon;
    isDrawing: boolean;
    hoveredPointIndex: number | null;
    selectedPointIndex: number | null;
    isDragging: boolean;
    canvasSize: { width: number; height: number };
}

/**
 * Configuração visual do canvas
 */
export interface CanvasVisualConfig {
    // Cores
    strokeColor: string;
    fillColor: string;
    pointColor: string;
    hoveredPointColor: string;
    selectedPointColor: string;

    // Tamanhos
    strokeWidth: number;
    pointRadius: number;
    hoveredPointRadius: number;

    // Opacidade
    fillOpacity: number;
}

// ============================================================================
// DEFAULTS & CONSTANTS v3.0
// ============================================================================

/**
 * Valores padrão para nova zona v3.0
 */
export const DEFAULT_ZONE_VALUES: Partial<CreateZonePayload> = {
    mode: ZoneMode.OCCUPANCY,  // ✅ Mudado de GENERIC para OCCUPANCY
    coordinate_system: CoordinateSystem.AUTO,  // ✅ Mudado de NORMALIZED para AUTO
    empty_timeout: 5.0,
    full_timeout: 10.0,
    empty_threshold: 0,
    full_threshold: 3,
    max_out_time: 30.0,
    email_cooldown: 600.0,
    enabled: true,
    active: true,
    color: "#3B82F6",
    tags: []
};

/**
 * Cores por modo v3.0
 * ✅ Suporta todos os 7 modos (4 novos + 3 legados)
 */
export const ZONE_MODE_COLORS: Record<ZoneMode, string> = {
    // ✅ v3.0 modes (novos)
    [ZoneMode.OCCUPANCY]: "#3B82F6",   // blue-500 - Ocupação
    [ZoneMode.COUNTING]: "#10B981",    // green-500 - Contagem
    [ZoneMode.ALERT]: "#EF4444",       // red-500 - Alerta
    [ZoneMode.TRACKING]: "#8B5CF6",    // purple-500 - Rastreamento

    // 🔙 v2.0 legacy (antigos)
    [ZoneMode.GENERIC]: "#6B7280",     // gray-500 - Genérico
    [ZoneMode.EMPTY]: "#14B8A6",       // teal-500 - Alerta Vazio
    [ZoneMode.FULL]: "#F97316"         // orange-500 - Alerta Cheio
};

/**
 * Labels dos modos v3.0 (PT-BR)
 * ✅ Todos os 7 modos traduzidos
 */
export const ZONE_MODE_LABELS: Record<ZoneMode, string> = {
    // v3.0 modes
    [ZoneMode.OCCUPANCY]: "Ocupação",
    [ZoneMode.COUNTING]: "Contagem",
    [ZoneMode.ALERT]: "Alerta",
    [ZoneMode.TRACKING]: "Rastreamento",

    // v2.0 legacy
    [ZoneMode.GENERIC]: "Genérico",
    [ZoneMode.EMPTY]: "Alerta Vazio",
    [ZoneMode.FULL]: "Alerta Cheio"
};

/**
 * Descrições dos modos v3.0
 * ✅ Explicações detalhadas
 */
export const ZONE_MODE_DESCRIPTIONS: Record<ZoneMode, string> = {
    // v3.0 modes
    [ZoneMode.OCCUPANCY]: "Detecção de ocupação em vagas de estacionamento ou áreas específicas",
    [ZoneMode.COUNTING]: "Contagem de pessoas ou objetos entrando e saindo da zona",
    [ZoneMode.ALERT]: "Alertas de intrusão em áreas restritas ou proibidas",
    [ZoneMode.TRACKING]: "Rastreamento de movimento e trajetórias de objetos",

    // v2.0 legacy
    [ZoneMode.GENERIC]: "Monitoramento geral de ocupação (modo legado)",
    [ZoneMode.EMPTY]: "Alerta quando zona fica vazia por muito tempo (modo legado)",
    [ZoneMode.FULL]: "Alerta quando zona fica cheia por muito tempo (modo legado)"
};

/**
 * ✅ NOVO v3.0: Ícones dos modos (string names para lucide-react)
 * Usado para importação dinâmica de ícones
 */
export const ZONE_MODE_ICONS: Record<ZoneMode, string> = {
    // v3.0 modes
    [ZoneMode.OCCUPANCY]: "Users",
    [ZoneMode.COUNTING]: "TrendingUp",
    [ZoneMode.ALERT]: "ShieldAlert",
    [ZoneMode.TRACKING]: "Eye",

    // v2.0 legacy
    [ZoneMode.GENERIC]: "AlertCircle",
    [ZoneMode.EMPTY]: "Circle",
    [ZoneMode.FULL]: "CircleDot"
};

/**
 * ✅ NOVO v3.0: Classes Tailwind por modo
 * Para badges e elementos coloridos
 */
export const ZONE_MODE_TAILWIND_CLASSES: Record<ZoneMode, string> = {
    // v3.0 modes
    [ZoneMode.OCCUPANCY]: "text-blue-600 bg-blue-50 border-blue-200",
    [ZoneMode.COUNTING]: "text-green-600 bg-green-50 border-green-200",
    [ZoneMode.ALERT]: "text-red-600 bg-red-50 border-red-200",
    [ZoneMode.TRACKING]: "text-purple-600 bg-purple-50 border-purple-200",

    // v2.0 legacy
    [ZoneMode.GENERIC]: "text-gray-600 bg-gray-50 border-gray-200",
    [ZoneMode.EMPTY]: "text-teal-600 bg-teal-50 border-teal-200",
    [ZoneMode.FULL]: "text-orange-600 bg-orange-50 border-orange-200"
};

/**
 * Configuração visual padrão do canvas
 */
export const DEFAULT_CANVAS_CONFIG: CanvasVisualConfig = {
    strokeColor: "#3B82F6",
    fillColor: "#3B82F6",
    pointColor: "#1E40AF",
    hoveredPointColor: "#F59E0B",
    selectedPointColor: "#EF4444",
    strokeWidth: 2,
    pointRadius: 6,
    hoveredPointRadius: 8,
    fillOpacity: 0.2
};

// ============================================================================
// HELPER TYPES
// ============================================================================

/**
 * Estado de loading/erro para operações
 */
export interface AsyncState<T> {
    data: T | null;
    loading: boolean;
    error: string | null;
}

/**
 * Resultado de operação com toast
 */
export interface OperationResult {
    success: boolean;
    message: string;
    data?: any;
}

// ============================================================================
// UTILITY FUNCTIONS v3.0
// ============================================================================

/**
 * ✅ NOVO: Verifica se o modo é v3.0 (lowercase)
 */
export const isV3Mode = (mode: ZoneMode): boolean => {
    return [
        ZoneMode.OCCUPANCY,
        ZoneMode.COUNTING,
        ZoneMode.ALERT,
        ZoneMode.TRACKING
    ].includes(mode);
};

/**
 * ✅ NOVO: Verifica se o modo é v2.0 legacy (uppercase)
 */
export const isLegacyMode = (mode: ZoneMode): boolean => {
    return [
        ZoneMode.GENERIC,
        ZoneMode.EMPTY,
        ZoneMode.FULL
    ].includes(mode);
};

/**
 * ✅ NOVO: Converte modo v2.0 para v3.0 equivalente
 */
export const convertLegacyMode = (legacyMode: ZoneMode): ZoneMode => {
    const conversionMap: Record<string, ZoneMode> = {
        [ZoneMode.GENERIC]: ZoneMode.OCCUPANCY,
        [ZoneMode.EMPTY]: ZoneMode.ALERT,
        [ZoneMode.FULL]: ZoneMode.ALERT
    };

    return conversionMap[legacyMode] || legacyMode;
};

/**
 * ✅ NOVO: Lista todos os modos disponíveis para seleção
 */
export const getAvailableZoneModes = (): Array<{
    value: ZoneMode;
    label: string;
    description: string;
    color: string;
    icon: string;
    version: 'v3.0' | 'v2.0 (legacy)';
}> => {
    return [
        // v3.0 modes (recomendados)
        {
            value: ZoneMode.OCCUPANCY,
            label: ZONE_MODE_LABELS[ZoneMode.OCCUPANCY],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.OCCUPANCY],
            color: ZONE_MODE_COLORS[ZoneMode.OCCUPANCY],
            icon: ZONE_MODE_ICONS[ZoneMode.OCCUPANCY],
            version: 'v3.0'
        },
        {
            value: ZoneMode.COUNTING,
            label: ZONE_MODE_LABELS[ZoneMode.COUNTING],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.COUNTING],
            color: ZONE_MODE_COLORS[ZoneMode.COUNTING],
            icon: ZONE_MODE_ICONS[ZoneMode.COUNTING],
            version: 'v3.0'
        },
        {
            value: ZoneMode.ALERT,
            label: ZONE_MODE_LABELS[ZoneMode.ALERT],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.ALERT],
            color: ZONE_MODE_COLORS[ZoneMode.ALERT],
            icon: ZONE_MODE_ICONS[ZoneMode.ALERT],
            version: 'v3.0'
        },
        {
            value: ZoneMode.TRACKING,
            label: ZONE_MODE_LABELS[ZoneMode.TRACKING],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.TRACKING],
            color: ZONE_MODE_COLORS[ZoneMode.TRACKING],
            icon: ZONE_MODE_ICONS[ZoneMode.TRACKING],
            version: 'v3.0'
        },
        // v2.0 legacy (para compatibilidade)
        {
            value: ZoneMode.GENERIC,
            label: ZONE_MODE_LABELS[ZoneMode.GENERIC],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.GENERIC],
            color: ZONE_MODE_COLORS[ZoneMode.GENERIC],
            icon: ZONE_MODE_ICONS[ZoneMode.GENERIC],
            version: 'v2.0 (legacy)'
        },
        {
            value: ZoneMode.EMPTY,
            label: ZONE_MODE_LABELS[ZoneMode.EMPTY],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.EMPTY],
            color: ZONE_MODE_COLORS[ZoneMode.EMPTY],
            icon: ZONE_MODE_ICONS[ZoneMode.EMPTY],
            version: 'v2.0 (legacy)'
        },
        {
            value: ZoneMode.FULL,
            label: ZONE_MODE_LABELS[ZoneMode.FULL],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.FULL],
            color: ZONE_MODE_COLORS[ZoneMode.FULL],
            icon: ZONE_MODE_ICONS[ZoneMode.FULL],
            version: 'v2.0 (legacy)'
        }
    ];
};
