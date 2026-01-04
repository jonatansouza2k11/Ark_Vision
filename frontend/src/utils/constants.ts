export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const STREAM_URL = import.meta.env.VITE_STREAM_URL || 'http://localhost:8000/video_feed';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export const ZONE_MODES = {
    GENERIC: 'Genérico',
    FLOW: 'Fluxo',
    QUEUE: 'Fila',
    CRITICAL: 'Crítico',
} as const;

export const ZONE_STATES = {
    OK: 'Normal',
    EMPTY_LONG: 'Vazia por muito tempo',
    FULL_LONG: 'Cheia por muito tempo',
} as const;
