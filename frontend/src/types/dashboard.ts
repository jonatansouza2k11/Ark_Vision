// src/types/dashboard.ts
import type { ElementType } from 'react';

// ============================================================================
// DASHBOARD
// ============================================================================

export interface Point {
    x: number;
    y: number;
}

export interface SafeZone {
    name: string;
    points: Point[];
    color: string;
    active: boolean;
    created_at: string;
}

export interface ZoneStatus {
    id: number;
    name: string;
    people_count: number;
    status: 'empty' | 'occupied' | 'full';
    last_change: string;
    duration_seconds: number;
}

export interface DashboardStats {
    inzone: number;
    outzone: number;
    detections: number;
    alerts: number;
    fps: number;
    system_status: string;
    model_name: string;
    video_source: string;
}

export interface Alert {
    person_id: number;
    timestamp: string;
    inzone: boolean;
    snapshot_path: string;
    email_sent: boolean;
    email_sent_at?: string | null;
    created_at: string;
    zone_id?: number | null;
    zone_name?: string | null;
}

export interface SystemLog {
    timestamp: string;
    action: string;
    reason?: string | null;
    username?: string | null;
    ip_address?: string | null;
    context?: Record<string, any> | null;
    created_at: string;
}

export interface SystemSettings {
    confthresh: number;
    targetwidth: number;
    framestep: number;
    maxouttime: number;
    emailcooldown: number;
    safezone: SafeZone[];
    source: string;
    camwidth: number;
    camheight: number;
    camfps: number;
    modelpath: string;
    tracker: string;
    zoneemptytimeout: number;
    zonefulltimeout: number;
    zonefullthreshold: number;
    bufferseconds: number;
}

export interface Activity {
    type: 'alert' | 'system';
    timestamp: string;
    description: string;
    severity: 'info' | 'warning' | 'critical';
    data?: Alert | SystemLog;
}

export interface DashboardData {
    stats: DashboardStats;
    alerts: Alert[];
    system_logs: SystemLog[];
    recent_activities: Activity[];
    settings: SystemSettings;
    zones: ZoneStatus[];
    safe_zones: SafeZone[];
    updated_at: string;
}

export interface SystemInfo {
    platform: string;
    python_version: string;
    opencv_version: string;
    yolo_model: string;
    database_status: string;
    uptime_seconds: number;
    total_detections: number;
    total_alerts: number;
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    last_restart: string;
}

// ============================================================================
// YOLO STREAM TYPES
// ============================================================================

export interface YOLOStats {
    // ✅ FPS Metrics (v3.0+)
    fps_current?: number;
    fps_avg?: number;
    fpsavg: number; // compat v2.0

    // Zonas
    inzone: number;
    outzone: number;

    // Detecções
    detected_count: number;

    // Status do sistema
    system_status: 'running' | 'stopped' | 'paused' | 'error';
    paused: boolean;
    stream_active: boolean;

    // Configuração
    preset: string;

    // Alertas
    recent_alerts: any[];

    // Métricas opcionais
    memory_mb?: number;
}

// ============================================================================
// STREAM CONTROL TYPES
// ============================================================================

export interface StreamControlResponse {
    message: string;
    status: string;
    paused?: boolean;
}

export interface StreamHealthResponse {
    status: 'healthy' | 'degraded' | 'unhealthy';
    stream_status: 'running' | 'stopped' | 'paused';
    uptime_seconds: number;
    fps_current: number;
    fps_target: number;
    frame_count: number;
    errors_count: number;
    memory_usage_mb: number;
    cpu_percent: number;
    gpu_available: boolean;
    last_error?: string;
    timestamp: string;
}

// ============================================================================
// COMPONENT PROPS
// ============================================================================

export interface SystemInfoBannerProps {
    modelName: string;
    videoSource: string;
    status: 'online' | 'offline' | 'paused' | 'stopped';
}

export interface StatCardProps {
    icon: ElementType;
    iconColor: string;
    title: string;
    value: number | string;
    subtitle?: string;
}

// ============================================================================
// ACTIVITY & EVENTS
// ============================================================================

export interface ActivityEvent {
    id: string;
    type: 'detection' | 'alert' | 'zone_violation' | 'system';
    timestamp: string;
    description: string;
    severity?: 'low' | 'medium' | 'high' | 'critical';
    metadata?: Record<string, any>;
}

// Observação: este type é de “estatística/estado por zona” do stream/detection.
// Não confundir com ZonesStatisticsResponse do endpoint /api/v1/zones/statistics.
export interface ZoneStatistics {
    zone_id: number;
    zone_name: string;
    count: number;
    status: 'OK' | 'EMPTY_LONG' | 'FULL_LONG';
    mode: 'GENERIC' | 'SECURITY' | 'MONITORING';
}

// ============================================================================
// DETECTION & TRACKING
// ============================================================================

export interface DetectionStats {
    total_detections: number;
    detections_per_minute: number;
    objects_in_zone: number;
    objects_out_zone: number;
    unique_tracks: number;
    active_tracks: number;
    detection_classes: Record<string, number>;
    zone_statistics: Record<string, ZoneStatistics>;
    alerts_triggered: number;
}

export interface TrackInfo {
    track_id: number;
    status: 'IN' | 'OUT';
    zone_idx: number;
    last_seen: number;
    out_time: number;
    recording: boolean;
}

// ============================================================================
// VIDEO & STREAM
// ============================================================================

export interface VideoStreamProps {
    onError?: (error: Error) => void;
    onLoad?: () => void;
    quality?: 'low' | 'medium' | 'high' | 'ultra';
}

export interface StreamMetrics {
    fps_current: number;
    fps_average: number;
    fps_min: number;
    fps_max: number;
    frame_count: number;
    dropped_frames: number;
    processing_time_ms: number;
    detection_time_ms: number;
    streaming_time_ms: number;
    memory_usage_mb: number;
    cpu_percent: number;
    gpu_percent?: number;
    bandwidth_mbps?: number;
    uptime_seconds: number;
    timestamp: string;
}

// ============================================================================
// SYSTEM & DIAGNOSTICS
// ============================================================================

export interface SystemDiagnostics {
    system_info: {
        platform: string;
        python_version: string;
        opencv_version?: string;
        cuda_available: boolean;
        cuda_version?: string;
        gpu_name?: string;
    };
    stream_info: {
        status: string;
        active: boolean;
        paused: boolean;
        fps: number;
        total_frames: number;
        restarts: number;
        errors: number;
    };
    performance_info: {
        memory_mb: number;
        cpu_percent: number;
        threads: number;
    };
    yolo_info: {
        model_loaded: boolean;
        detection_enabled: boolean;
        tracking_enabled: boolean;
        active_tracks: number;
    };
    zones_info: {
        zones_count: number;
        zones: string[];
    };
    issues: string[];
    recommendations: string[];
}

// ============================================================================
// API RESPONSE TYPES
// ============================================================================

export interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    message?: string;
    error?: string;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
}

// ============================================================================
// HOOK RETURN TYPES
// ============================================================================

export interface UseYOLOStreamReturn {
    stats: YOLOStats | null;
    isConnected: boolean;
    error: string | null;
    refresh: () => Promise<void>;
}

export interface UseStreamControlReturn {
    isLoading: boolean;
    error: string | null;
    startStream: () => Promise<void>;
    stopStream: () => Promise<void>;
    pauseStream: () => Promise<void>;
}

// ============================================================================
// ZONES STATISTICS (API: /api/v1/zones/statistics) - NEW v3.0
// (frontend snake_case; mapeado no src/api/dashboard.ts)
// ============================================================================

export interface ZonesStatisticsResponse {
    total_zones: number;
    enabled_zones: number;
    disabled_zones: number;
    active_zones: number;

    zones_by_mode: Record<string, number>;
    average_area: number;

    total_detections?: number | null;
    most_active_zones?: Array<Record<string, any>>;

    timestamp: string;
}
