// frontendsrc/types/trackers.types.ts

export type TrackerType =
    | 'simple'
    | 'yolo_bytetrack'
    | 'yolo_botsort'
    | 'strongsort'
    | 'fast_strongsort';

export const TRACKER_OPTIONS: {
    value: TrackerType;
    label: string;
    description: string;
}[] = [
        {
            value: 'simple',
            label: 'Somente detecção',
            description: 'IDs efêmeros por frame, sem tracking temporal. Mais leve.'
        },
        {
            value: 'yolo_bytetrack',
            label: 'ByteTrack (YOLO)',
            description: 'Rastreador rápido, bom para fluxo geral por câmera.'
        },
        {
            value: 'yolo_botsort',
            label: 'BoT-SORT (YOLO)',
            description: 'Rastreador mais estável, com custo um pouco maior.'
        },
        {
            value: 'strongsort',
            label: 'StrongSORT',
            description: 'Rastreador + ReID forte, ideal para casos críticos.'
        },
        {
            value: 'fast_strongsort',
            label: 'Fast-StrongSORT',
            description: 'Variante mais leve do StrongSORT.'
        }
    ];
