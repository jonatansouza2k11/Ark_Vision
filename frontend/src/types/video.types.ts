
export interface VideoStatus {
    system_status: 'running' | 'paused' | 'stopped';
    stream_active: boolean;
    paused: boolean;
    fps: number;
    fps_inst: number;
    fps_avg: number;
    in_zone: number;
    out_zone: number;
    detected_count: number;
    zones: ZoneStats[];
    memory_mb: number;
    peak_memory_mb: number;
    frame_count: number;
    preset: string;
}

export interface ZoneStats {
    index: number;
    name: string;
    mode: 'GENERIC' | 'FLOW' | 'QUEUE' | 'CRITICAL';
    count: number;
    empty_time: number | null;
    full_time: number | null;
    state: 'OK' | 'EMPTY_LONG' | 'FULL_LONG';
}

export interface Detection {
    track_id: number;
    status: 'IN' | 'OUT';
    out_time: number;
    zone_index: number;
    is_recording: boolean;
    last_seen: string;
}

export interface VideoControlResponse {
    success: boolean;
    message: string;
    system_status: string;
}
