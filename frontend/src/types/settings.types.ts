// frontend/src/types/settings.types.ts

/**
 * Settings Types v4.0 - Advanced Features
 */

export interface YOLOConfig {
    model_path: string;
    conf_thresh: number;
    target_width: number;
    frame_step: number;
    tracker: string;
    source: string;
    cam_width: number;
    cam_height: number;
    cam_fps: number;
}

export interface ZoneConfig {
    max_out_time: number;
    email_cooldown: number;
    zone_empty_timeout: number;
    zone_full_timeout: number;
    zone_full_threshold: number;
    buffer_seconds: number;
}

export interface EmailConfig {
    email_smtp_server: string;
    email_smtp_port: number;
    email_user: string;
    email_password: string;
    email_from: string;
}

export interface SystemConfig {
    use_cuda: boolean;
    verbose_logs: boolean;
    auto_restart: boolean;
}

export interface AllSettings extends YOLOConfig, ZoneConfig, EmailConfig, SystemConfig { }

export type SettingsTab = 'yolo' | 'zones' | 'email' | 'system';

export interface ApiResponse<T> {
    data?: T;
    error?: string;
}

// ============================================================================
// NEW v4.0: Validation Types
// ============================================================================

export interface ValidationRule {
    field: string;
    message: string;
    level: 'error' | 'warning' | 'info';
}

export interface FieldValidation {
    valid: boolean;
    message?: string;
    level?: 'error' | 'warning' | 'info';
}

// ============================================================================
// NEW v4.0: History Types
// ============================================================================

export interface SettingsSnapshot {
    id: string;
    timestamp: string;
    user: string;
    category: SettingsTab;
    changes: Record<string, { old: any; new: any }>;
    settings: Partial<AllSettings>;
}

// ============================================================================
// NEW v4.0: Diff Types
// ============================================================================

export interface SettingsDiff {
    field: string;
    label: string;
    oldValue: any;
    newValue: any;
    changed: boolean;
}

// ============================================================================
// NEW v4.0: Export Types
// ============================================================================

export interface ExportData {
    version: string;
    exported_at: string;
    exported_by: string;
    category?: SettingsTab;
    settings: Partial<AllSettings>;
}
