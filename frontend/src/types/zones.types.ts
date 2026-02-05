/**
 * ============================================================================
 * zones.types.ts - Zone Types v3.1 (Backend Aligned + Queue Mode)
 * ============================================================================
 * 100% compatível com backend/models/zones.py v3.0
 * Suporta modos: occupancy, counting, alert, tracking, capacity, queue
 * Mantém compatibilidade v2.0: GENERIC, EMPTY, FULL
 * ============================================================================
 */
import type { TrackerType } from './trackers.types';

// ============================================================================
// ENUMS (Alinhados com backend v3.0)
// ============================================================================

/**
 * Modos de operação das zonas v3.x
 * ✅ Alinhado com backend/models/zones.py (+ modo queue)
 */
export enum ZoneMode {
    // ✅ v3.x Modes (lowercase - novos)
    OCCUPANCY = 'occupancy', // Detecção de ocupação (vagas, áreas)
    COUNTING = 'counting',  // Contagem de pessoas/objetos
    ALERT = 'alert',     // Alerta de intrusão
    TRACKING = 'tracking',  // Rastreamento de movimento
    CAPACITY = 'capacity',  // Capacidade / Lotação
    QUEUE = 'queue',     // Fila (comprimento, espera, desistências)

    // 🔙 Backward compatibility v2.0 (uppercase - legado)
    GENERIC = 'GENERIC',
    EMPTY = 'EMPTY',
    FULL = 'FULL',
}

/**
 * Sistema de coordenadas
 */
export enum CoordinateSystem {
    NORMALIZED = 'normalized', // 0-1 range
    ABSOLUTE = 'absolute',   // Pixel coordinates (deprecated)
    AUTO = 'auto',       // Auto-detect
}

/**
* Base opcional para qualquer metadata de zona
 */
export interface BaseZoneMetadata {
    tracker_override?: TrackerType;
    reid_required?: boolean;
}

// ============================================================================
// TYPES BÁSICOS
// ============================================================================

/** Ponto 2D */
export type Point = [number, number];

/** Polígono (array de pontos) */
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

    // Parâmetros (colunas da tabela zones)
    max_out_time?: number;
    camera_id?: number | null;
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

    // Metadata v3.0 (coluna JSONB metadata)
    description?: string;
    color?: string;
    tags?: string[];
    snapshot_path?: string;
    metadata?: BaseZoneMetadata & Record<string, any>;

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
    camera_id?: number | null;

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
    snapshot_base64?: string;
    metadata?: BaseZoneMetadata & Record<string, any>;
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
    errors: Array<{
        index: number;
        message: string;
    }>;
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
    mode: 'create' | 'edit' | 'view';
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
// DEFAULTS & CONSTANTS v3.x
// ============================================================================

/**
 * Valores padrão para nova zona v3.x
 */
export const DEFAULT_ZONE_VALUES: Partial<CreateZonePayload> = {
    mode: ZoneMode.OCCUPANCY,
    coordinate_system: CoordinateSystem.AUTO,
    empty_timeout: 5.0,
    full_timeout: 10.0,
    empty_threshold: 0,
    full_threshold: 3,
    max_out_time: 30.0,
    email_cooldown: 600.0,
    enabled: true,
    active: true,
    color: '#3B82F6',
    tags: [],
    metadata: {},
};

/**
 * Cores por modo v3.x
 * ✅ Suporta todos os modos (novos + legados)
 */
export const ZONE_MODE_COLORS: Record<ZoneMode, string> = {
    // v3.x modes
    [ZoneMode.OCCUPANCY]: '#3B82F6', // blue-500 - Ocupação
    [ZoneMode.COUNTING]: '#10B981', // green-500 - Contagem
    [ZoneMode.ALERT]: '#EF4444', // red-500 - Alerta
    [ZoneMode.TRACKING]: '#8B5CF6', // purple-500 - Rastreamento
    [ZoneMode.CAPACITY]: '#F59E0B', // amber-500 - Lotação
    [ZoneMode.QUEUE]: '#6366F1', // indigo-500 - Fila

    // v2.0 legacy
    [ZoneMode.GENERIC]: '#6B7280', // gray-500 - Genérico
    [ZoneMode.EMPTY]: '#14B8A6', // teal-500 - Alerta Vazio
    [ZoneMode.FULL]: '#F97316', // orange-500 - Alerta Cheio
};

/**
 * Labels dos modos v3.x (PT-BR)
 */
export const ZONE_MODE_LABELS: Record<ZoneMode, string> = {
    // v3.x modes
    [ZoneMode.OCCUPANCY]: 'Ocupação',
    [ZoneMode.COUNTING]: 'Contagem',
    [ZoneMode.ALERT]: 'Alerta',
    [ZoneMode.TRACKING]: 'Rastreamento',
    [ZoneMode.CAPACITY]: 'Capacidade Máxima',
    [ZoneMode.QUEUE]: 'Fila',

    // v2.0 legacy
    [ZoneMode.GENERIC]: 'Genérico',
    [ZoneMode.EMPTY]: 'Área Vazia',
    [ZoneMode.FULL]: 'Áreaa Cheia',
};

/**
 * Descrições dos modos v3.x
 */
export const ZONE_MODE_DESCRIPTIONS: Record<ZoneMode, string> = {
    // v3.x modes
    [ZoneMode.OCCUPANCY]:
        'Detecção de ocupação em vagas de estacionamento ou áreas específicas',
    [ZoneMode.COUNTING]:
        'Contagem de pessoas ou objetos entrando e saindo da zona',
    [ZoneMode.ALERT]:
        'Alertas de intrusão em áreas restritas ou proibidas',
    [ZoneMode.TRACKING]:
        'Rastreamento de movimento e trajetórias de objetos',
    [ZoneMode.CAPACITY]:
        'Controle de capacidade máxima (eventos, elevadores, lojas, etc.)',
    [ZoneMode.QUEUE]:
        'Gerenciamento de filas: tamanho, tempo de espera e desistências',

    // v2.0 legacy
    [ZoneMode.GENERIC]:
        'Monitoramento geral de ocupação (modo legado)',
    [ZoneMode.EMPTY]:
        'Alerta quando zona fica vazia por muito tempo (modo legado)',
    [ZoneMode.FULL]:
        'Alerta quando zona fica cheia por muito tempo (modo legado)',
};

// ============================================================================
// v3.3: HELPER - CAMPOS VISÍVEIS POR MODO
// ============================================================================

/**
 * Configuração de campos utilizados por modo.
 * Define quais campos devem ser zerados quando NÃO são usados pelo modo.
 * Usado para limpar campos ao trocar de modo (ex: capacity → counting).
 */
export const ZONE_MODE_FIELDS: Record<
    string,
    {
        threshold_empty: boolean;
        threshold_full: boolean;
        timeout_empty: boolean;
        timeout_full: boolean;
        email_cooldown: boolean;
        capacity: boolean;
        counting?: boolean;
        queue?: boolean;
    }
> = {
    // v3.x Modes
    occupancy: {
        threshold_empty: true,
        threshold_full: true,
        timeout_empty: true,
        timeout_full: true,
        email_cooldown: true,
        capacity: false,
    },
    counting: {
        threshold_empty: false,
        threshold_full: true,
        timeout_empty: false,
        timeout_full: true,
        email_cooldown: false,
        capacity: false,
        counting: true,
    },
    alert: {
        threshold_empty: false,
        threshold_full: true,
        timeout_empty: false,
        timeout_full: true,
        email_cooldown: true,
        capacity: false,
    },
    tracking: {
        threshold_empty: false,
        threshold_full: false,
        timeout_empty: false,
        timeout_full: false,
        email_cooldown: false,
        capacity: false,
    },
    capacity: {
        threshold_empty: false,
        threshold_full: false,
        timeout_empty: false,
        timeout_full: true,
        email_cooldown: true,
        capacity: true,
    },
    queue: {
        threshold_empty: false,
        threshold_full: false,
        timeout_empty: false,
        timeout_full: false,
        // usamos email_cooldown global para cooldown de alertas de fila
        email_cooldown: true,
        capacity: false,
        queue: true,
    },

    // v2.0 Legacy
    GENERIC: {
        threshold_empty: true,
        threshold_full: true,
        timeout_empty: true,
        timeout_full: true,
        email_cooldown: true,
        capacity: false,
    },
    EMPTY: {
        threshold_empty: true,
        threshold_full: false,
        timeout_empty: true,
        timeout_full: false,
        email_cooldown: true,
        capacity: false,
    },
    FULL: {
        threshold_empty: false,
        threshold_full: true,
        timeout_empty: false,
        timeout_full: true,
        email_cooldown: true,
        capacity: false,
    },
};

// ============================================================================
// v3.9: Counting / Capacity / Queue - Types & Defaults
// ============================================================================

/** Direção de contagem */
export type CountDirection = 'in' | 'out' | 'both';

/** Período de reset automático */
export type ResetInterval = 'none' | 'hourly' | 'daily' | 'weekly' | 'monthly';

/** Metadata para modo COUNTING */
export interface CountingMetadata extends BaseZoneMetadata {
    count_direction: CountDirection;
    count_in?: number;
    count_out?: number;
    reset_interval: ResetInterval;
    last_reset?: string;
    alert_enabled?: boolean;
    alert_threshold?: number;
    intersection_threshold?: number;
    confirmation_time?: number;
}

/** Metadata para modo CAPACITY */
export interface CapacityMetadata extends BaseZoneMetadata {
    max_capacity: number;
    alert_percentage: number;
}

/**
 * Configuração de KPIs para modo QUEUE (fila)
 * Controla o que será exibido no dashboard/ZoneTable.
 */
export interface QueueKpiConfig {
    show_queue_length: boolean;
    show_avg_wait_time: boolean;
    show_max_wait_time: boolean;
    show_abandon_rate: boolean;
    show_throughput: boolean;
}

/**
 * Metadata para modo QUEUE (fila)
 * Usará a coluna JSONB metadata da tabela zones.
 */
export interface QueueMetadata extends BaseZoneMetadata {
    // Limites de comprimento da fila
    max_queue_length: number;      // capacidade "máxima desejável"
    warning_queue_length: number;  // ponto de aviso
    critical_queue_length: number; // ponto crítico

    // SLA de espera (segundos)
    max_wait_warning: number;   // média ou p95 para WARNING
    max_wait_critical: number;  // max/p95 para CRITICAL

    // Histerese de entrada/saída(segundos)
    queue_join_confirm_time ?: number;  // tempo mínimo dentro da zona p/ confirmar entrada
    queue_leave_grace_time ?: number;   // tempo fora da zona p/ considerar saída definitiva

    // Opcional: cooldown específico para alertas de fila
    email_cooldown_seconds?: number;

    // KPIs visíveis no dashboard para esta zona
    kpis?: QueueKpiConfig;
}

/**
 * Labels das direções (PT-BR)
 */
export const COUNT_DIRECTION_LABELS: Record<CountDirection, string> = {
    in: '🔽 Apenas Entradas',
    out: '🔼 Apenas Saídas',
    both: '↕️ Ambas Direções',
} as const;

/**
 * Descrições das direções
 */
export const COUNT_DIRECTION_DESCRIPTIONS: Record<CountDirection, string> = {
    in: 'Conta apenas objetos entrando na zona',
    out: 'Conta apenas objetos saindo da zona',
    both: 'Conta entradas e saídas separadamente',
} as const;

/**
 * Labels dos períodos de reset (PT-BR)
 */
export const RESET_INTERVAL_LABELS: Record<ResetInterval, string> = {
    none: 'Nunca (acumula sempre)',
    hourly: 'A cada 1 hora',
    daily: 'Diariamente às 00:00',
    weekly: 'Semanalmente (Segunda 00:00)',
    monthly: 'Mensalmente (dia 1 às 00:00)',
} as const;

/**
 * Metadata padrão por modo
 * (usado no Drawer para inicializar metadata a partir do modo)
 */
export const MODE_METADATA_DEFAULTS: Record<string, any> = {
    // Sem metadata específica
    occupancy: {},
    alert: {},
    tracking: {},
    GENERIC: {},
    EMPTY: {},
    FULL: {},

    // Capacity
    capacity: {
        max_capacity: 50,
        alert_percentage: 90,
    } as CapacityMetadata,

    // Counting
    counting: {
        count_direction: 'both',
        count_in: 0,
        count_out: 0,
        reset_interval: 'daily',
        alert_enabled: false,
        alert_threshold: 100,
        intersection_threshold: 0.7,
        confirmation_time: 0,
    } as CountingMetadata,

    // Queue
    queue: {
        max_queue_length: 10,
        warning_queue_length: 7,
        critical_queue_length: 10,
        max_wait_warning: 120,  // 2 minutos
        max_wait_critical: 300, // 5 minutos,
        queue_join_confirm_time: 5, // 1 segundo dentro da ROI para confirmar entrada na fila
        queue_leave_grace_time: 7, // 2 segundos fora da ROI para considerar saída definitiva
        kpis: {
            show_queue_length: true,
            show_avg_wait_time: true,
            show_max_wait_time: false,
            show_abandon_rate: true,
            show_throughput: false,
        } as QueueKpiConfig,
    } as QueueMetadata,
} as const;

/**
 * Ícones dos modos (string names para lucide-react)
 * Usado para importação dinâmica de ícones
 */
export const ZONE_MODE_ICONS: Record<ZoneMode, string> = {
    // v3.x modes
    [ZoneMode.OCCUPANCY]: 'Users',
    [ZoneMode.COUNTING]: 'TrendingUp',
    [ZoneMode.ALERT]: 'ShieldAlert',
    [ZoneMode.TRACKING]: 'Eye',
    [ZoneMode.CAPACITY]: 'UserPlus',
    [ZoneMode.QUEUE]: 'Users',

    // v2.0 legacy
    [ZoneMode.GENERIC]: 'AlertCircle',
    [ZoneMode.EMPTY]: 'Circle',
    [ZoneMode.FULL]: 'CircleDot',
};

/**
 * Classes Tailwind por modo
 * Para badges e elementos coloridos
 */
export const ZONE_MODE_TAILWIND_CLASSES: Record<ZoneMode, string> = {
    // v3.x modes
    [ZoneMode.OCCUPANCY]:
        'text-blue-600 bg-blue-50 border-blue-200',
    [ZoneMode.COUNTING]:
        'text-green-600 bg-green-50 border-green-200',
    [ZoneMode.ALERT]:
        'text-red-600 bg-red-50 border-red-200',
    [ZoneMode.TRACKING]:
        'text-purple-600 bg-purple-50 border-purple-200',
    [ZoneMode.CAPACITY]:
        'text-amber-600 bg-amber-50 border-amber-200',
    [ZoneMode.QUEUE]:
        'text-indigo-600 bg-indigo-50 border-indigo-200',

    // v2.0 legacy
    [ZoneMode.GENERIC]:
        'text-gray-600 bg-gray-50 border-gray-200',
    [ZoneMode.EMPTY]:
        'text-teal-600 bg-teal-50 border-teal-200',
    [ZoneMode.FULL]:
        'text-orange-600 bg-orange-50 border-orange-200',
};

/**
 * Configuração visual padrão do canvas
 */
export const DEFAULT_CANVAS_CONFIG: CanvasVisualConfig = {
    strokeColor: '#3B82F6',
    fillColor: '#3B82F6',
    pointColor: '#1E40AF',
    hoveredPointColor: '#F59E0B',
    selectedPointColor: '#EF4444',
    strokeWidth: 2,
    pointRadius: 6,
    hoveredPointRadius: 8,
    fillOpacity: 0.2,
};

// ============================================================================
// HELPER TYPES
// ============================================================================

/**
 * Estado de loading/erro para operações async
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
// UTILITY FUNCTIONS v3.x
// ============================================================================

/**
 * Verifica se o modo é v3.x (lowercase)
 */
export const isV3Mode = (mode: ZoneMode): boolean => {
    return [
        ZoneMode.OCCUPANCY,
        ZoneMode.COUNTING,
        ZoneMode.ALERT,
        ZoneMode.TRACKING,
        ZoneMode.CAPACITY,
        ZoneMode.QUEUE,
    ].includes(mode);
};

/**
 * Verifica se o modo é v2.0 legacy (uppercase)
 */
export const isLegacyMode = (mode: ZoneMode): boolean => {
    return [
        ZoneMode.GENERIC,
        ZoneMode.EMPTY,
        ZoneMode.FULL,
    ].includes(mode);
};

/**
 * Converte modo v2.0 para v3.x equivalente
 */
export const convertLegacyMode = (legacyMode: ZoneMode): ZoneMode => {
    const conversionMap: Record<ZoneMode, ZoneMode> = {
        [ZoneMode.GENERIC]: ZoneMode.OCCUPANCY,
        [ZoneMode.EMPTY]: ZoneMode.ALERT,
        [ZoneMode.FULL]: ZoneMode.ALERT,

        // identidade para modos já v3.x
        [ZoneMode.OCCUPANCY]: ZoneMode.OCCUPANCY,
        [ZoneMode.COUNTING]: ZoneMode.COUNTING,
        [ZoneMode.ALERT]: ZoneMode.ALERT,
        [ZoneMode.TRACKING]: ZoneMode.TRACKING,
        [ZoneMode.CAPACITY]: ZoneMode.CAPACITY,
        [ZoneMode.QUEUE]: ZoneMode.QUEUE,
    };

    return conversionMap[legacyMode] || legacyMode;
};

/**
 * Lista todos os modos disponíveis para seleção
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
        // v3.x modes (recomendados)
        {
            value: ZoneMode.OCCUPANCY,
            label: ZONE_MODE_LABELS[ZoneMode.OCCUPANCY],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.OCCUPANCY],
            color: ZONE_MODE_COLORS[ZoneMode.OCCUPANCY],
            icon: ZONE_MODE_ICONS[ZoneMode.OCCUPANCY],
            version: 'v3.0',
        },
        {
            value: ZoneMode.COUNTING,
            label: ZONE_MODE_LABELS[ZoneMode.COUNTING],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.COUNTING],
            color: ZONE_MODE_COLORS[ZoneMode.COUNTING],
            icon: ZONE_MODE_ICONS[ZoneMode.COUNTING],
            version: 'v3.0',
        },
        {
            value: ZoneMode.ALERT,
            label: ZONE_MODE_LABELS[ZoneMode.ALERT],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.ALERT],
            color: ZONE_MODE_COLORS[ZoneMode.ALERT],
            icon: ZONE_MODE_ICONS[ZoneMode.ALERT],
            version: 'v3.0',
        },
        {
            value: ZoneMode.TRACKING,
            label: ZONE_MODE_LABELS[ZoneMode.TRACKING],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.TRACKING],
            color: ZONE_MODE_COLORS[ZoneMode.TRACKING],
            icon: ZONE_MODE_ICONS[ZoneMode.TRACKING],
            version: 'v3.0',
        },
        {
            value: ZoneMode.CAPACITY,
            label: ZONE_MODE_LABELS[ZoneMode.CAPACITY],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.CAPACITY],
            color: ZONE_MODE_COLORS[ZoneMode.CAPACITY],
            icon: ZONE_MODE_ICONS[ZoneMode.CAPACITY],
            version: 'v3.0',
        },
        {
            value: ZoneMode.QUEUE,
            label: ZONE_MODE_LABELS[ZoneMode.QUEUE],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.QUEUE],
            color: ZONE_MODE_COLORS[ZoneMode.QUEUE],
            icon: ZONE_MODE_ICONS[ZoneMode.QUEUE],
            version: 'v3.0',
        },

        // v2.0 legacy (para compatibilidade)
        {
            value: ZoneMode.GENERIC,
            label: ZONE_MODE_LABELS[ZoneMode.GENERIC],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.GENERIC],
            color: ZONE_MODE_COLORS[ZoneMode.GENERIC],
            icon: ZONE_MODE_ICONS[ZoneMode.GENERIC],
            version: 'v2.0 (legacy)',
        },
        {
            value: ZoneMode.EMPTY,
            label: ZONE_MODE_LABELS[ZoneMode.EMPTY],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.EMPTY],
            color: ZONE_MODE_COLORS[ZoneMode.EMPTY],
            icon: ZONE_MODE_ICONS[ZoneMode.EMPTY],
            version: 'v2.0 (legacy)',
        },
        {
            value: ZoneMode.FULL,
            label: ZONE_MODE_LABELS[ZoneMode.FULL],
            description: ZONE_MODE_DESCRIPTIONS[ZoneMode.FULL],
            color: ZONE_MODE_COLORS[ZoneMode.FULL],
            icon: ZONE_MODE_ICONS[ZoneMode.FULL],
            version: 'v2.0 (legacy)',
        },
    ];
};
