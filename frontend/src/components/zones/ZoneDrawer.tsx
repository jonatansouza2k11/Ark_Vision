import {
    useState,
    useRef,
    useEffect,
    useCallback,
    MouseEvent as ReactMouseEvent,
} from 'react';
import {
    X,
    Save,
    Trash2,
    RefreshCw,
    AlertCircle,
    CheckCircle2,
    Camera as CameraIcon,
} from 'lucide-react';

import { useToast } from '../../hooks/useToast';
import useCameras from '../../hooks/useCameras';

import type {
    Zone,
    CreateZonePayload,
    UpdateZonePayload,
    Polygon,
    Point,
    CoordinateSystem,
    CountingMetadata,
    CapacityMetadata,
    QueueMetadata,
    QueueKpiConfig,
} from '../../types/zones.types';
import {
    ZoneMode,
    DEFAULT_ZONE_VALUES,
    ZONE_MODE_COLORS,
    ZONE_MODE_LABELS,
    ZONE_MODE_DESCRIPTIONS,
    ZONE_MODE_FIELDS,
    MODE_METADATA_DEFAULTS,
} from '../../types/zones.types';

import ClassSelector from './ClassSelector';

import {
    TRACKER_OPTIONS,
    type TrackerType,
} from '../../types/trackers.types';

const REID_CAPABLE_TRACKERS: TrackerType[] = [
    'strongsort',
    'fast_strongsort',
];

// ============================================================================
// TYPES
// ============================================================================

interface ZoneDrawerProps {
    isOpen: boolean;
    mode: 'create' | 'edit' | 'view';
    zone?: Zone | null;
    onClose: () => void;
    onSave: (
        data: CreateZonePayload | UpdateZonePayload,
        zoneId?: number
    ) => Promise<void>;
    streamUrl?: string;
    cameraId?: number;
}

interface CanvasPoint {
    x: number;
    y: number;
    isDragging?: boolean;
    isHovered?: boolean;
}

// ============================================================================
// CONSTANTES DE CANVAS
// ============================================================================

const CANVAS_WIDTH = 960;
const CANVAS_HEIGHT = 540;
const POINT_RADIUS = 6;
const HOVER_RADIUS = 8;

// ============================================================================
// COMPONENTE
// ============================================================================

export default function ZoneDrawer({
    isOpen,
    mode,
    zone,
    onClose,
    onSave,
    cameraId,
}: ZoneDrawerProps) {
    const { success, error, warning } = useToast();
    const { cameras, loading: camerasLoading } = useCameras();

    // ------------------------------------------------------------------------
    // STATE DO FORMULÁRIO
    // ------------------------------------------------------------------------

    const [formData, setFormData] = useState<CreateZonePayload>({
        name: '',
        mode: ZoneMode.GENERIC as ZoneMode,
        points: [],
        ...DEFAULT_ZONE_VALUES,
        metadata: {},
    });

    const [canvasPoints, setCanvasPoints] = useState<CanvasPoint[]>([]);
    const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
    const [draggingIndex, setDraggingIndex] = useState<number | null>(null);

    const [isValidPolygon, setIsValidPolygon] = useState(false);
    const [validationMessage, setValidationMessage] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null);
    const [capturingSnapshot, setCapturingSnapshot] = useState(false);
    const [streamActive, setStreamActive] = useState(false);
    const [isLoadingZone, setIsLoadingZone] = useState(false);

    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const imgRef = useRef<HTMLImageElement | null>(null);
    const containerRef = useRef<HTMLDivElement | null>(null);

    // ========================================================================
    // ReID: tracker efetivo e governança
    // ========================================================================

    const camera = cameras.find(c => c.id === formData.camera_id);
    const cameraDefaultTracker =
        (camera as any)?.metadata?.defaulttracker ?? 'yolo_bytetrack';
        
    const overrideTracker =
        (formData.metadata as any)?.trackeroverride as TrackerType | undefined;

    const effectiveTracker: TrackerType =
        overrideTracker
            ? overrideTracker
            : (cameraDefaultTracker as TrackerType);

    const canUseReid = REID_CAPABLE_TRACKERS.includes(effectiveTracker);

    // ========================================================================
    // HELPERS DE CONFIG / METADATA
    // ========================================================================

    const shouldShowField = useCallback(
        (
            field:
                | 'threshold_empty'
                | 'threshold_full'
                | 'timeout_empty'
                | 'timeout_full'
                | 'email_cooldown'
                | 'capacity'
        ): boolean => {
            const config = ZONE_MODE_FIELDS[formData.mode];
            if (!config) return true;
            return config[field];
        },
        [formData.mode]
    );

    const normalizeMetadataForMode = useCallback(
        (modeValue: ZoneMode, prevMetadata: Record<string, any> | undefined) => {
            const base = (prevMetadata || {}) as Record<string, any>;
            const defaults = MODE_METADATA_DEFAULTS[modeValue] || {};
            const merged = { ...defaults, ...base };

            if (modeValue === ZoneMode.CAPACITY) {
                const typed = merged as CapacityMetadata;
                return {
                    ...merged,
                    max_capacity: typed.max_capacity ?? 50,
                    alert_percentage: typed.alert_percentage ?? 90,
                } as CapacityMetadata;
            }

            if (modeValue === ZoneMode.COUNTING) {
                const typed = merged as CountingMetadata;
                return {
                    ...merged,
                    count_direction: typed.count_direction ?? 'both',
                    count_in: typed.count_in ?? 0,
                    count_out: typed.count_out ?? 0,
                    reset_interval: typed.reset_interval ?? 'daily',
                    alert_enabled: typed.alert_enabled ?? false,
                    alert_threshold: typed.alert_threshold ?? 100,
                    intersection_threshold: typed.intersection_threshold ?? 0.7,
                    confirmation_time: typed.confirmation_time ?? 0,
                } as CountingMetadata;
            }

            if (modeValue === ZoneMode.QUEUE) {
                const typed = merged as QueueMetadata;
                const maxQueue = typed.max_queue_length ?? 10;

                const joinConfirm = typed.queue_join_confirm_time ?? 1; // 1s
                const leaveGrace = typed.queue_leave_grace_time ?? 2; // 2s

                return {
                    ...merged,
                    max_queue_length: maxQueue,
                    warning_queue_length:
                        typed.warning_queue_length ?? Math.round(maxQueue * 0.7),
                    critical_queue_length:
                        typed.critical_queue_length ?? maxQueue,
                    max_wait_warning: typed.max_wait_warning ?? 120,
                    max_wait_critical: typed.max_wait_critical ?? 300,
                    queue_join_confirm_time: joinConfirm,
                    queue_leave_grace_time: leaveGrace,
                    kpis: {
                        show_queue_length: typed.kpis?.show_queue_length ?? true,
                        show_avg_wait_time:
                            typed.kpis?.show_avg_wait_time ?? true,
                        show_max_wait_time:
                            typed.kpis?.show_max_wait_time ?? false,
                        show_abandon_rate:
                            typed.kpis?.show_abandon_rate ?? true,
                        show_throughput: typed.kpis?.show_throughput ?? false,
                    } as QueueKpiConfig,
                } as QueueMetadata;
            }

            return merged;
        },
        []
    );

    // ========================================================================
    // EFFECT: CARREGAR ZONA EM MODO EDIT/VIEW
    // ========================================================================

    useEffect(() => {
        if (!isOpen) return;

        if (mode === 'edit' || mode === 'view') {
            if (!zone) return;
            setIsLoadingZone(true);

            const metadata = zone.metadata || {};

            const canvasPts: CanvasPoint[] = (zone.points || []).map(
                ([x, y]) => ({
                    x: x * CANVAS_WIDTH,
                    y: y * CANVAS_HEIGHT,
                })
            );

            setFormData({
                name: zone.name,
                mode: zone.mode,
                points: zone.points,
                camera_id: zone.camera_id ?? undefined,
                empty_timeout: zone.empty_timeout,
                full_timeout: zone.full_timeout,
                empty_threshold: zone.empty_threshold,
                full_threshold: zone.full_threshold,
                max_out_time: zone.max_out_time,
                email_cooldown: zone.email_cooldown,
                coordinate_system: zone.coordinate_system as CoordinateSystem,
                enabled: zone.enabled,
                active: zone.active,
                description: zone.description,
                color: zone.color ?? DEFAULT_ZONE_VALUES.color,
                tags: zone.tags ?? [],
                snapshot_base64: undefined,
                metadata: normalizeMetadataForMode(zone.mode, metadata),
            });

            setCanvasPoints(canvasPts);

            if (zone.snapshot_path) {
                const snapshotPath = zone.snapshot_path;
                const filename = snapshotPath.split('/').pop();
                if (filename) {
                    (async () => {
                        try {
                            const response = await fetch(
                                `http://localhost:8000/api/v1/zones/snapshots/${filename}`,
                                {
                                    headers: {
                                        Authorization: `Bearer ${localStorage.getItem(
                                            'access_token'
                                        )}`,
                                    },
                                }
                            );
                            if (response.ok) {
                                const blob = await response.blob();
                                const url = URL.createObjectURL(blob);
                                setSnapshotUrl(url);
                            }
                        } catch (err) {
                            console.warn('Erro ao carregar snapshot', err);
                        } finally {
                            setIsLoadingZone(false);
                        }
                    })();
                } else {
                    setIsLoadingZone(false);
                }
            } else {
                setSnapshotUrl(null);
                setIsLoadingZone(false);
            }
        } else {
            // modo create
            setIsLoadingZone(false);
            setFormData({
                name: '',
                mode: ZoneMode.GENERIC as ZoneMode,
                points: [],
                ...DEFAULT_ZONE_VALUES,
                metadata: {},
            });
            setCanvasPoints([]);
            setSnapshotUrl(null);
        }
    }, [isOpen, mode, zone, normalizeMetadataForMode]);

    // ========================================================================
    // EFFECT: NORMALIZAR CAMPOS AO MUDAR MODO
    // ========================================================================

    useEffect(() => {
        if (isLoadingZone) return;
        if (!formData.mode) return;

        setFormData(prev => {
            const updated: CreateZonePayload = {
                ...prev,
            };

            const cfg = ZONE_MODE_FIELDS[prev.mode];

            if (cfg) {
                // thresholds
                if (!cfg.threshold_empty) {
                    delete (updated as any).empty_threshold;
                } else if (updated.empty_threshold == null) {
                    updated.empty_threshold = 0;
                }

                if (!cfg.threshold_full) {
                    delete (updated as any).full_threshold;
                } else if (updated.full_threshold == null) {
                    updated.full_threshold =
                        (updated.empty_threshold ?? 0) + 1;
                }

                // timeouts
                if (!cfg.timeout_empty) {
                    delete (updated as any).empty_timeout;
                }
                if (!cfg.timeout_full) {
                    delete (updated as any).full_timeout;
                }

                // email cooldown
                if (!cfg.email_cooldown) {
                    delete (updated as any).email_cooldown;
                }

                // metadata por modo
                updated.metadata = normalizeMetadataForMode(
                    updated.mode,
                    updated.metadata
                );
            }

            return updated;
        });
    }, [formData.mode, isLoadingZone, normalizeMetadataForMode]);

    // ========================================================================
    // EFFECT: resetar reid_required se tracker não suporta ReID
    // ========================================================================

    useEffect(() => {
        const currentReid = Boolean(
            (formData.metadata as any)?.reid_required
        );

        if (currentReid && !canUseReid) {
            setFormData(prev => ({
                ...prev,
                metadata: {
                    ...(prev.metadata || {}),
                    reid_required: false,
                },
            }));
            warning(
                'ReID desativado: o tracker atual da zona/câmera não suporta ReID. Use StrongSORT ou Fast StrongSORT para habilitar.'
            );
        }
    }, [canUseReid, formData.metadata, warning]);

    // ========================================================================
    // EFFECT: VALIDAR POLÍGONO
    // ========================================================================

    useEffect(() => {
        if (mode === 'view') {
            if (!snapshotUrl) {
                setIsValidPolygon(false);
                setValidationMessage('Capture uma foto antes de desenhar.');
                return;
            }
        }

        if (canvasPoints.length >= 3) {
            setIsValidPolygon(true);
            setValidationMessage(
                `Polígono válido com ${canvasPoints.length} pontos.`
            );
        } else if (canvasPoints.length === 0) {
            setIsValidPolygon(false);
            setValidationMessage(
                'Clique no canvas para adicionar pelo menos 3 pontos.'
            );
        } else {
            setIsValidPolygon(false);
            setValidationMessage(
                `Adicione mais ${3 - canvasPoints.length
                } ponto(s) para completar o polígono.`
            );
        }
    }, [canvasPoints.length, mode, snapshotUrl]);

    // ========================================================================
    // EFFECT: DRAW CANVAS
    // ========================================================================

    const drawCanvas = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        if (canvasPoints.length === 0) return;

        // Polígono
        if (canvasPoints.length >= 2) {
            ctx.beginPath();
            ctx.moveTo(canvasPoints[0].x, canvasPoints[0].y);
            for (let i = 1; i < canvasPoints.length; i++) {
                ctx.lineTo(canvasPoints[i].x, canvasPoints[i].y);
            }
            if (canvasPoints.length >= 3) {
                ctx.closePath();
                ctx.fillStyle = `${formData.color || ZONE_MODE_COLORS[formData.mode]
                    }33`;
                ctx.fill();
            }
            ctx.strokeStyle =
                formData.color || ZONE_MODE_COLORS[formData.mode];
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // Pontos
        canvasPoints.forEach((point, index) => {
            const isHovered = index === hoveredIndex;
            const isDragging = index === draggingIndex;
            const radius =
                isHovered || isDragging ? HOVER_RADIUS : POINT_RADIUS;

            ctx.beginPath();
            ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);

            if (isDragging) {
                ctx.fillStyle = '#EF4444';
            } else if (isHovered) {
                ctx.fillStyle = '#F59E0B';
            } else {
                ctx.fillStyle = '#1E40AF';
            }
            ctx.fill();

            ctx.strokeStyle = '#FFFFFF';
            ctx.lineWidth = 2;
            ctx.stroke();

            // índice
            ctx.fillStyle = '#FFFFFF';
            ctx.font = 'bold 12px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(String(index + 1), point.x, point.y);
        });
    }, [canvasPoints, draggingIndex, hoveredIndex, formData.color, formData.mode]);

    useEffect(() => {
        drawCanvas();
    }, [drawCanvas]);

    // ========================================================================
    // EFFECT: MONITORAR STATUS DO STREAM
    // ========================================================================

    useEffect(() => {
        if (!isOpen) return;

        const checkStreamStatus = async () => {
            try {
                const response = await fetch(
                    'http://localhost:8000/api/v1/stream/status',
                    {
                        headers: {
                            Authorization: `Bearer ${localStorage.getItem(
                                'access_token'
                            )}`,
                        },
                    }
                );
                if (!response.ok) {
                    setStreamActive(false);
                    return;
                }
                const data = await response.json();
                setStreamActive(Boolean(data.stream_active));
            } catch {
                setStreamActive(false);
            }
        };

        checkStreamStatus();
        const interval = setInterval(checkStreamStatus, 2000);
        return () => clearInterval(interval);
    }, [isOpen]);

    // ========================================================================
    // CANVAS HELPERS
    // ========================================================================

    const getCanvasCoordinates = (
        e: ReactMouseEvent<HTMLCanvasElement>
    ): Point => {
        const canvas = canvasRef.current;
        if (!canvas) return [0, 0];
        const rect = canvas.getBoundingClientRect();
        const x =
            ((e.clientX - rect.left) / rect.width) * CANVAS_WIDTH;
        const y =
            ((e.clientY - rect.top) / rect.height) * CANVAS_HEIGHT;
        return [x, y];
    };

    const findNearestPoint = (x: number, y: number): number | null => {
        const threshold = HOVER_RADIUS;
        for (let i = 0; i < canvasPoints.length; i++) {
            const dx = canvasPoints[i].x - x;
            const dy = canvasPoints[i].y - y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist <= threshold) return i;
        }
        return null;
    };

    // ========================================================================
    // CANVAS EVENT HANDLERS
    // ========================================================================

    const handleCanvasClick = (
        e: ReactMouseEvent<HTMLCanvasElement>
    ) => {
        if (mode === 'view' || !snapshotUrl) return;
        const [x, y] = getCanvasCoordinates(e);
        const nearest = findNearestPoint(x, y);
        if (nearest !== null) return;

        setCanvasPoints(prev => [...prev, { x, y }]);
    };

    const handleCanvasContextMenu = (
        e: ReactMouseEvent<HTMLCanvasElement>
    ) => {
        if (mode === 'view' || !snapshotUrl) return;
        e.preventDefault();
        const [x, y] = getCanvasCoordinates(e);
        const nearest = findNearestPoint(x, y);
        if (nearest !== null) {
            setCanvasPoints(prev =>
                prev.filter((_, i) => i !== nearest)
            );
            warning('Ponto removido.');
        }
    };

    const handleCanvasMouseMove = (
        e: ReactMouseEvent<HTMLCanvasElement>
    ) => {
        if (!snapshotUrl) return;
        const [x, y] = getCanvasCoordinates(e);

        if (draggingIndex !== null) {
            setCanvasPoints(prev =>
                prev.map((p, i) =>
                    i === draggingIndex ? { ...p, x, y } : p
                )
            );
            return;
        }

        const nearest = findNearestPoint(x, y);
        setHoveredIndex(nearest);
    };

    const handleCanvasMouseDown = (
        e: ReactMouseEvent<HTMLCanvasElement>
    ) => {
        if (mode === 'view' || !snapshotUrl) return;
        const [x, y] = getCanvasCoordinates(e);
        const nearest = findNearestPoint(x, y);
        if (nearest !== null) {
            setDraggingIndex(nearest);
        }
    };

    const handleCanvasMouseUp = () => {
        setDraggingIndex(null);
    };

    const handleCanvasMouseLeave = () => {
        setHoveredIndex(null);
        setDraggingIndex(null);
    };

    // ========================================================================
    // SNAPSHOT HANDLER
    // ========================================================================

    const handleCaptureSnapshot = async () => {
        if (mode === 'view') return;
        setCapturingSnapshot(true);
        try {
            const url = cameraId
                ? `http://localhost:8000/api/v1/stream/snapshot/${cameraId}`
                : 'http://localhost:8000/api/v1/stream/snapshot';

            const response = await fetch(url, {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem(
                        'access_token'
                    )}`,
                },
            });

            if (!response.ok) {
                throw new Error('Falha ao capturar snapshot');
            }

            const blob = await response.blob();
            const newUrl = URL.createObjectURL(blob);

            if (snapshotUrl) {
                URL.revokeObjectURL(snapshotUrl);
            }

            setSnapshotUrl(newUrl);

            // opcional: parar stream
            try {
                await fetch('http://localhost:8000/api/v1/stream/stop', {
                    method: 'POST',
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem(
                            'access_token'
                        )}`,
                    },
                });
            } catch (err) {
                console.warn('Não foi possível parar stream', err);
            }
        } catch (err) {
            console.error('Erro ao capturar snapshot', err);
            error('Erro ao capturar foto do stream.');
        } finally {
            setCapturingSnapshot(false);
        }
    };

    // ========================================================================
    // FORM HANDLERS
    // ========================================================================

    const handleFieldChange = <K extends keyof CreateZonePayload>(
        field: K,
        value: CreateZonePayload[K]
    ) => {
        setFormData(prev => ({
            ...prev,
            [field]: value,
        }));
    };

    const handleClearPoints = () => {
        setCanvasPoints([]);
        warning('Pontos limpos.');
    };

    const buildPayload = async (): Promise<{
        payload: CreateZonePayload | UpdateZonePayload;
        zoneId?: number;
    } | null> => {
        if (!formData.name.trim()) {
            error('Nome da zona é obrigatório.');
            return null;
        }

        if (canvasPoints.length < 3) {
            error('Adicione pelo menos 3 pontos para criar o polígono.');
            return null;
        }

        const normalizedPoints: Polygon = canvasPoints.map(p => [
            p.x / CANVAS_WIDTH,
            p.y / CANVAS_HEIGHT,
        ]);

        let snapshotBase64: string | undefined;
        if (snapshotUrl && mode === 'create') {
            try {
                const response = await fetch(snapshotUrl);
                const blob = await response.blob();
                const reader = new FileReader();

                snapshotBase64 = await new Promise<string>((resolve, reject) => {
                    reader.onloadend = () => {
                        try {
                            const base64 = (reader.result as string).split(',')[1];
                            resolve(base64);
                        } catch (err) {
                            reject(err);
                        }
                    };
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            } catch (err) {
                console.warn('Erro ao converter snapshot para base64', err);
            }
        }

        const modeConfig = ZONE_MODE_FIELDS[formData.mode];

        const payload: any = {
            ...formData,
            points: normalizedPoints,
            coordinate_system: 'normalized' as CoordinateSystem,
            snapshot_base64: snapshotBase64,
            metadata: normalizeMetadataForMode(
                formData.mode,
                formData.metadata
            ),
        };

        // Limpa campos não usados pelo modo atual
        if (modeConfig) {
            if (!modeConfig.threshold_empty) {
                delete payload.empty_threshold;
            }
            if (!modeConfig.threshold_full) {
                delete payload.full_threshold;
            }
            if (!modeConfig.timeout_empty) {
                delete payload.empty_timeout;
            }
            if (!modeConfig.timeout_full) {
                delete payload.full_timeout;
            }
            if (!modeConfig.email_cooldown) {
                delete payload.email_cooldown;
            }

            if (!modeConfig.capacity && payload.metadata) {
                const { max_capacity, alert_percentage, ...rest } =
                    payload.metadata;
                payload.metadata = rest;
            }
        }

        // thresholds seguros
        if (payload.full_threshold != null) {
            const minFull = (payload.empty_threshold ?? 0) + 1;
            if (payload.full_threshold < minFull) {
                payload.full_threshold = minFull;
            }
        }
        if (payload.empty_threshold != null && payload.empty_threshold < 0) {
            payload.empty_threshold = 0;
        }

        // remove undefined/null
        Object.keys(payload).forEach(key => {
            if (
                payload[key] === undefined ||
                payload[key] === null
            ) {
                delete payload[key];
            }
        });

        return {
            payload: payload as CreateZonePayload | UpdateZonePayload,
            zoneId: zone?.id,
        };
    };

    const handleSave = async () => {
        const result = await buildPayload();
        if (!result) return;

        setIsSaving(true);
        try {
            await onSave(result.payload, result.zoneId);
            success(
                mode === 'create'
                    ? 'Zona criada com sucesso.'
                    : 'Zona atualizada com sucesso.'
            );
            setCanvasPoints([]);
            onClose();
        } catch (err) {
            console.error('Erro ao salvar zona', err);
            error('Erro ao salvar zona.');
        } finally {
            setIsSaving(false);
        }
    };

    // ========================================================================
    // RENDER
    // ========================================================================

    if (!isOpen) return null;

    const disabled = mode === 'view';

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Drawer */}
            <div className="fixed inset-y-0 right-0 w-full max-w-4xl bg-white shadow-2xl z-50 overflow-hidden flex flex-col">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-blue-700 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
                            <svg
                                className="w-6 h-6 text-white"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                                />
                            </svg>
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">
                                {mode === 'create'
                                    ? 'Nova Zona'
                                    : mode === 'edit'
                                        ? 'Editar Zona'
                                        : 'Visualizar Zona'}
                            </h2>
                            <p className="text-sm text-blue-100">
                                {mode === 'create'
                                    ? 'Desenhe o polígono no vídeo'
                                    : `ID: ${zone?.id}`}
                            </p>
                        </div>
                    </div>

                    <button
                        onClick={onClose}
                        className="w-10 h-10 flex items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
                    >
                        <X className="w-5 h-5 text-white" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    <div className="max-w-3xl mx-auto space-y-6">
                        {/* Canvas Section */}
                        <div className="bg-gray-50 rounded-xl p-4 border-2 border-gray-200 space-y-3">
                            <div className="flex items-center justify-between mb-1">
                                <div>
                                    <h3 className="font-semibold text-gray-900">
                                        Desenhar Zona
                                    </h3>
                                    <p className="text-sm text-gray-600">
                                        <span className="font-medium">Botão esquerdo</span>{' '}
                                        adiciona ponto •{' '}
                                        <span className="font-medium">Botão direito</span>{' '}
                                        remove ponto
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    {/* Capturar snapshot */}
                                    <button
                                        onClick={handleCaptureSnapshot}
                                        disabled={
                                            !streamActive ||
                                            capturingSnapshot ||
                                            mode === 'view'
                                        }
                                        className="flex items-center gap-2 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                                        title={
                                            !streamActive
                                                ? 'Inicie o stream primeiro'
                                                : 'Capturar foto do stream'
                                        }
                                    >
                                        <CameraIcon className="w-4 h-4" />
                                        {capturingSnapshot ? 'Capturando...' : 'Capturar'}
                                    </button>

                                    {!streamActive && (
                                        <div className="text-xs text-amber-700 bg-amber-50 px-3 py-1 rounded-lg border border-amber-200 flex items-center gap-1">
                                            <AlertCircle className="w-3 h-3" />
                                            <span>Stream parado</span>
                                        </div>
                                    )}

                                    {/* Limpar pontos */}
                                    <button
                                        onClick={handleClearPoints}
                                        disabled={canvasPoints.length === 0 || disabled}
                                        className="flex items-center gap-2 px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                        Limpar
                                    </button>
                                </div>
                            </div>

                            {/* Canvas + snapshot */}
                            <div
                                ref={containerRef}
                                className="relative bg-black rounded-lg overflow-hidden border-2 border-gray-300"
                                style={{ aspectRatio: `${CANVAS_WIDTH}/${CANVAS_HEIGHT}` }}
                            >
                                {snapshotUrl ? (
                                    <img
                                        ref={imgRef}
                                        src={snapshotUrl}
                                        alt="Snapshot"
                                        className="absolute inset-0 w-full h-full object-contain bg-gray-900"
                                        onLoad={drawCanvas}
                                    />
                                ) : mode === 'edit' ? (
                                    <div className="absolute inset-0 w-full h-full bg-gray-800 flex items-center justify-center">
                                        <div className="text-gray-400 text-sm">
                                            Editando polígono da zona
                                        </div>
                                    </div>
                                ) : (
                                    <div className="absolute inset-0 w-full h-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center pointer-events-none">
                                        <div className="text-center text-gray-400">
                                            <svg
                                                className="w-16 h-16 mx-auto mb-3 opacity-50"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                            >
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M3 9a2 2 0 012-2h.93A2 2 0 007.6 5.11l.81-1.22A2 2 0 0110.07 3h3.86a2 2 0 011.66.89l.81 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                                                />
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M15 7a3 3 0 11-6 0 3 3 0 016 0z"
                                                />
                                            </svg>
                                            <p className="text-sm font-medium mb-2">
                                                Nenhuma foto capturada
                                            </p>
                                            <p className="text-xs text-gray-500">
                                                Clique no botão &quot;Capturar&quot; acima
                                            </p>
                                        </div>
                                    </div>
                                )}

                                {/* Canvas overlay */}
                                <canvas
                                    ref={canvasRef}
                                    width={CANVAS_WIDTH}
                                    height={CANVAS_HEIGHT}
                                    onClick={
                                        mode !== 'view' && snapshotUrl
                                            ? handleCanvasClick
                                            : undefined
                                    }
                                    onContextMenu={
                                        mode !== 'view' && snapshotUrl
                                            ? handleCanvasContextMenu
                                            : undefined
                                    }
                                    onMouseMove={
                                        snapshotUrl ? handleCanvasMouseMove : undefined
                                    }
                                    onMouseDown={
                                        mode !== 'view' && snapshotUrl
                                            ? handleCanvasMouseDown
                                            : undefined
                                    }
                                    onMouseUp={
                                        mode !== 'view' && snapshotUrl
                                            ? handleCanvasMouseUp
                                            : undefined
                                    }
                                    onMouseLeave={
                                        snapshotUrl ? handleCanvasMouseLeave : undefined
                                    }
                                    className={`absolute inset-0 w-full h-full ${mode === 'view'
                                            ? 'cursor-default'
                                            : snapshotUrl
                                                ? 'cursor-crosshair'
                                                : 'cursor-not-allowed'
                                        }`}
                                    style={{
                                        imageRendering: 'crisp-edges',
                                        pointerEvents:
                                            mode === 'view'
                                                ? 'none'
                                                : snapshotUrl
                                                    ? 'auto'
                                                    : 'none',
                                    }}
                                />
                            </div>

                            {/* Validation status */}
                            <div
                                className={`mt-3 flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${isValidPolygon
                                        ? 'bg-green-50 text-green-700'
                                        : 'bg-amber-50 text-amber-700'
                                    }`}
                            >
                                {isValidPolygon ? (
                                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                                ) : (
                                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                                )}
                                <span className="font-medium">{validationMessage}</span>
                            </div>
                        </div>

                        {/* Form Section */}
                        <div className="bg-white rounded-xl border-2 border-gray-200 p-6 space-y-4">
                            <h3 className="font-semibold text-gray-900 text-lg">
                                Configurações da Zona
                            </h3>

                            {/* Nome */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Nome da Zona
                                </label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e =>
                                        handleFieldChange('name', e.target.value)
                                    }
                                    placeholder="Ex: Entrada Principal"
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60"
                                    disabled={disabled}
                                />
                            </div>

                            {/* Seletor de Classes COCO */}
                            <ClassSelector
                                selectedClasses={
                                    Array.isArray(formData.metadata?.detection_classes)
                                        ? formData.metadata!.detection_classes
                                        : [0]
                                }
                                onChange={classes => {
                                    setFormData(prev => ({
                                        ...prev,
                                        metadata: {
                                            ...(prev.metadata || {}),
                                            detection_classes: classes,
                                        },
                                    }));
                                }}
                                disabled={mode === 'view'}
                                showSearch={true}
                                maxHeight="250px"
                            />

                            {/* Modo */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Modo de Operação
                                </label>
                                <select
                                    value={formData.mode}
                                    onChange={e =>
                                        handleFieldChange(
                                            'mode',
                                            e.target.value as ZoneMode
                                        )
                                    }
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60"
                                    disabled={disabled}
                                >
                                    {Object.entries(ZONE_MODE_LABELS).map(
                                        ([value, label]) => (
                                            <option key={value} value={value}>
                                                {label}
                                            </option>
                                        )
                                    )}
                                </select>
                                <p className="mt-1 text-sm text-gray-600">
                                    {ZONE_MODE_DESCRIPTIONS[formData.mode]}
                                </p>
                            </div>

                            {/* Câmera associada */}
                            <div>
                                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                                    <CameraIcon className="w-4 h-4" />
                                    Câmera Associada
                                </label>
                                <select
                                    value={formData.camera_id ?? ''}
                                    onChange={e =>
                                        handleFieldChange(
                                            'camera_id',
                                            e.target.value
                                                ? parseInt(e.target.value, 10)
                                                : null
                                        )
                                    }
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60"
                                    disabled={disabled || camerasLoading}
                                >
                                    <option value="">Nenhuma</option>
                                    {cameras.map(cam => (
                                        <option
                                            key={cam.id}
                                            value={cam.id}
                                            disabled={!cam.enabled}
                                        >
                                            {cam.name}
                                            {!cam.enabled ? ' (Inativa)' : ''}
                                        </option>
                                    ))}
                                </select>
                                <p className="mt-1 text-sm text-gray-600">
                                    {formData.camera_id
                                        ? 'Zona vinculada a câmera específica'
                                        : 'Não vinculada a câmera'}
                                </p>
                            </div>

                            {/* Tracker avançado (opcional, por zona) */}
                            <div className="space-y-1">
                                <label className="block text-sm font-medium text-gray-700">
                                    Tracker avançado por zona
                                </label>
                                <select
                                    value={
                                        (formData.metadata as any)?.trackeroverride ??
                                        ''
                                    }
                                    onChange={e => {
                                        const value = e.target.value as TrackerType;

                                        setFormData(prev => ({
                                            ...prev,
                                            metadata: {
                                                ...prev.metadata,
                                                trackeroverride: value
                                                    ? value
                                                    : undefined,
                                            },
                                        }));
                                    }}
                                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60"
                                    disabled={mode === 'view'}
                                >
                                    <option value="">
                                        Herdar tracker padrão da câmera
                                    </option>
                                    {TRACKER_OPTIONS.map(opt => (
                                        <option key={opt.value} value={opt.value}>
                                            {opt.label}
                                        </option>
                                    ))}
                                </select>
                                <p className="text-xs text-gray-500">
                                    {(formData.metadata as any)?.trackeroverride
                                        ? TRACKER_OPTIONS.find(
                                            o =>
                                                o.value ===
                                                (formData.metadata as any)
                                                    .trackeroverride
                                        )?.description
                                        : 'Use um tracker mais robusto apenas em zonas críticas (fila, suspeito, alta prioridade).'}
                                </p>

                                {/* GOVERNANÇA DE REID POR ZONA */}
                                <div className="mt-4 pt-2 border-t border-gray-100 flex items-start justify-between gap-3">
                                    <div className="space-y-1">
                                        <p className="text-sm font-medium text-gray-700">
                                            Exigir rastreamento nesta zona
                                        </p>
                                        <p className="mt-1 text-sm text-gray-600">
                                            Quando ativado, só entram nas métricas desta
                                            zona os objetos que já tiverem um id global
                                            resolvido pelo rastreamento.
                                        </p>
                                    </div>

                                    <input
                                        type="checkbox"
                                        className="mt-1 h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 disabled:opacity-60"
                                        disabled={mode === 'view' || !canUseReid}
                                        checked={Boolean(
                                            (formData.metadata as any)
                                                ?.reid_required
                                        )}
                                        onChange={e =>
                                            setFormData(prev => ({
                                                ...prev,
                                                metadata: {
                                                    ...(prev.metadata || {}),
                                                    reid_required:
                                                        e.target.checked,
                                                },
                                            }))
                                        }
                                    />
                                </div>
                            </div>

                            {/* Thresholds */}
                            {(shouldShowField('threshold_empty') ||
                                shouldShowField('threshold_full')) && (
                                    <div className="grid grid-cols-2 gap-4">
                                        {shouldShowField('threshold_empty') && (
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                                    Threshold Vazio
                                                </label>
                                                <input
                                                    type="number"
                                                    min={0}
                                                    value={formData.empty_threshold ?? 0}
                                                    onChange={e =>
                                                        handleFieldChange(
                                                            'empty_threshold',
                                                            Number(e.target.value)
                                                        )
                                                    }
                                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60"
                                                    disabled={disabled}
                                                />
                                                <p className="mt-1 text-xs text-gray-500">
                                                    Mínimo de objetos para ser considerado
                                                    vazio.
                                                </p>
                                            </div>
                                        )}

                                        {shouldShowField('threshold_full') && (
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                                    {formData.mode === 'counting'
                                                        ? 'Threshold Contagem'
                                                        : formData.mode === 'alert'
                                                            ? 'Threshold Alerta'
                                                            : 'Threshold Cheio'}
                                                </label>
                                                <input
                                                    type="number"
                                                    min={
                                                        (formData.empty_threshold ?? 0) + 1
                                                    }
                                                    value={formData.full_threshold ?? 3}
                                                    onChange={e => {
                                                        const value = Number(
                                                            e.target.value
                                                        );
                                                        const minValue =
                                                            (formData.empty_threshold ??
                                                                0) + 1;
                                                        if (value < minValue) {
                                                            warning(
                                                                `Threshold Cheio deve ser maior que ${formData.empty_threshold ??
                                                                0
                                                                }.`
                                                            );
                                                            return;
                                                        }
                                                        handleFieldChange(
                                                            'full_threshold',
                                                            value
                                                        );
                                                    }}
                                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60"
                                                    disabled={disabled}
                                                />
                                                <p className="mt-1 text-xs text-gray-500">
                                                    {formData.mode === 'counting'
                                                        ? 'Mínimo para registrar entrada/saída.'
                                                        : formData.mode === 'alert'
                                                            ? 'Pessoas para disparar alerta.'
                                                            : `Número de objetos para considerar cheio (mínimo: ${(formData.empty_threshold ??
                                                                0) + 1
                                                            }).`}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                )}

                            {/* Timeouts */}
                            {(shouldShowField('timeout_empty') ||
                                shouldShowField('timeout_full')) && (
                                    <div className="grid grid-cols-2 gap-4">
                                        {shouldShowField('timeout_empty') && (
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                                    Timeout Vazio (s)
                                                </label>
                                                <input
                                                    type="number"
                                                    min={0}
                                                    step={0.5}
                                                    value={formData.empty_timeout ?? 5}
                                                    onChange={e =>
                                                        handleFieldChange(
                                                            'empty_timeout',
                                                            Number(e.target.value)
                                                        )
                                                    }
                                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60"
                                                    disabled={disabled}
                                                />
                                                <p className="mt-1 text-xs text-gray-500">
                                                    Tempo vazio antes de alertar.
                                                </p>
                                            </div>
                                        )}

                                        {shouldShowField('timeout_full') && (
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                                    {formData.mode === 'alert'
                                                        ? 'Timeout Alerta (s)'
                                                        : formData.mode === 'capacity'
                                                            ? 'Timeout de Lotação (s)'
                                                            : formData.mode === 'counting'
                                                                ? 'Tempo de Confirmação (s)'
                                                                : 'Timeout Cheio (s)'}
                                                </label>
                                                <input
                                                    type="number"
                                                    min={0}
                                                    step={0.5}
                                                    value={
                                                        formData.mode === 'counting'
                                                            ? formData.metadata
                                                                ?.confirmation_time ?? 0
                                                            : formData.full_timeout ?? 10
                                                    }
                                                    onChange={e => {
                                                        const value = Number(
                                                            e.target.value
                                                        );
                                                        if (
                                                            formData.mode === 'counting'
                                                        ) {
                                                            setFormData(prev => ({
                                                                ...prev,
                                                                metadata: {
                                                                    ...(prev.metadata ||
                                                                        {}),
                                                                    confirmation_time:
                                                                        isNaN(value)
                                                                            ? 0
                                                                            : value,
                                                                },
                                                            }));
                                                        } else {
                                                            handleFieldChange(
                                                                'full_timeout',
                                                                value
                                                            );
                                                        }
                                                    }}
                                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60"
                                                    disabled={disabled}
                                                />
                                                <p className="mt-1 text-xs text-gray-500">
                                                    {formData.mode === 'alert'
                                                        ? 'Tolerância antes de disparar alerta.'
                                                        : formData.mode === 'capacity'
                                                            ? 'Tempo na capacidade antes de alertar (0 = imediato).'
                                                            : formData.mode === 'counting'
                                                                ? 'Tempo que o objeto deve permanecer para ser contado.'
                                                                : 'Tempo cheio antes de alertar.'}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                )}

                            {/* CAPACITY BLOCK */}
                            {shouldShowField('capacity') &&
                                formData.mode === ZoneMode.CAPACITY && (
                                    <div className="bg-amber-50 border-2 border-amber-200 rounded-lg p-4">
                                        <label className="flex items-center gap-2 text-sm font-medium text-amber-900 mb-2">
                                            <svg
                                                className="w-5 h-5"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                            >
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                                                />
                                            </svg>
                                            Capacidade Máxima
                                        </label>
                                        <input
                                            type="number"
                                            min={1}
                                            max={1000}
                                            value={
                                                formData.metadata?.max_capacity ??
                                                50
                                            }
                                            onChange={e =>
                                                setFormData(prev => ({
                                                    ...prev,
                                                    metadata: {
                                                        ...(prev.metadata || {}),
                                                        max_capacity: Number(
                                                            e.target.value
                                                        ),
                                                    },
                                                }))
                                            }
                                            className="w-full px-4 py-2 bg-white border border-amber-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent font-bold text-lg text-amber-900 disabled:opacity-60"
                                            disabled={disabled}
                                            placeholder="50"
                                        />
                                        <p className="mt-2 text-sm text-amber-800 font-medium">
                                            📊 Lotação máxima:{' '}
                                            {formData.metadata?.max_capacity ||
                                                50}{' '}
                                            pessoas
                                        </p>

                                        {/* Slider de alerta */}
                                        <div className="mt-4 pt-4 border-t border-amber-300">
                                            <label className="block text-sm font-medium text-amber-900 mb-2">
                                                Percentual de Alerta (%)
                                            </label>
                                            <input
                                                type="range"
                                                min={0}
                                                max={100}
                                                step={5}
                                                value={
                                                    formData.metadata
                                                        ?.alert_percentage ?? 90
                                                }
                                                onChange={e =>
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        metadata: {
                                                            ...(prev.metadata ||
                                                                {}),
                                                            alert_percentage:
                                                                Number(
                                                                    e.target.value
                                                                ),
                                                        },
                                                    }))
                                                }
                                                className="w-full h-2 bg-amber-200 rounded-lg appearance-none cursor-pointer accent-amber-600 hover:accent-amber-700 disabled:opacity-50"
                                                disabled={disabled}
                                            />
                                            <p className="mt-2 text-xs text-amber-700 bg-amber-100 px-3 py-2 rounded-lg border border-amber-300">
                                                🔔 Sistema alertará quando atingir{' '}
                                                <span className="font-bold">
                                                    {formData.metadata
                                                        ?.alert_percentage ?? 90}
                                                    %
                                                </span>{' '}
                                                da capacidade (
                                                <span className="font-bold">
                                                    {Math.floor(
                                                        ((formData.metadata
                                                            ?.max_capacity ?? 50) *
                                                            (formData.metadata
                                                                ?.alert_percentage ??
                                                                90)) /
                                                        100
                                                    )}
                                                </span>{' '}
                                                pessoas).
                                            </p>
                                        </div>
                                    </div>
                                )}

                            {/* COUNTING MODE BLOCK */}
                            {formData.mode === ZoneMode.COUNTING && (
                                <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 space-y-4">
                                    <div className="flex items-center gap-2 mb-3">
                                        <svg
                                            className="w-5 h-5 text-blue-600"
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
                                        <h4 className="text-sm font-medium text-blue-900">
                                            Configurações de Contagem
                                        </h4>
                                    </div>

                                    {/* Direção */}
                                    <div>
                                        <label className="block text-sm font-medium text-blue-900 mb-2">
                                            Direção de Contagem
                                        </label>
                                        <div className="space-y-2">
                                            {(['in', 'out', 'both'] as const).map(
                                                dir => (
                                                    <label
                                                        key={dir}
                                                        className={`flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer ${formData.metadata
                                                                ?.count_direction ===
                                                                dir ||
                                                                (!formData.metadata
                                                                    ?.count_direction &&
                                                                    dir === 'both')
                                                                ? 'border-blue-300 bg-white'
                                                                : 'border-blue-200 hover:bg-blue-100'
                                                            }`}
                                                    >
                                                        <input
                                                            type="radio"
                                                            name="count_direction"
                                                            value={dir}
                                                            checked={
                                                                formData.metadata
                                                                    ?.count_direction ===
                                                                dir ||
                                                                (!formData.metadata
                                                                    ?.count_direction &&
                                                                    dir === 'both')
                                                            }
                                                            onChange={() =>
                                                                setFormData(
                                                                    prev => ({
                                                                        ...prev,
                                                                        metadata:
                                                                        {
                                                                            ...(prev.metadata ||
                                                                                {}),
                                                                            count_direction:
                                                                                dir,
                                                                        },
                                                                    })
                                                                )
                                                            }
                                                            disabled={disabled}
                                                            className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                                                        />
                                                        <div className="flex-1">
                                                            <span className="text-sm font-medium text-blue-900">
                                                                {dir === 'in'
                                                                    ? 'Apenas Entradas'
                                                                    : dir ===
                                                                        'out'
                                                                        ? 'Apenas Saídas'
                                                                        : 'Ambas Direções'}
                                                            </span>
                                                            <p className="text-xs text-blue-700 mt-0.5">
                                                                {dir === 'in'
                                                                    ? 'Conta apenas objetos entrando na zona.'
                                                                    : dir ===
                                                                        'out'
                                                                        ? 'Conta apenas objetos saindo da zona.'
                                                                        : 'Contadores separados IN/OUT (recomendado).'}
                                                            </p>
                                                        </div>
                                                    </label>
                                                )
                                            )}
                                        </div>
                                    </div>

                                    {/* Reset */}
                                    <div className="pt-3 border-t border-blue-300">
                                        <label className="block text-sm font-medium text-blue-900 mb-2">
                                            Período de Reset do Contador
                                        </label>
                                        <select
                                            value={
                                                formData.metadata
                                                    ?.reset_interval ?? 'daily'
                                            }
                                            onChange={e =>
                                                setFormData(prev => ({
                                                    ...prev,
                                                    metadata: {
                                                        ...(prev.metadata || {}),
                                                        reset_interval:
                                                            e.target.value,
                                                    },
                                                }))
                                            }
                                            className="w-full px-4 py-2 bg-white border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
                                            disabled={disabled}
                                        >
                                            <option value="none">
                                                Nunca (acumula sempre)
                                            </option>
                                            <option value="hourly">
                                                A cada 1 hora
                                            </option>
                                            <option value="daily">
                                                Diariamente às 00:00
                                            </option>
                                            <option value="weekly">
                                                Semanalmente (Segunda 00:00)
                                            </option>
                                            <option value="monthly">
                                                Mensalmente (dia 1 às 00:00)
                                            </option>
                                        </select>
                                        <p className="mt-1 text-xs text-blue-700">
                                            Zera automaticamente para gerar
                                            relatórios periódicos.
                                        </p>
                                    </div>

                                    {/* Intersection threshold */}
                                    <div className="pt-3 border-t border-blue-300">
                                        <label className="block text-sm font-medium text-blue-900 mb-2">
                                            Percentual mínimo do objeto dentro da
                                            zona
                                        </label>
                                        <input
                                            type="range"
                                            min={30}
                                            max={90}
                                            step={5}
                                            value={
                                                (formData.metadata
                                                    ?.intersection_threshold ??
                                                    0.7) * 100
                                            }
                                            onChange={e => {
                                                const value =
                                                    Number(e.target.value) / 100;
                                                setFormData(prev => ({
                                                    ...prev,
                                                    metadata: {
                                                        ...(prev.metadata || {}),
                                                        intersection_threshold:
                                                            value,
                                                    },
                                                }));
                                            }}
                                            className="w-full"
                                            disabled={disabled}
                                        />
                                        <p className="mt-1 text-xs text-blue-700">
                                            A zona só contará entrada/saída quando
                                            pelo menos{' '}
                                            {(
                                                (formData.metadata
                                                    ?.intersection_threshold ??
                                                    0.7) * 100
                                            ).toFixed(0)}
                                            % da bbox estiver dentro do polígono.
                                        </p>
                                    </div>

                                    {/* Alerta por limite */}
                                    <div className="pt-3 border-t border-blue-300">
                                        <label className="flex items-center gap-2 mb-3 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={
                                                    formData.metadata
                                                        ?.alert_enabled ?? false
                                                }
                                                onChange={e =>
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        metadata: {
                                                            ...(prev.metadata ||
                                                                {}),
                                                            alert_enabled:
                                                                e.target.checked,
                                                        },
                                                    }))
                                                }
                                                disabled={disabled}
                                                className="w-4 h-4 text-blue-600 border-blue-300 rounded focus:ring-blue-500"
                                            />
                                            <span className="text-sm font-medium text-blue-900">
                                                Alerta por Limite de Contagem
                                            </span>
                                        </label>

                                        {formData.metadata?.alert_enabled && (
                                            <div className="ml-6 space-y-1">
                                                <label className="block text-sm font-medium text-blue-900">
                                                    Disparar alerta quando atingir
                                                </label>
                                                <input
                                                    type="number"
                                                    min={1}
                                                    max={10000}
                                                    value={
                                                        formData.metadata
                                                            ?.alert_threshold ??
                                                        100
                                                    }
                                                    onChange={e =>
                                                        setFormData(prev => ({
                                                            ...prev,
                                                            metadata: {
                                                                ...(prev.metadata ||
                                                                    {}),
                                                                alert_threshold:
                                                                    Number(
                                                                        e.target
                                                                            .value
                                                                    ),
                                                            },
                                                        }))
                                                    }
                                                    className="w-full px-4 py-2 bg-white border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-bold text-lg text-blue-900 disabled:opacity-50"
                                                    disabled={disabled}
                                                    placeholder="100"
                                                />
                                                <p className="mt-1 text-xs text-blue-700 bg-blue-100 px-3 py-2 rounded-lg border border-blue-300">
                                                    Sistema enviará alerta por email
                                                    quando contador atingir{' '}
                                                    <span className="font-bold">
                                                        {formData.metadata
                                                            ?.alert_threshold ??
                                                            100}
                                                    </span>{' '}
                                                    eventos.
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* QUEUE MODE BLOCK */}
                            {formData.mode === ZoneMode.QUEUE && (
                                <div className="bg-indigo-50 border-2 border-indigo-200 rounded-lg p-4 space-y-4">
                                    <div className="flex items-center gap-2 mb-3">
                                        <svg
                                            className="w-5 h-5 text-indigo-600"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                        >
                                            <path
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                strokeWidth={2}
                                                d="M8 7h13M8 12h13M8 17h13M3 7h.01M3 12h.01M3 17h.01"
                                            />
                                        </svg>
                                        <h4 className="text-sm font-medium text-indigo-900">
                                            Configurações de Fila
                                        </h4>
                                    </div>

                                    {/* Comprimento da fila */}
                                    <div className="grid grid-cols-3 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-indigo-900 mb-1">
                                                Tamanho Máx. Desejável
                                            </label>
                                            <input
                                                type="number"
                                                min={1}
                                                value={
                                                    formData.metadata
                                                        ?.max_queue_length ?? 10
                                                }
                                                onChange={e =>
                                                    setFormData(prev => {
                                                        const value =
                                                            Number(
                                                                e.target.value
                                                            ) || 1;
                                                        const warn =
                                                            prev.metadata
                                                                ?.warning_queue_length ??
                                                            Math.round(
                                                                value * 0.7
                                                            );
                                                        const crit =
                                                            prev.metadata
                                                                ?.critical_queue_length ??
                                                            value;
                                                        return {
                                                            ...prev,
                                                            metadata: {
                                                                ...(prev.metadata ||
                                                                    {}),
                                                                max_queue_length:
                                                                    value,
                                                                warning_queue_length:
                                                                    warn,
                                                                critical_queue_length:
                                                                    crit,
                                                            },
                                                        };
                                                    })
                                                }
                                                disabled={disabled}
                                                className="w-full px-3 py-2 bg-white border border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-indigo-900 font-semibold"
                                            />
                                            <p className="mt-1 text-xs text-indigo-700">
                                                Comprimento de fila considerado
                                                aceitável.
                                            </p>
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-indigo-900 mb-1">
                                                Aviso (warning)
                                            </label>
                                            <input
                                                type="number"
                                                min={1}
                                                value={
                                                    formData.metadata
                                                        ?.warning_queue_length ??
                                                    Math.round(
                                                        (formData.metadata
                                                            ?.max_queue_length ??
                                                            10) * 0.7
                                                    )
                                                }
                                                onChange={e =>
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        metadata: {
                                                            ...(prev.metadata ||
                                                                {}),
                                                            warning_queue_length:
                                                                Number(
                                                                    e.target.value
                                                                ) || 1,
                                                        },
                                                    }))
                                                }
                                                disabled={disabled}
                                                className="w-full px-3 py-2 bg-white border border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                            />
                                            <p className="mt-1 text-xs text-indigo-700">
                                                A partir de quantas pessoas a fila
                                                entra em aviso.
                                            </p>
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-indigo-900 mb-1">
                                                Crítico
                                            </label>
                                            <input
                                                type="number"
                                                min={1}
                                                value={
                                                    formData.metadata
                                                        ?.critical_queue_length ??
                                                    (formData.metadata
                                                        ?.max_queue_length ?? 10)
                                                }
                                                onChange={e =>
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        metadata: {
                                                            ...(prev.metadata ||
                                                                {}),
                                                            critical_queue_length:
                                                                Number(
                                                                    e.target.value
                                                                ) || 1,
                                                        },
                                                    }))
                                                }
                                                disabled={disabled}
                                                className="w-full px-3 py-2 bg-white border border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                            />
                                            <p className="mt-1 text-xs text-indigo-700">
                                                Comprimento de fila considerado
                                                crítico.
                                            </p>
                                        </div>
                                    </div>

                                    {/* SLA de espera */}
                                    <div className="grid grid-cols-2 gap-4 pt-3 border-t border-indigo-200">
                                        <div>
                                            <label className="block text-sm font-medium text-indigo-900 mb-1">
                                                Tempo de Espera (warning) – s
                                            </label>
                                            <input
                                                type="number"
                                                min={0}
                                                value={
                                                    formData.metadata
                                                        ?.max_wait_warning ??
                                                    120
                                                }
                                                onChange={e =>
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        metadata: {
                                                            ...(prev.metadata ||
                                                                {}),
                                                            max_wait_warning:
                                                                Number(
                                                                    e.target.value
                                                                ) || 0,
                                                        },
                                                    }))
                                                }
                                                disabled={disabled}
                                                className="w-full px-3 py-2 bg-white border border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                            />
                                            <p className="mt-1 text-xs text-indigo-700">
                                                Tempo médio de espera para sinalizar
                                                fila alta.
                                            </p>
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-indigo-900 mb-1">
                                                Tempo de Espera (crítico) – s
                                            </label>
                                            <input
                                                type="number"
                                                min={0}
                                                value={
                                                    formData.metadata
                                                        ?.max_wait_critical ??
                                                    300
                                                }
                                                onChange={e =>
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        metadata: {
                                                            ...(prev.metadata ||
                                                                {}),
                                                            max_wait_critical:
                                                                Number(
                                                                    e.target.value
                                                                ) || 0,
                                                        },
                                                    }))
                                                }
                                                disabled={disabled}
                                                className="w-full px-3 py-2 bg-white border border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                            />
                                            <p className="mt-1 text-xs text-indigo-700">
                                                Tempo máximo de espera aceitável antes
                                                de marcar fila como crítica.
                                            </p>
                                        </div>
                                    </div>

                                    {/* Histerese de entrada/saída */}
                                    <div className="grid grid-cols-2 gap-4 pt-3 border-t border-indigo-200">
                                        <div>
                                            <label className="block text-sm font-medium text-indigo-900 mb-1">
                                                Tempo de Confirmação de Entrada – s
                                            </label>
                                            <input
                                                type="number"
                                                min={0}
                                                step={0.1}
                                                value={
                                                    formData.metadata
                                                        ?.queue_join_confirm_time ??
                                                    1
                                                }
                                                onChange={e =>
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        metadata: {
                                                            ...(prev.metadata ||
                                                                {}),
                                                            queue_join_confirm_time:
                                                                Number(
                                                                    e.target.value
                                                                ) || 0,
                                                        },
                                                    }))
                                                }
                                                disabled={disabled}
                                                className="w-full px-3 py-2 bg-white border border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                            />
                                            <p className="mt-1 text-xs text-indigo-700">
                                                Tempo mínimo que o objeto deve
                                                permanecer dentro da zona para ser
                                                considerado na fila.
                                            </p>
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-indigo-900 mb-1">
                                                Tempo de Graça na Saída – s
                                            </label>
                                            <input
                                                type="number"
                                                min={0}
                                                step={0.1}
                                                value={
                                                    formData.metadata
                                                        ?.queue_leave_grace_time ??
                                                    2
                                                }
                                                onChange={e =>
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        metadata: {
                                                            ...(prev.metadata ||
                                                                {}),
                                                            queue_leave_grace_time:
                                                                Number(
                                                                    e.target.value
                                                                ) || 0,
                                                        },
                                                    }))
                                                }
                                                disabled={disabled}
                                                className="w-full px-3 py-2 bg-white border border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                            />
                                            <p className="mt-1 text-xs text-indigo-700">
                                                Tempo que o objeto pode ficar fora da
                                                zona antes de ser considerado saída
                                                definitiva/abandono.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Email cooldown */}
                            {shouldShowField('email_cooldown') && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        {formData.mode === 'capacity'
                                            ? 'Cooldown de Alerta de Lotação (min)'
                                            : 'Cooldown de Email (min)'}
                                    </label>
                                    <input
                                        type="number"
                                        min={1}
                                        max={60}
                                        step={1}
                                        value={Math.round(
                                            (formData.email_cooldown ?? 600) / 60
                                        )}
                                        onChange={e =>
                                            handleFieldChange(
                                                'email_cooldown',
                                                Number(e.target.value) * 60
                                            )
                                        }
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60"
                                        disabled={disabled}
                                    />
                                    <p className="mt-1 text-xs text-gray-500">
                                        {formData.mode === 'capacity'
                                            ? 'Tempo mínimo entre alertas de lotação crítica por email (padrão: 10 minutos).'
                                            : 'Tempo mínimo entre alertas por email (padrão: 10 minutos).'}
                                    </p>
                                </div>
                            )}

                            {/* Cor */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Cor da Zona
                                </label>
                                <div className="flex items-center gap-3">
                                    <input
                                        type="color"
                                        value={
                                            formData.color ||
                                            ZONE_MODE_COLORS[formData.mode]
                                        }
                                        onChange={e =>
                                            handleFieldChange('color', e.target.value)
                                        }
                                        className="w-16 h-10 rounded border border-gray-300 cursor-pointer disabled:opacity-60"
                                        disabled={disabled}
                                    />
                                    <input
                                        type="text"
                                        value={
                                            formData.color ||
                                            ZONE_MODE_COLORS[formData.mode]
                                        }
                                        onChange={e =>
                                            handleFieldChange('color', e.target.value)
                                        }
                                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm disabled:opacity-60"
                                        placeholder="#3B82F6"
                                        disabled={disabled}
                                    />
                                </div>
                            </div>

                            {/* Descrição */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Descrição (opcional)
                                </label>
                                <textarea
                                    value={formData.description ?? ''}
                                    onChange={e =>
                                        handleFieldChange(
                                            'description',
                                            e.target.value
                                        )
                                    }
                                    rows={3}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:opacity-60"
                                    placeholder="Descreva o propósito desta zona..."
                                    disabled={disabled}
                                />
                            </div>

                            {/* Status */}
                            <div className="flex items-center gap-6 pt-2">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={formData.enabled ?? true}
                                        onChange={e =>
                                            handleFieldChange(
                                                'enabled',
                                                e.target.checked
                                            )
                                        }
                                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 disabled:opacity-60"
                                        disabled={disabled}
                                    />
                                    <span className="text-sm font-medium text-gray-700">
                                        Habilitada
                                    </span>
                                </label>

                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={formData.active ?? true}
                                        onChange={e =>
                                            handleFieldChange(
                                                'active',
                                                e.target.checked
                                            )
                                        }
                                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 disabled:opacity-60"
                                        disabled={disabled}
                                    />
                                    <span className="text-sm font-medium text-gray-700">
                                        Ativa
                                    </span>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                {mode !== 'view' && (
                    <div className="border-top border-gray-200 px-6 py-4 bg-gray-50 flex items-center justify-end gap-3">
                        <button
                            onClick={onClose}
                            disabled={isSaving}
                            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors font-medium text-gray-700 disabled:opacity-50"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={
                                !isValidPolygon || !formData.name.trim() || isSaving
                            }
                            className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                        >
                            {isSaving ? (
                                <>
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                    Salvando...
                                </>
                            ) : (
                                <>
                                    <Save className="w-4 h-4" />
                                    {mode === 'create'
                                        ? 'Criar Zona'
                                        : 'Salvar Alterações'}
                                </>
                            )}
                        </button>
                    </div>
                )}
            </div>
        </>
    );
}
