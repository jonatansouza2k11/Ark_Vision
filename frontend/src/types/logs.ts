// frontend/src/types/logs.ts

/**
 * ============================================================================
 * LOGS TYPES - Completo e Alinhado com Backend
 * ============================================================================
 */

// ==================== SYSTEM LOG ====================
export interface SystemLog {
    id: number;
    action: string;
    username: string;
    reason: string | null;
    timestamp: string;
    email_sent: boolean;
    ip_address?: string | null;
    user_agent?: string | null;
    context?: Record<string, any>;
    session_id?: string | null;
}

// ==================== AUDIT LOG ====================
export interface AuditLog {
    id: number;
    timestamp: string;
    user_id: string;
    action: string;
    details: string | null;
    ip_address: string | null;
    previous_hash: string | null;
    current_hash: string;
    context?: Record<string, any>;
}

// ==================== COMBINED LOG (Union) ====================
export type CombinedLog = SystemLog & {
    log_type: 'system';
} | AuditLog & {
    log_type: 'audit';
} | Alert & {
    log_type: 'alert';
};

// ==================== LOG FILTERS ====================
export interface LogFilters {
    action?: string;
    username?: string;
    level?: LogLevel;
    start_date?: string;
    end_date?: string;
    search_term?: string;
    limit?: number;
}

export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
export type LogAction = 'login' | 'logout' | 'backup' | 'settings_changed' | 'user_created' | 'user_deleted' | string;
export type ExportFormat = 'json' | 'csv';

// ==================== LOG SEARCH REQUEST ====================
export interface LogSearchRequest {
    action?: string;
    username?: string;
    level?: LogLevel;
    start_date?: string;
    end_date?: string;
    search_term?: string;
    limit?: number;
}

// ==================== LOG SEARCH RESPONSE ====================
export interface LogSearchResponse {
    logs: SystemLog[];
    count: number;
    filters: Partial<LogSearchRequest>;
}

// ==================== LOG STATISTICS ====================
export interface LogStatistics {
    total: number;
    today: number;
    this_week: number;
    this_month: number;
    by_action: Record<string, number>;
    by_user: Record<string, number>;
}

// ==================== ALERT (Re-export from dashboard) ====================
export interface Alert {
    id: number;
    person_id: number;
    track_id?: number;
    out_time: number;
    zone_id?: number;
    zone_index?: number;
    zone_name?: string;
    alert_type: string;
    severity: string;
    description?: string;
    snapshot_path?: string | null;
    video_path?: string | null;
    email_sent: boolean;
    notification_sent?: boolean;
    resolved_at?: string | null;
    resolved_by?: string | null;
    resolution_notes?: string | null;
    metadata?: Record<string, any>;
    created_at: string;
    updated_at?: string | null;
}
