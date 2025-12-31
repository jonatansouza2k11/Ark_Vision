// src/types/dashboard.ts

// ============================================================================
// TIPOS BASEADOS NO BANCO DE DADOS SQLite (database.py)
// ============================================================================

// Tabela: alerts
export interface Alert {
    id: number;
    person_id: number;
    out_time: number; // tempo fora da zona (segundos)
    snapshot_path: string | null;
    email_sent: boolean;
    timestamp: string;
}

// Tabela: system_logs
export interface SystemLog {
    id: number;
    action: 'PAUSAR' | 'RETOMAR' | 'PARAR' | 'INICIAR';
    username: string;
    reason: string | null;
    email_sent: boolean;
    timestamp: string;
}

// Tabela: settings (configurações do sistema)
export interface SystemSettings {
    // YOLO
    conf_thresh: number;
    model_path: string;

    // Performance
    target_width: number;
    frame_step: number;

    // Zona / Alertas
    safe_zone: SafeZone[]; // JSON array de zonas
    max_out_time: number;
    email_cooldown: number;
    buffer_seconds: number;

    // Fonte de vídeo
    source: string; // "0" para webcam ou path/url

    // Parâmetros da câmera
    cam_width: number;
    cam_height: number;
    cam_fps: number;

    // Tracker
    tracker: string;

    // Parâmetros de zona
    zone_empty_timeout: number;
    zone_full_timeout: number;
    zone_full_threshold: number;

    // Email / SMTP
    email_smtp_server: string;
    email_smtp_port: number;
    email_use_tls: boolean;
    email_use_ssl: boolean;
    email_from: string;
    email_user: string;
    email_password: string;
}

// Safe Zone (zona poligonal)
export interface SafeZone {
    id: string;
    name: string;
    mode: 'FLOW' | 'QUEUE' | 'CRITICAL' | 'GENERIC';
    polygon: Point[]; // Array de pontos [x, y]
    enabled: boolean;
    // Parâmetros específicos por modo
    params?: {
        empty_timeout?: number;
        full_timeout?: number;
        full_threshold?: number;
    };
}

export interface Point {
    x: number;
    y: number;
}

// Informações do sistema (runtime)
export interface SystemInfo {
    model_name: string;
    video_source_label: string;
    confidence: number;
    fps: number;
    resolution: string;
    gpu_enabled: boolean;
    status: 'online' | 'offline' | 'paused' | 'stopped';
    uptime: number; // segundos
}

// Estatísticas em tempo real
export interface DashboardStats {
    // Contadores da sessão atual
    in_zone_count: number;
    out_zone_count: number;
    total_detections: number;

    // Alertas
    alerts_last_24h: number;
    alerts_total: number;

    // Zonas
    zones: ZoneStatus[];
}

// Status de uma zona em tempo real
export interface ZoneStatus {
    zone_id: string;
    zone_name: string;
    mode: 'FLOW' | 'QUEUE' | 'CRITICAL' | 'GENERIC';
    current_count: number;
    time_empty: number; // segundos que está vazia
    time_full: number; // segundos que está cheia
    state: 'empty' | 'normal' | 'warning' | 'alert' | 'critical';
}

// Atividade recente (combinação de alerts + detecções)
export interface Activity {
    id: string;
    type: 'alert' | 'detection' | 'system_action';
    timestamp: string;
    person_id?: number;
    out_time?: number;
    zone_name?: string;
    action?: string;
    username?: string;
    reason?: string;
    snapshot_path?: string;
    message: string;
}

// Dados completos do dashboard
export interface DashboardData {
    system_info: SystemInfo;
    stats: DashboardStats;
    recent_activities: Activity[];
}
