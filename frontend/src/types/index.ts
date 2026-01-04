// ============================================
// 🎯 ARK YOLO - TYPESCRIPT TYPES
// ============================================

// ============================
// YOLO STREAM & STATS
// ============================
export interface YOLOStats {
    fpsavg: number;
    inzone: number;
    outzone: number;
    detectedcount: number;
    system_status: 'running' | 'paused' | 'stopped';
    preset?: string;
    recentalerts?: Alert[];
}

export interface Alert {
    id?: number;
    type: 'intrusion' | 'warning' | 'info';
    message: string;
    timestamp: string;
    severity?: 'low' | 'medium' | 'high' | 'critical';
}

// ============================
// USER & AUTH
// ============================
export interface User {
    id: number;
    username: string;
    email: string;
    is_active: boolean;
    is_superuser: boolean;
    created_at?: string;
}

export interface LoginCredentials {
    username: string;
    password: string;
}

export interface RegisterData {
    username: string;
    email: string;
    password: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user: User;
}

// ============================
// SETTINGS
// ============================
export interface Settings {
    // YOLO Model
    yolo_model_path: string;
    yolo_conf_threshold: number;
    yolo_target_width: number;
    yolo_frame_step: number;
    tracker: string;

    // Video Source
    video_source: string;

    // Camera Settings
    cam_width: number;
    cam_height: number;
    cam_fps: number;

    // Zone Detection
    max_out_time: number;
    email_cooldown: number;
    buffer_seconds: number;
    zone_empty_timeout: number;
    zone_full_timeout: number;
    zone_full_threshold: number;

    // Email Notifications
    smtp_server: string;
    smtp_port: number;
    email_sender: string;
    email_app_password: string;
    smtp_use_tls: boolean;

    // GPU
    use_gpu: boolean;
    cuda_visible_devices: string;

    // Memory
    buffer_size: number;
    gc_interval: number;
    memory_warning_threshold: number;
}

export interface SettingsUpdate extends Partial<Settings> { }

// ============================
// LOGS
// ============================
export interface LogEntry {
    id?: number;
    timestamp: string;
    level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
    message: string;
    module?: string;
}

// ============================
// DIAGNOSTICS
// ============================
export interface SystemDiagnostics {
    cpu_usage: number;
    memory_usage: number;
    gpu_available: boolean;
    gpu_usage?: number;
    disk_usage: number;
    yolo_status: string;
    camera_status: string;
    database_status: string;
}

// ============================
// API RESPONSES
// ============================
export interface APIResponse<T = any> {
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
    total_pages: number;
}

// ============================
// UI STATE
// ============================
export interface ToastNotification {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
    duration?: number;
}

export interface LoadingState {
    isLoading: boolean;
    message?: string;
    subtext?: string;
}
