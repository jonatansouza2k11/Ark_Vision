/**
 * ============================================================================
 * ZoneDrawer.tsx - Zone Configuration Drawer v3.0
 * ============================================================================
 * Modal/Drawer para criar e editar zonas com canvas interativo
 * 
 * Features:
 * - Canvas HTML5 para desenhar polígonos
 * - Click esquerdo: adicionar ponto
 * - Click direito: remover ponto
 * - Drag & drop de pontos
 * - Stream de vídeo como referência
 * - Formulário completo de configuração
 * - Validação em tempo real
 * - Responsivo e acessível
 * ============================================================================
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { X, Save, Trash2, RefreshCw, AlertCircle, CheckCircle2, Camera } from 'lucide-react';
import { useToast } from '../../hooks/useToast';
import { useCameras } from '../../hooks/useCameras';

import type {
    Zone,
    CreateZonePayload,
    UpdateZonePayload,
    Polygon,
    Point,
    CoordinateSystem
} from '../../types/zones.types';

import { ZoneMode } from '../../types/zones.types';

import {
    DEFAULT_ZONE_VALUES,
    ZONE_MODE_COLORS,
    ZONE_MODE_LABELS,
    ZONE_MODE_DESCRIPTIONS,
    ZONE_MODE_FIELDS
} from '../../types/zones.types';

import ClassSelector from './ClassSelector';

// ============================================================================
// TYPES
// ============================================================================

interface ZoneDrawerProps {
    isOpen: boolean;
    mode: 'create' | 'edit' | 'view';
    zone?: Zone | null;
    onClose: () => void;
    onSave: (data: CreateZonePayload | UpdateZonePayload, zoneId?: number) => Promise<void>;
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
// COMPONENT
// ============================================================================

export default function ZoneDrawer({
    isOpen,
    mode,
    zone,
    onClose,
    onSave,
    cameraId,
}: ZoneDrawerProps) {

    // ==========================================================================
    // STATE
    // ==========================================================================

    const [formData, setFormData] = useState<CreateZonePayload>({
        name: '',
        mode: 'GENERIC' as ZoneMode,
        points: [],
        ...DEFAULT_ZONE_VALUES,
        metadata: {}
    });

    const { cameras, loading: camerasLoading } = useCameras();
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

    const canvasRef = useRef<HTMLCanvasElement>(null);
    const imgRef = useRef<HTMLImageElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const { error: showError, warning } = useToast();

    // ==========================================================================
    // CANVAS DIMENSIONS
    // ==========================================================================

    const CANVAS_WIDTH = 960;
    const CANVAS_HEIGHT = 540;
    const POINT_RADIUS = 6;
    const HOVER_RADIUS = 8;

    /**
     * Verifica se um campo deve ser exibido para o modo atual
     */
    //const shouldShowField = (field: keyof typeof ZONE_MODE_FIELDS['occupancy']): boolean => {
    //    const config = ZONE_MODE_FIELDS[formData.mode];
    //    if (!config) return true;  // Default: mostrar tudo
    //    return config[field];
    //};

    /**
     * Verifica se um campo deve ser exibido para o modo atual
     */
    const shouldShowField = (field: 'threshold_empty' | 'threshold_full' | 'timeout_empty' | 'timeout_full' | 'email_cooldown' | 'capacity'): boolean => {
        const config = ZONE_MODE_FIELDS[formData.mode];
       if (!config) return true;  // Default: mostrar tudo
      return config[field];
    };
    

// ==========================================================================
// EFFECTS
// ==========================================================================

    /**
     * Carrega dados da zona quando em modo edit ou view
     */
    useEffect(() => {
        if ((mode === 'edit' || mode === 'view') && zone) {
            setIsLoadingZone(true);

            // ✅ v3.9: Extrai campos do metadata para popular formulário
            const metadata = zone.metadata || {};

            setFormData({
                name: zone.name,
                mode: zone.mode,
                points: zone.points,
                camera_id: zone.camera_id,
                empty_timeout: zone.empty_timeout,
                full_timeout: zone.full_timeout,
                empty_threshold: zone.empty_threshold,
                full_threshold: zone.full_threshold,
                max_out_time: zone.max_out_time,
                email_cooldown: zone.email_cooldown,
                coordinate_system: zone.coordinate_system,
                enabled: zone.enabled,
                active: zone.active,
                description: zone.description,
                color: zone.color,
                tags: zone.tags,

                // ✅ v3.9: Reconstrói metadata com valores do banco OU defaults
                metadata: {
                    // Campos do modo counting
                    count_direction: metadata.count_direction || 'both',
                    reset_interval: metadata.reset_interval || 'never',
                    alert_enabled: metadata.alert_enabled ?? false,
                    alert_threshold: metadata.alert_threshold,
                    count_in: metadata.count_in ?? 0,
                    count_out: metadata.count_out ?? 0,

                    // ✅ NOVO: Percentual mínimo da bbox dentro da zona (0.0–1.0)
                    intersection_threshold:
                        metadata.intersection_threshold ?? 0.7,

                    // Campos do modo capacity
                    max_capacity: metadata.max_capacity,
                    alert_percentage: metadata.alert_percentage,

                    // Outros campos que possam existir
                    ...metadata
                }
            });

            // Converte pontos normalizados para canvas
            const canvasPoints = zone.points.map(([x, y]) => ({
                x: x * CANVAS_WIDTH,
                y: y * CANVAS_HEIGHT
            }));
            setCanvasPoints(canvasPoints);

            // ✅ Carregar snapshot se existir
            if (zone.snapshot_path) {
                const snapshotPath = zone.snapshot_path;

                const loadSnapshot = async () => {
                    try {
                        const filename = snapshotPath.split('/').pop();

                        if (filename) {
                            const response = await fetch(
                                `http://localhost:8000/api/v1/zones/snapshots/${filename}`,
                                {
                                    headers: {
                                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                                    }
                                }
                            );

                            if (response.ok) {
                                const blob = await response.blob();
                                const url = URL.createObjectURL(blob);
                                setSnapshotUrl(url);
                            } else {
                                console.warn('⚠️ Snapshot não encontrado (404)');
                            }
                        }
                    } catch (err) {
                        console.warn('⚠️ Erro ao carregar snapshot:', err);
                    }
                };

                loadSnapshot();
            }

            // ✅ v3.9: Marca load como completo após um tick
            setTimeout(() => {
                setIsLoadingZone(false);
            }, 0);

        } else {
            // Reset para modo create
            setIsLoadingZone(false);
            setFormData({
                name: '',
                mode: 'GENERIC' as ZoneMode,
                points: [],
                ...DEFAULT_ZONE_VALUES
            });
            setCanvasPoints([]);
        }
    }, [mode, zone, isOpen]);
    



    // ============================================================================
    // ✅ v3.9: Normaliza campos E metadata ao mudar modo (COM PROTEÇÃO DE LOAD)
    // ============================================================================
    useEffect(() => {
        // ✅ v3.9: Não normaliza enquanto está carregando zona inicial
        if (isLoadingZone) {
            return;
        }

        // ✅ v3.9: Não normaliza em modo edit/view (preserva valores do banco)
        if (mode === 'edit' || mode === 'view') {
            return;
        }

        if (!formData.mode) return;

        const config = ZONE_MODE_FIELDS[formData.mode];
        if (!config) return;


        setFormData(prev => {
            const updated = { ...prev };

            // ========================================================================
            // 1️⃣ Remove campos não utilizados (thresholds/timeouts)
            // ========================================================================

            // Threshold Empty
            if (!config.threshold_empty) {
                updated.empty_threshold = undefined;
            } else if (updated.empty_threshold === undefined || updated.empty_threshold === 0) {
                updated.empty_threshold = 0;  // 0 é válido para empty
            }

            // Threshold Full
            if (!config.threshold_full) {
                updated.full_threshold = undefined;
            } else if (updated.full_threshold === undefined || updated.full_threshold === 0) {
                updated.full_threshold = 1;  // Backend exige >= 1
            }

            // Timeout Empty
            if (!config.timeout_empty) {
                updated.empty_timeout = undefined;
            }

            // Timeout Full
            if (!config.timeout_full) {
                updated.full_timeout = undefined;
            }

            // Email Cooldown
            if (!config.email_cooldown) {
                updated.email_cooldown = undefined;
            }
            // ========================================================================
            // 2️⃣ Normaliza metadata por modo (PRESERVANDO DADOS EXISTENTES)
            // ========================================================================

            if (formData.mode === 'capacity') {
                // ✅ MODO CAPACITY: Garante estrutura completa
                updated.metadata = {
                    ...updated.metadata,  // ✅ Preserva outros campos
                    max_capacity: updated.metadata?.max_capacity ?? 50,
                    alert_percentage: updated.metadata?.alert_percentage ?? 90,
                };
            } else if (formData.mode === ZoneMode.COUNTING) {
                // MODO COUNTING – preserva configurações de contagem + alerta
                updated.metadata = {
                    ...updated.metadata,
                    // Direção e reset
                    count_direction: updated.metadata?.count_direction ?? 'both',
                    reset_interval: updated.metadata?.reset_interval ?? 'daily',

                    // Alerta por limite de contagem
                    alert_enabled: updated.metadata?.alert_enabled ?? false,
                    alert_threshold: updated.metadata?.alert_threshold,

                    // Contadores atuais
                    count_in: updated.metadata?.count_in ?? 0,
                    count_out: updated.metadata?.count_out ?? 0,

                    // Tempo de confirmação (usado pelo backend como confirmation_time)
                    confirmation_time: updated.metadata?.confirmation_time ?? 0,

                    // Percentual mínimo da bbox dentro da zona (interseção)
                    intersection_threshold: updated.metadata?.intersection_threshold ?? 0.7,

                    // detectionclasses sempre preservado
                    detection_classes: updated.metadata?.detection_classes ?? 0,
                };
            } else {
                // OUTROS MODOS – preserva apenas detectionclasses, limpa o resto
                updated.metadata = {
                    detection_classes: updated.metadata?.detection_classes ?? 0,
                };
            }

            return updated;
        });
    }, [formData.mode, isLoadingZone, mode]);  
    
    


    /**
     * Valida polígono quando pontos mudam
     */
    useEffect(() => {
        if (mode === 'edit') {
            if (canvasPoints.length >= 3) {
                setIsValidPolygon(true);
                setValidationMessage(`Polígono válido com ${canvasPoints.length} pontos`);
            } else if (canvasPoints.length > 0) {
                setIsValidPolygon(false);
                setValidationMessage(`Adicione ${3 - canvasPoints.length} pontos para completar`);
            } else {
                setIsValidPolygon(false);
                setValidationMessage("Clique no canvas para adicionar pontos");
            }
        } else if (!snapshotUrl) {
            setIsValidPolygon(false);
            setValidationMessage("Capture uma foto antes de desenhar");
        } else if (canvasPoints.length >= 3) {
            setIsValidPolygon(true);
            setValidationMessage(`Polígono válido com ${canvasPoints.length} pontos`);
        } else if (canvasPoints.length > 0) {
            setIsValidPolygon(false);
            setValidationMessage(`Adicione ${3 - canvasPoints.length} pontos para completar`);
        } else {
            setIsValidPolygon(false);
            setValidationMessage("Clique no canvas para adicionar pontos");
        }
    }, [canvasPoints, snapshotUrl, mode]);



    /**
     * Renderiza canvas quando pontos mudam
     */
    useEffect(() => {
        drawCanvas();
    }, [canvasPoints, hoveredIndex, draggingIndex]);


        /**
     * Renderiza canvas quando pontos mudam
     */
    useEffect(() => {
        drawCanvas();
    }, [canvasPoints, hoveredIndex, draggingIndex]);


    /**
     * Verifica status do stream a cada 2 segundos
     */
    useEffect(() => {
        const checkStreamStatus = async () => {
            try {
                const response = await fetch('http://localhost:8000/api/v1/stream/status', {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    }
                });
                const data = await response.json();
                setStreamActive(data.stream_active || false);
            } catch (error) {
                setStreamActive(false);
            }
        };

        if (isOpen) {
            checkStreamStatus();
            const interval = setInterval(checkStreamStatus, 2000);
            return () => clearInterval(interval);
        }
    }, [isOpen]);


    // ==========================================================================
    // CANVAS DRAWING
    // ==========================================================================

    /**
     * Desenha o canvas com polígono e pontos
     */
    const drawCanvas = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Limpa canvas
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        // Se não há pontos, para aqui
        if (canvasPoints.length === 0) return;

        // Desenha polígono
        if (canvasPoints.length >= 2) {
            ctx.beginPath();
            ctx.moveTo(canvasPoints[0].x, canvasPoints[0].y);

            for (let i = 1; i < canvasPoints.length; i++) {
                ctx.lineTo(canvasPoints[i].x, canvasPoints[i].y);
            }

            // Fecha polígono se tiver 3+ pontos
            if (canvasPoints.length >= 3) {
                ctx.closePath();
                ctx.fillStyle = `${formData.color || ZONE_MODE_COLORS[formData.mode]}33`; // 20% opacity
                ctx.fill();
            }

            ctx.strokeStyle = formData.color || ZONE_MODE_COLORS[formData.mode];
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // Desenha pontos
        canvasPoints.forEach((point, index) => {
            const isHovered = index === hoveredIndex;
            const isDragging = index === draggingIndex;
            const radius = isHovered || isDragging ? HOVER_RADIUS : POINT_RADIUS;

            ctx.beginPath();
            ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);

            // Cor do ponto
            if (isDragging) {
                ctx.fillStyle = '#EF4444'; // red-500
            } else if (isHovered) {
                ctx.fillStyle = '#F59E0B'; // amber-500
            } else {
                ctx.fillStyle = '#1E40AF'; // blue-800
            }

            ctx.fill();
            ctx.strokeStyle = '#FFFFFF';
            ctx.lineWidth = 2;
            ctx.stroke();

            // Número do ponto
            ctx.fillStyle = '#FFFFFF';
            ctx.font = 'bold 12px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText((index + 1).toString(), point.x, point.y);
        });
    }, [canvasPoints, hoveredIndex, draggingIndex, formData.color, formData.mode]);

    // ==========================================================================
    // CANVAS EVENT HANDLERS
    // ==========================================================================

    /**
     * Obtém coordenadas do mouse relativas ao canvas
     */
    const getCanvasCoordinates = (e: React.MouseEvent<HTMLCanvasElement>): Point => {
        const canvas = canvasRef.current;
        if (!canvas) return [0, 0];

        const rect = canvas.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * CANVAS_WIDTH;
        const y = ((e.clientY - rect.top) / rect.height) * CANVAS_HEIGHT;

        return [x, y];
    };

    /**
     * Encontra índice do ponto próximo ao mouse
     */
    const findNearestPoint = (x: number, y: number): number | null => {
        const threshold = HOVER_RADIUS + 2;

        for (let i = 0; i < canvasPoints.length; i++) {
            const dx = canvasPoints[i].x - x;
            const dy = canvasPoints[i].y - y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance <= threshold) {
                return i;
            }
        }

        return null;
    };

    /**
     * Click esquerdo: adiciona ponto ou inicia drag
     */
    const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const [x, y] = getCanvasCoordinates(e);
        const nearestIndex = findNearestPoint(x, y);

        // Se clicou em ponto existente, não adiciona novo
        if (nearestIndex !== null) return;

        // Adiciona novo ponto
        setCanvasPoints(prev => [...prev, { x, y }]);
    };

    /**
     * Click direito: remove ponto
     */
    const handleCanvasContextMenu = (e: React.MouseEvent<HTMLCanvasElement>) => {
        e.preventDefault();

        const [x, y] = getCanvasCoordinates(e);
        const nearestIndex = findNearestPoint(x, y);

        if (nearestIndex !== null) {
            setCanvasPoints(prev => prev.filter((_, i) => i !== nearestIndex));
            warning('Ponto removido');
        }
    };

    /**
     * Mouse move: hover e drag
     */
    const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const [x, y] = getCanvasCoordinates(e);

        // Se está arrastando
        if (draggingIndex !== null) {
            setCanvasPoints(prev => prev.map((point, i) =>
                i === draggingIndex ? { x, y } : point
            ));
            return;
        }

        // Detecta hover
        const nearestIndex = findNearestPoint(x, y);
        setHoveredIndex(nearestIndex);
    };

    /**
     * Mouse down: inicia drag
     */
    const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const [x, y] = getCanvasCoordinates(e);
        const nearestIndex = findNearestPoint(x, y);

        if (nearestIndex !== null) {
            setDraggingIndex(nearestIndex);
        }
    };

    /**
     * Mouse up: termina drag
     */
    const handleCanvasMouseUp = () => {
        setDraggingIndex(null);
    };

    /**
     * Mouse leave: limpa estados
     */
    const handleCanvasMouseLeave = () => {
        setHoveredIndex(null);
        setDraggingIndex(null);
    };


    // ==========================================================================
    // SNAPSHOT HANDLER
    // ==========================================================================

    /**
     * Captura snapshot do stream
     */
    const handleCaptureSnapshot = async () => {
        setCapturingSnapshot(true);
        try {
            // ✅ Usa cameraId se disponível, senão fallback para endpoint global
            const snapshotUrl = cameraId
                ? `http://localhost:8000/api/v1/stream/snapshot/${cameraId}`
                : 'http://localhost:8000/api/v1/stream/snapshot';

            const response = await fetch(snapshotUrl, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });

            if (!response.ok) {
                throw new Error('Falha ao capturar snapshot');
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);

            if (snapshotUrl) {
                URL.revokeObjectURL(snapshotUrl);
            }

            setSnapshotUrl(url);

            // ✅ PARAR stream para economizar memória (não precisa mais dele)
            try {
                await fetch('http://localhost:8000/api/v1/stream/stop', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    }
                });
                console.log('✅ Stream parado para economizar memória');
            } catch (stopError) {
                console.warn('Não foi possível parar stream:', stopError);
            }

        } catch (error) {
            console.error('Erro ao capturar snapshot:', error);
            showError && showError('Erro ao capturar foto do stream');
        } finally {
            setCapturingSnapshot(false);
        }
    };
    



    // ==========================================================================
    // FORM HANDLERS
    // ==========================================================================

    /**
     * Atualiza campo do formulário
     */
    const handleFieldChange = (field: keyof CreateZonePayload, value: any) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };


    /**
     * Limpa todos os pontos
     */
    const handleClearPoints = () => {
        setCanvasPoints([]);
        warning('Pontos limpos');
    };


    /**
     * Salva zona
     */
    const handleSave = async () => {
        // Validações
        if (!formData.name.trim()) {
            showError('Nome da zona é obrigatório');
            return;
        }

        if (canvasPoints.length < 3) {
            showError('Adicione pelo menos 3 pontos para criar o polígono');
            return;
        }

        // Converte pontos do canvas para normalizados (0-1)
        const normalized_points: Polygon = canvasPoints.map((p) => [
            p.x / CANVAS_WIDTH,
            p.y / CANVAS_HEIGHT,
        ]);

        setIsSaving(true);

        try {
            let snapshot_base64: string | undefined = undefined;

            if (snapshotUrl && mode === 'create') {
                try {
                    const response = await fetch(snapshotUrl);
                    const blob = await response.blob();
                    const reader = new FileReader();

                    snapshot_base64 = await new Promise<string>((resolve) => {
                        reader.onloadend = () => {
                            const base64 = (reader.result as string).split(',')[1];
                            resolve(base64);
                        };
                        reader.readAsDataURL(blob);
                    });
                } catch (err) {
                    console.warn('⚠️ Erro ao converter snapshot:', err);
                }
            }

            // Config do modo atual
            const config = ZONE_MODE_FIELDS[formData.mode];

            const payload: any = {
                ...formData,
                // nomes em snake_case, alinhados com backend
                points: normalized_points,
                coordinate_system: 'normalized' as CoordinateSystem,
                snapshot_base64,
                // garante metadata completo para COUNTING
                metadata: {
                    ...(formData.metadata || {}),
                    ...(formData.mode === ZoneMode.COUNTING
                        ? {
                            // percentual mínimo da bbox dentro da zona
                            intersection_threshold:
                                formData.metadata?.intersection_threshold ?? 0.7,
                            // tempo de confirmação em segundos
                            confirmation_time:
                                formData.metadata?.confirmation_time ?? 0,
                        }
                        : {}),
                },
            };

            // Remove campos não utilizados pelo modo atual
            if (config) {
                if (!config.threshold_empty) delete payload.empty_threshold;
                if (!config.threshold_full) delete payload.full_threshold;
                if (!config.timeout_empty) delete payload.empty_timeout;
                if (!config.timeout_full) delete payload.full_timeout;
                if (!config.email_cooldown) delete payload.email_cooldown;

                if (!config.capacity && payload.metadata) {
                    const { max_capacity, alert_percentage, ...rest } = payload.metadata;
                    payload.metadata =
                        Object.keys(rest).length > 0 ? rest : undefined;
                }
            }

            // Garante thresholds válidos para o backend
            if (payload.full_threshold !== undefined && payload.full_threshold < 1) {
                payload.full_threshold = 1;
            }
            if (payload.empty_threshold !== undefined && payload.empty_threshold < 0) {
                payload.empty_threshold = 0;
            }

            // Remove undefined/null
            Object.keys(payload).forEach((key) => {
                if (payload[key] === undefined || payload[key] === null) {
                    delete payload[key];
                }
            });

            await onSave(payload, zone?.id);

            // Reset e fecha
            setCanvasPoints([]);
            onClose();
        } catch (err) {
            console.error('Erro ao salvar zona:', err);
        } finally {
            setIsSaving(false);
        }
    };
      


    // ==========================================================================
    // RENDER
    // ==========================================================================

    if (!isOpen) return null;

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
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-blue-700">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
                            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                            </svg>
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">
                                {mode === 'create' ? 'Nova Zona' : mode === 'edit' ? 'Editar Zona' : 'Visualizar Zona'}
                            </h2>
                            <p className="text-sm text-blue-100">
                                {mode === 'create' ? 'Desenhe o polígono no vídeo' : `ID: ${zone?.id}`}
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
                        <div className="bg-gray-50 rounded-xl p-4 border-2 border-gray-200">
                            <div className="flex items-center justify-between mb-3">
                                <div>
                                    <h3 className="font-semibold text-gray-900">Desenhar Zona</h3>
                                    <p className="text-sm text-gray-600">
                                        <span className="font-medium">Botão esquerdo:</span> adicionar ponto •
                                        <span className="font-medium ml-2">Botão direito:</span> remover ponto
                                    </p>
                                </div>

                                <div className="flex items-center gap-2">

                                    {/* Botão Capturar Foto */}
                                    <button
                                        onClick={handleCaptureSnapshot}
                                        disabled={!streamActive || capturingSnapshot || mode === 'view'}
                                        className="flex items-center gap-2 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                                        title={!streamActive ? 'Inicie o stream primeiro' : 'Capturar foto'}
                                    >
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                                        </svg>
                                        {capturingSnapshot ? 'Capturando...' : 'Capturar'}
                                    </button>

                                    {/* Badge de aviso quando stream está parado */}
                                    {!streamActive && (
                                        <div className="text-xs text-amber-700 bg-amber-50 px-3 py-1 rounded-lg border border-amber-200 flex items-center gap-1">
                                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                            </svg>
                                            <span>Stream parado</span>
                                        </div>
                                    )}

                                    {/* Botão Limpar */}
                                    <button
                                        onClick={handleClearPoints}
                                        disabled={canvasPoints.length === 0}
                                        className="flex items-center gap-2 px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                        Limpar
                                    </button>
                                </div>
                            </div>


                            {/* Canvas Container */}
                            <div
                                ref={containerRef}
                                className="relative bg-black rounded-lg overflow-hidden border-2 border-gray-300"
                                style={{ aspectRatio: `${CANVAS_WIDTH}/${CANVAS_HEIGHT}` }}
                            >
                                {/* ✅ Background com Snapshot ou Placeholder */}
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
                                        <div className="text-gray-400 text-sm">Editando polígono da zona</div>
                                    </div>
                                ) : (
                                    <div className="absolute inset-0 w-full h-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center pointer-events-none">
                                        <div className="text-center text-gray-400">
                                            <svg className="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                                            </svg>
                                            <p className="text-sm font-medium mb-2">Nenhuma foto capturada</p>
                                            <p className="text-xs text-gray-500">
                                                Clique no botão "Capturar" acima
                                            </p>
                                        </div>
                                    </div>
                                )}

                                {/* Canvas Overlay */}
                                <canvas
                                    ref={canvasRef}
                                    width={CANVAS_WIDTH}
                                    height={CANVAS_HEIGHT}
                                    onClick={mode !== 'view' && (snapshotUrl || mode === 'edit') ? handleCanvasClick : undefined}
                                    onContextMenu={mode !== 'view' && (snapshotUrl || mode === 'edit') ? handleCanvasContextMenu : undefined}
                                    onMouseMove={mode !== 'view' && (snapshotUrl || mode === 'edit') ? handleCanvasMouseMove : undefined}
                                    onMouseDown={mode !== 'view' && (snapshotUrl || mode === 'edit') ? handleCanvasMouseDown : undefined}
                                    onMouseUp={mode !== 'view' && (snapshotUrl || mode === 'edit') ? handleCanvasMouseUp : undefined}
                                    onMouseLeave={mode !== 'view' && (snapshotUrl || mode === 'edit') ? handleCanvasMouseLeave : undefined}
                                    className={`absolute inset-0 w-full h-full ${mode === 'view' ? 'cursor-default' :
                                            (snapshotUrl || mode === 'edit') ? 'cursor-crosshair' : 'cursor-not-allowed'
                                        }`}
                                    style={{
                                        imageRendering: 'crisp-edges',
                                        pointerEvents: mode === 'view' ? 'none' : (snapshotUrl || mode === 'edit' ? 'auto' : 'none')
                                    }}
                                />

                            </div>


                            {/* Validation Status */}
                            <div className={`mt-3 flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${isValidPolygon
                                    ? 'bg-green-50 text-green-700'
                                    : 'bg-amber-50 text-amber-700'
                                }`}>
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
                            <h3 className="font-semibold text-gray-900 text-lg">Configurações da Zona</h3>

                            {/* Nome */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Nome da Zona
                                </label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => handleFieldChange('name', e.target.value)}
                                    placeholder="Ex: Entrada Principal"
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    disabled={mode === 'view'}
                                />
                            </div>

                            {/* Seletor de Classes COCO (ACIMA do modo) */}
                            <ClassSelector
                                selectedClasses={formData.metadata?.detection_classes || [0]}
                                onChange={(classes) => {
                                    setFormData(prev => ({
                                        ...prev,
                                        metadata: {
                                            ...(prev.metadata || {}),
                                            detection_classes: classes
                                        }
                                    }));
                                }}
                                disabled={mode === 'view'}
                                showSearch={true}
                                maxHeight="250px"
                            />

                            {/* Modos de operacao */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Modo de Operação
                                </label>
                                <select
                                    value={formData.mode}
                                    onChange={(e) => handleFieldChange('mode', e.target.value as ZoneMode)}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    disabled={mode === 'view'}
                                >
                                    {Object.entries(ZONE_MODE_LABELS).map(([value, label]) => (
                                        <option key={value} value={value}>
                                            {label}
                                        </option>
                                    ))}
                                </select>
                                <p className="mt-1 text-sm text-gray-600">
                                    {ZONE_MODE_DESCRIPTIONS[formData.mode]}
                                </p>
                            </div>

                            {/* Câmera Associada */}
                            <div>
                                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                                    <Camera className="w-4 h-4" />
                                    Câmera Associada
                                </label>
                                <select
                                    value={formData.camera_id || ''}
                                    onChange={(e) => handleFieldChange('camera_id', e.target.value ? parseInt(e.target.value) : null)}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    disabled={mode === 'view' || camerasLoading}
                                >
                                    <option value="">Nenhuma</option>
                                    {cameras.map(camera => (
                                        <option key={camera.id} value={camera.id}>
                                            {camera.name} {!camera.enabled && '(Inativa)'}
                                        </option>
                                    ))}
                                </select>
                                <p className="mt-1 text-sm text-gray-600">
                                    {formData.camera_id
                                        ? 'Zona vinculada a câmera específica'
                                        : 'Não vinculada a câmera'}
                                </p>
                            </div>


                            {/* Thresholds (condicional por modo) */}
                            {(shouldShowField('threshold_empty') || shouldShowField('threshold_full')) && (
                                <div className="grid grid-cols-2 gap-4">
                                    {shouldShowField('threshold_empty') && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                Threshold Vazio
                                            </label>
                                            <input
                                                type="number"
                                                min={0}
                                                value={formData.empty_threshold || 0}
                                                onChange={(e) => handleFieldChange('empty_threshold', parseInt(e.target.value))}
                                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                disabled={mode === 'view'}
                                            />
                                            <p className="mt-1 text-xs text-gray-500">
                                                Mínimo de objetos para ser considerado vazio
                                            </p>
                                        </div>
                                    )}

                                    {shouldShowField('threshold_full') && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                {formData.mode === 'counting' ? 'Threshold Contagem'
                                                    : formData.mode === 'alert' ? 'Threshold Alerta'
                                                        : 'Threshold Cheio'}
                                            </label>
                                            <input
                                                type="number"
                                                min={(formData.empty_threshold ?? 0) + 1}
                                                value={formData.full_threshold ?? 3}
                                                onChange={(e) => {
                                                    const value = parseInt(e.target.value);
                                                    const minValue = (formData.empty_threshold ?? 0) + 1;

                                                    if (value < minValue) {
                                                        warning(`Threshold Cheio deve ser maior que ${formData.empty_threshold ?? 0}`);
                                                        return;
                                                    }

                                                    handleFieldChange('full_threshold', value);
                                                }}
                                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                disabled={mode === 'view'}
                                            />
                                            <p className="mt-1 text-xs text-gray-500">
                                                {formData.mode === 'counting' ? 'Mínimo para registrar entrada/saída'
                                                    : formData.mode === 'alert' ? 'Pessoas para disparar alerta'
                                                        : `Número de objetos para considerar cheio (mínimo: ${(formData.empty_threshold ?? 0) + 1})`}
                                            </p>
                                        </div>

                                    )}
                                </div>
                            )}


                            {/* Timeouts (condicional por modo) */}
                            {(shouldShowField('timeout_empty') || shouldShowField('timeout_full')) && (
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
                                                value={formData.empty_timeout || 5}
                                                onChange={(e) =>
                                                    handleFieldChange('empty_timeout', parseFloat(e.target.value))
                                                }
                                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                disabled={mode === 'view'}
                                            />
                                            <p className="mt-1 text-xs text-gray-500">
                                                Tempo vazio antes de alertar
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

                                            {/* 👇 AQUI é o ajuste: quando counting usa metadata.confirmation_time */}
                                            <input
                                                type="number"
                                                min={0}
                                                step={0.5}
                                                value={
                                                    formData.mode === 'counting'
                                                        ? formData.metadata?.confirmation_time ?? 0
                                                        : formData.full_timeout || 10
                                                }
                                                onChange={(e) => {
                                                    const value = parseFloat(e.target.value);
                                                    if (formData.mode === 'counting') {
                                                        setFormData((prev) => ({
                                                            ...prev,
                                                            metadata: {
                                                                ...(prev.metadata || {}),
                                                                confirmation_time: isNaN(value) ? 0 : value,
                                                            },
                                                        }));
                                                    } else {
                                                        handleFieldChange('full_timeout', value);
                                                    }
                                                }}
                                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                disabled={mode === 'view'}
                                            />

                                            <p className="mt-1 text-xs text-gray-500">
                                                {formData.mode === 'alert'
                                                    ? 'Tolerância antes de disparar alerta'
                                                    : formData.mode === 'capacity'
                                                        ? 'Tempo na capacidade antes de alertar (0 = imediato)'
                                                        : formData.mode === 'counting'
                                                            ? 'Tempo que o objeto deve permanecer para ser contado'
                                                            : 'Tempo cheio antes de alertar'}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}



                            {/* Capacidade Máxima (só para modo CAPACITY) */}
                            {shouldShowField('capacity') && (
                                <div className="bg-amber-50 border-2 border-amber-200 rounded-lg p-4">
                                    <label className="flex items-center gap-2 text-sm font-medium text-amber-900 mb-2">
                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                                        </svg>
                                        Capacidade Máxima
                                    </label>
                                    <input
                                        type="number"
                                        min={1}
                                        max={1000}
                                        value={formData.metadata?.max_capacity || 50}
                                        onChange={(e) => {
                                            const value = parseInt(e.target.value);
                                            setFormData(prev => ({
                                                ...prev,
                                                metadata: {
                                                    ...(prev.metadata || {}),
                                                    max_capacity: value
                                                }
                                            }));
                                        }}
                                        className="w-full px-4 py-2 bg-white border border-amber-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent font-bold text-lg text-amber-900"
                                        disabled={mode === 'view'}
                                        placeholder="50"
                                    />
                                    <p className="mt-2 text-sm text-amber-800 font-medium">
                                        📊 Lotação máxima: {formData.metadata?.max_capacity || 50} pessoas
                                    </p>

                                    {/* Slider para percentual de alerta (0% a 100%) */}
                                    <div className="mt-4 pt-4 border-t border-amber-300">
                                        <label className="block text-sm font-medium text-amber-900 mb-3">
                                            ⚠️ Percentual de Alerta: <span className="text-lg font-bold">{formData.metadata?.alert_percentage || 90}%</span>
                                        </label>
                                        <input
                                            type="range"
                                            min={0}
                                            max={100}
                                            step={5}
                                            value={formData.metadata?.alert_percentage || 90}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value);
                                                setFormData(prev => ({
                                                    ...prev,
                                                    metadata: {
                                                        ...(prev.metadata || {}),
                                                        alert_percentage: value
                                                    }
                                                }));
                                            }}
                                            className="w-full h-2 bg-amber-200 rounded-lg appearance-none cursor-pointer accent-amber-600 hover:accent-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                            disabled={mode === 'view'}
                                        />
                                        <div className="flex justify-between text-xs text-amber-700 mt-1">
                                            <span>0%</span>
                                            <span>25%</span>
                                            <span>50%</span>
                                            <span>75%</span>
                                            <span>100%</span>
                                        </div>
                                        <p className="mt-2 text-xs text-amber-700 bg-amber-100 px-3 py-2 rounded-lg border border-amber-300">
                                            🔔 Sistema alertará quando atingir <span className="font-bold">{formData.metadata?.alert_percentage || 90}%</span> da capacidade
                                            (<span className="font-bold">{Math.floor(((formData.metadata?.max_capacity || 50) * (formData.metadata?.alert_percentage || 90)) / 100)}</span> pessoas)
                                        </p>
                                    </div>
                                </div>
                            )}


                            {/* COUNTING MODE - Direção, Reset e Alertas */}
                            {formData.mode === 'counting' && (
                                <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 space-y-4">
                                    <div className="flex items-center gap-2 mb-3">
                                        <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                        </svg>
                                        <h4 className="text-sm font-medium text-blue-900">
                                            Configurações de Contagem
                                        </h4>
                                    </div>


                                    {/* Direção de Contagem */}
                                    <div>
                                        <label className="block text-sm font-medium text-blue-900 mb-3">
                                            📍 Direção de Contagem
                                        </label>


                                        <div className="space-y-2">
                                            <label className="flex items-center gap-3 p-3 border-2 border-blue-200 rounded-lg cursor-pointer hover:bg-blue-100 transition-colors">
                                                <input
                                                    type="radio"
                                                    name="count_direction"
                                                    value="in"
                                                    checked={formData.metadata?.count_direction === 'in'}
                                                    onChange={() => {
                                                        setFormData(prev => ({
                                                            ...prev,
                                                            metadata: {
                                                                ...prev.metadata,
                                                                count_direction: 'in',
                                                            }
                                                        }));
                                                    }}
                                                    disabled={mode === 'view'}
                                                    className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                                                />
                                                <div className="flex-1">
                                                    <span className="text-sm font-medium text-blue-900">
                                                        🔽 Apenas Entradas
                                                    </span>
                                                    <p className="text-xs text-blue-700 mt-0.5">
                                                        Conta apenas objetos entrando na zona
                                                    </p>
                                                </div>
                                            </label>


                                            <label className="flex items-center gap-3 p-3 border-2 border-blue-200 rounded-lg cursor-pointer hover:bg-blue-100 transition-colors">
                                                <input
                                                    type="radio"
                                                    name="count_direction"
                                                    value="out"
                                                    checked={formData.metadata?.count_direction === 'out'}
                                                    onChange={() => {
                                                        setFormData(prev => ({
                                                            ...prev,
                                                            metadata: {
                                                                ...prev.metadata,
                                                                count_direction: 'out',
                                                            }
                                                        }));
                                                    }}
                                                    disabled={mode === 'view'}
                                                    className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                                                />
                                                <div className="flex-1">
                                                    <span className="text-sm font-medium text-blue-900">
                                                        🔼 Apenas Saídas
                                                    </span>
                                                    <p className="text-xs text-blue-700 mt-0.5">
                                                        Conta apenas objetos saindo da zona
                                                    </p>
                                                </div>
                                            </label>


                                            <label className="flex items-center gap-3 p-3 border-2 border-blue-300 rounded-lg cursor-pointer hover:bg-blue-100 transition-colors bg-white">
                                                <input
                                                    type="radio"
                                                    name="count_direction"
                                                    value="both"
                                                    checked={formData.metadata?.count_direction === 'both' || !formData.metadata?.count_direction}
                                                    onChange={() => {
                                                        setFormData(prev => ({
                                                            ...prev,
                                                            metadata: {
                                                                ...prev.metadata,
                                                                count_direction: 'both',
                                                            }
                                                        }));
                                                    }}
                                                    disabled={mode === 'view'}
                                                    className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                                                />
                                                <div className="flex-1">
                                                    <span className="text-sm font-medium text-blue-900">
                                                        ↕️ Ambas Direções
                                                    </span>
                                                    <p className="text-xs text-blue-700 mt-0.5">
                                                        Contadores separados IN/OUT (recomendado)
                                                    </p>
                                                </div>
                                            </label>
                                        </div>
                                    </div>


                                    {/* Período de Reset */}
                                    <div className="pt-3 border-t border-blue-300">
                                        <label className="block text-sm font-medium text-blue-900 mb-2">
                                            🔄 Período de Reset do Contador
                                        </label>
                                        <select
                                            value={formData.metadata?.reset_interval || 'daily'}
                                            onChange={(e) => {
                                                setFormData(prev => ({
                                                    ...prev,
                                                    metadata: {
                                                        ...prev.metadata,
                                                        reset_interval: e.target.value
                                                    }
                                                }));
                                            }}
                                            disabled={mode === 'view'}
                                            className="w-full px-4 py-2 bg-white border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        >
                                            <option value="none">Nunca (acumula sempre)</option>
                                            <option value="hourly">A cada 1 hora</option>
                                            <option value="daily">Diariamente às 00:00</option>
                                            <option value="weekly">Semanalmente (Segunda 00:00)</option>
                                            <option value="monthly">Mensalmente (dia 1 às 00:00)</option>
                                        </select>
                                        <p className="mt-1 text-xs text-blue-700">
                                            Zera automaticamente para gerar relatórios periódicos
                                        </p>
                                    </div>


                                    {/* Percentual mínimo da bbox dentro da zona */}
                                    <div className="pt-3 border-t border-blue-300">
                                        <label className="block text-sm font-medium text-blue-900 mb-2">
                                            📏 Percentual mínimo do objeto dentro da zona
                                        </label>
                                        <input
                                            type="range"
                                            min={30}
                                            max={90}
                                            step={5}
                                            value={(formData.metadata?.intersection_threshold ?? 0.7) * 100}
                                            onChange={(e) => {
                                                const value = Number(e.target.value) / 100;
                                                setFormData(prev => ({
                                                    ...prev,
                                                    metadata: {
                                                        ...prev.metadata,
                                                        intersection_threshold: value,
                                                    },
                                                }));
                                            }}
                                            disabled={mode === 'view'}
                                            className="w-full"
                                        />
                                        <p className="mt-1 text-xs text-blue-700">
                                            A zona só contará entrada/saída quando pelo menos{' '}
                                            {((formData.metadata?.intersection_threshold ?? 0.7) * 100).toFixed(0)}%
                                            da bbox estiver dentro do polígono.
                                        </p>
                                    </div>


                                    {/* Alerta por Limite */}
                                    <div className="pt-3 border-t border-blue-300">
                                        <label className="flex items-center gap-2 mb-3 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={formData.metadata?.alert_enabled || false}
                                                onChange={(e) => {
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        metadata: {
                                                            ...prev.metadata,
                                                            alert_enabled: e.target.checked
                                                        }
                                                    }));
                                                }}
                                                disabled={mode === 'view'}
                                                className="w-4 h-4 text-blue-600 border-blue-300 rounded focus:ring-blue-500"
                                            />
                                            <span className="text-sm font-medium text-blue-900">
                                                🔔 Alerta por Limite de Contagem
                                            </span>
                                        </label>


                                        {formData.metadata?.alert_enabled && (
                                            <div className="ml-6">
                                                <label className="block text-sm font-medium text-blue-900 mb-2">
                                                    Disparar alerta quando atingir
                                                </label>
                                                <input
                                                    type="number"
                                                    min={1}
                                                    max={10000}
                                                    value={formData.metadata?.alert_threshold || 100}
                                                    onChange={(e) => {
                                                        const value = parseInt(e.target.value);
                                                        setFormData(prev => ({
                                                            ...prev,
                                                            metadata: {
                                                                ...prev.metadata,
                                                                alert_threshold: value
                                                            }
                                                        }));
                                                    }}
                                                    disabled={mode === 'view'}
                                                    className="w-full px-4 py-2 bg-white border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-bold text-lg text-blue-900"
                                                    placeholder="100"
                                                />
                                                <p className="mt-1 text-xs text-blue-700 bg-blue-100 px-3 py-2 rounded-lg border border-blue-300">
                                                    Sistema enviará alerta por email quando contador atingir{' '}
                                                    <span className="font-bold">{formData.metadata?.alert_threshold || 100}</span> eventos
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}



                            {/* Email Cooldown (alguns modos) - ✅ v3.4: Agora em MINUTOS */}
                            {shouldShowField('email_cooldown') && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        {formData.mode === 'capacity' ? '⏱️ Cooldown de Alerta de Lotação (min)' : 'Cooldown de Email (min)'}
                                    </label>
                                    <input
                                        type="number"
                                        min={1}
                                        max={60}
                                        step={1}
                                        value={Math.round((formData.email_cooldown || 600) / 60)}
                                        onChange={(e) => {
                                            // Converte minutos para segundos antes de salvar
                                            const minutes = parseFloat(e.target.value);
                                            handleFieldChange('email_cooldown', minutes * 60);
                                        }}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        disabled={mode === 'view'}
                                        placeholder="10"
                                    />
                                    <p className="mt-1 text-xs text-gray-500">
                                        {formData.mode === 'capacity'
                                            ? 'Tempo mínimo entre alertas de lotação crítica por email (padrão: 10 minutos)'
                                            : 'Tempo mínimo entre alertas por email (padrão: 10 minutos)'
                                        }
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
                                        value={formData.color || ZONE_MODE_COLORS[formData.mode]}
                                        onChange={(e) => handleFieldChange('color', e.target.value)}
                                        className="w-16 h-10 rounded border border-gray-300 cursor-pointer"
                                        disabled={mode === 'view'}
                                    />
                                    <input
                                        type="text"
                                        value={formData.color || ZONE_MODE_COLORS[formData.mode]}
                                        onChange={(e) => handleFieldChange('color', e.target.value)}
                                        placeholder="#3B82F6"
                                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                                        disabled={mode === 'view'}
                                    />
                                </div>
                            </div>

                            {/* Descrição */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Descrição (opcional)
                                </label>
                                <textarea
                                    value={formData.description || ''}
                                    onChange={(e) => handleFieldChange('description', e.target.value)}
                                    placeholder="Descreva o propósito desta zona..."
                                    rows={3}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                                    disabled={mode === 'view'}
                                />
                            </div>

                            {/* Status Toggles */}
                            <div className="flex items-center gap-6 pt-2">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={formData.enabled}
                                        onChange={(e) => handleFieldChange('enabled', e.target.checked)}
                                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                        disabled={mode === 'view'}
                                    />
                                    <span className="text-sm font-medium text-gray-700">Habilitada</span>
                                </label>

                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={formData.active}
                                        onChange={(e) => handleFieldChange('active', e.target.checked)}
                                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                        disabled={mode === 'view'}
                                    />
                                    <span className="text-sm font-medium text-gray-700">Ativa</span>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                {mode !== 'view' && (
                    <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 flex items-center justify-end gap-3">
                        <button
                            onClick={onClose}
                            disabled={isSaving}
                            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors font-medium text-gray-700 disabled:opacity-50"
                        >
                            Cancelar
                        </button>

                        <button
                            onClick={handleSave}
                            disabled={!isValidPolygon || !formData.name.trim() || isSaving}
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
                                    {mode === 'create' ? 'Criar Zona' : 'Salvar Alterações'}
                                </>
                            )}
                        </button>
                    </div>
                )}
            </div>
        </>
    );
}
