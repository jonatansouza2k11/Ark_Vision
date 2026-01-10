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
import { X, Save, Trash2, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useToast } from '../../hooks/useToast';
import type {
    Zone,
    CreateZonePayload,
    UpdateZonePayload,
    Polygon,
    Point,
    ZoneMode,
    CoordinateSystem
} from '../../types/zones.types';
import {
    DEFAULT_ZONE_VALUES,
    ZONE_MODE_COLORS,
    ZONE_MODE_LABELS,
    ZONE_MODE_DESCRIPTIONS
} from '../../types/zones.types';

// ============================================================================
// TYPES
// ============================================================================

interface ZoneDrawerProps {
    isOpen: boolean;
    mode: 'create' | 'edit' | 'view';
    zone?: Zone | null;
    onClose: () => void;
    onSave: (data: CreateZonePayload | UpdateZonePayload, zoneId?: number) => Promise<void>;
    streamUrl?: string; // URL do stream de vídeo como referência
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
    streamUrl = 'http://localhost:8000/video_feed'
}: ZoneDrawerProps) {
    // ==========================================================================
    // STATE
    // ==========================================================================

    const [formData, setFormData] = useState<CreateZonePayload>({
        name: '',
        mode: 'GENERIC' as ZoneMode,
        points: [],
        ...DEFAULT_ZONE_VALUES
    });

    const [canvasPoints, setCanvasPoints] = useState<CanvasPoint[]>([]);
    const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
    const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
    const [isValidPolygon, setIsValidPolygon] = useState(false);
    const [validationMessage, setValidationMessage] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    const canvasRef = useRef<HTMLCanvasElement>(null);
    const imgRef = useRef<HTMLImageElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const { success, error: showError, warning } = useToast();

    // ==========================================================================
    // CANVAS DIMENSIONS
    // ==========================================================================

    const CANVAS_WIDTH = 640;
    const CANVAS_HEIGHT = 480;
    const POINT_RADIUS = 6;
    const HOVER_RADIUS = 8;

    // ==========================================================================
    // EFFECTS
    // ==========================================================================

    /**
     * Carrega dados da zona quando em modo edit
     */
    useEffect(() => {
        if (mode === 'edit' && zone) {
            setFormData({
                name: zone.name,
                mode: zone.mode,
                points: zone.points,
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
                tags: zone.tags
            });

            // Converte pontos normalizados para canvas
            const canvasPoints = zone.points.map(([x, y]) => ({
                x: x * CANVAS_WIDTH,
                y: y * CANVAS_HEIGHT
            }));
            setCanvasPoints(canvasPoints);
        } else {
            // Reset para modo create
            setFormData({
                name: '',
                mode: 'GENERIC' as ZoneMode,
                points: [],
                ...DEFAULT_ZONE_VALUES
            });
            setCanvasPoints([]);
        }
    }, [mode, zone, isOpen]);

    /**
     * Valida polígono quando pontos mudam
     */
    useEffect(() => {
        if (canvasPoints.length >= 3) {
            setIsValidPolygon(true);
            setValidationMessage(`Polígono válido com ${canvasPoints.length} pontos`);
        } else if (canvasPoints.length > 0) {
            setIsValidPolygon(false);
            setValidationMessage(`Adicione ${3 - canvasPoints.length} ponto(s) para completar`);
        } else {
            setIsValidPolygon(false);
            setValidationMessage('Clique no vídeo para adicionar pontos');
        }
    }, [canvasPoints]);

    /**
     * Renderiza canvas quando pontos mudam
     */
    useEffect(() => {
        drawCanvas();
    }, [canvasPoints, hoveredIndex, draggingIndex]);

    // ==========================================================================
    // CANVAS DRAWING
    // ==========================================================================

    /**
     * Desenha o canvas com polígono e pontos
     */
    const drawCanvas = useCallback(() => {
        const canvas = canvasRef.current;
        const img = imgRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Limpa canvas
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        // Desenha imagem de fundo (stream)
        if (img && img.complete) {
            ctx.drawImage(img, 0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        }

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
        const normalizedPoints: Polygon = canvasPoints.map(p => [
            p.x / CANVAS_WIDTH,
            p.y / CANVAS_HEIGHT
        ]);

        setIsSaving(true);

        try {
            const payload = {
                ...formData,
                points: normalizedPoints,
                coordinate_system: 'normalized' as CoordinateSystem
            };

            await onSave(payload, zone?.id);

            // Reset e fecha
            setCanvasPoints([]);
            onClose();
        } catch (err) {
            console.error('Erro ao salvar zona:', err);
            // O erro já é tratado pelo hook useZones
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

                                <button
                                    onClick={handleClearPoints}
                                    disabled={canvasPoints.length === 0}
                                    className="flex items-center gap-2 px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    Limpar
                                </button>
                            </div>

                            {/* Canvas Container */}
                            <div
                                ref={containerRef}
                                className="relative bg-black rounded-lg overflow-hidden border-2 border-gray-300"
                                style={{ aspectRatio: `${CANVAS_WIDTH}/${CANVAS_HEIGHT}` }}
                            >
                                {/* Background Image (Stream) */}
                                <img
                                    ref={imgRef}
                                    src={streamUrl}
                                    alt="Video Stream"
                                    className="absolute inset-0 w-full h-full object-cover"
                                    onLoad={drawCanvas}
                                    crossOrigin="anonymous"
                                />

                                {/* Canvas Overlay */}
                                <canvas
                                    ref={canvasRef}
                                    width={CANVAS_WIDTH}
                                    height={CANVAS_HEIGHT}
                                    onClick={handleCanvasClick}
                                    onContextMenu={handleCanvasContextMenu}
                                    onMouseMove={handleCanvasMouseMove}
                                    onMouseDown={handleCanvasMouseDown}
                                    onMouseUp={handleCanvasMouseUp}
                                    onMouseLeave={handleCanvasMouseLeave}
                                    className="absolute inset-0 w-full h-full cursor-crosshair"
                                    style={{ imageRendering: 'crisp-edges' }}
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
                                    Nome da Zona *
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

                            {/* Modo */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Modo de Operação *
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

                            {/* Thresholds */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Threshold Vazio
                                    </label>
                                    <input
                                        type="number"
                                        min="0"
                                        value={formData.empty_threshold}
                                        onChange={(e) => handleFieldChange('empty_threshold', parseInt(e.target.value))}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        disabled={mode === 'view'}
                                    />
                                    <p className="mt-1 text-xs text-gray-500">
                                        Mínimo de pessoas para considerar vazio
                                    </p>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Threshold Cheio
                                    </label>
                                    <input
                                        type="number"
                                        min="1"
                                        value={formData.full_threshold}
                                        onChange={(e) => handleFieldChange('full_threshold', parseInt(e.target.value))}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        disabled={mode === 'view'}
                                    />
                                    <p className="mt-1 text-xs text-gray-500">
                                        Número de pessoas para considerar cheio
                                    </p>
                                </div>
                            </div>

                            {/* Timeouts */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Timeout Vazio (s)
                                    </label>
                                    <input
                                        type="number"
                                        min="0"
                                        step="0.5"
                                        value={formData.empty_timeout}
                                        onChange={(e) => handleFieldChange('empty_timeout', parseFloat(e.target.value))}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        disabled={mode === 'view'}
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Timeout Cheio (s)
                                    </label>
                                    <input
                                        type="number"
                                        min="0"
                                        step="0.5"
                                        value={formData.full_timeout}
                                        onChange={(e) => handleFieldChange('full_timeout', parseFloat(e.target.value))}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        disabled={mode === 'view'}
                                    />
                                </div>
                            </div>

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
