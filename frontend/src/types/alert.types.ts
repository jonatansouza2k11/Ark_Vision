// src/types/alert.types.ts
// ============================================================================
// ALERTS - Alinhado com backend/database.py (v2.2 com zone_id)
// ============================================================================

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AlertType = 'zone_violation' | 'intrusion' | 'warning' | 'info';

export interface Alert {
    id: number;
    person_id: number;
    track_id?: number | null;
    out_time: number;
    snapshot_path?: string | null;
    video_path?: string | null;
    email_sent: boolean;
    created_at: string;              
    zone_index?: number | null;
    zone_id?: number | null;         
    zone_name?: string | null;
    alert_type: AlertType;           
    severity: AlertSeverity;        
    description?: string | null;
    metadata?: Record<string, any>;
    resolved_at?: string | null;    
    resolved_by?: string | null;
    resolution_notes?: string | null;
}

export interface AlertCreate {
    person_id: number;
    out_time: number;
    track_id?: number;
    snapshot_path?: string;
    video_path?: string;
    zone_index?: number;
    zone_id?: number;
    zone_name?: string;
    alert_type?: AlertType;
    severity?: AlertSeverity;
    description?: string;
    metadata?: Record<string, any>;
}

export interface AlertStats {
    total: number;
    last_24h: number;
    by_severity: Record<AlertSeverity, number>;
    by_zone: Array<{
        zone_id: number;
        zone_name: string;
        count: number;
    }>;
}
