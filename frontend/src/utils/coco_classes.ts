/**
 * coco_classes.ts v2.0 - COCO Dataset Classes (Frontend)
 * Baseado em backend/services/coco_classes.py
 * 80 Classes do COCO Dataset (MS COCO 2017)
 * Compatível com YOLOv8, YOLOv9, YOLOv10, YOLOv11
 */

// ============================================================================
// COCO CLASSES DICTIONARY (80 classes)
// ============================================================================

export const COCO_CLASSES: Record<number, string> = {
    // PERSON
    0: 'pessoa',

    // VEHICLES
    1: 'bicicleta',
    2: 'carro',
    3: 'moto',
    4: 'avião',
    5: 'ônibus',
    6: 'trem',
    7: 'caminhão',
    8: 'barco',

    // TRAFFIC
    9: 'semáforo',
    10: 'hidrante',
    11: 'placa de pare',
    12: 'parquímetro',
    13: 'banco',

    // ANIMALS
    14: 'pássaro',
    15: 'gato',
    16: 'cachorro',
    17: 'cavalo',
    18: 'ovelha',
    19: 'vaca',
    20: 'elefante',
    21: 'urso',
    22: 'zebra',
    23: 'girafa',

    // ACCESSORIES
    24: 'mochila',
    25: 'guarda-chuva',
    26: 'bolsa',
    27: 'gravata',
    28: 'mala',

    // SPORTS
    29: 'frisbee',
    30: 'esquis',
    31: 'snowboard',
    32: 'bola',
    33: 'pipa',
    34: 'taco de baseball',
    35: 'luva de baseball',
    36: 'skate',
    37: 'prancha de surf',
    38: 'raquete de tênis',

    // KITCHEN
    39: 'garrafa',
    40: 'taça de vinho',
    41: 'xícara',
    42: 'garfo',
    43: 'faca',
    44: 'colher',
    45: 'tigela',

    // FOOD
    46: 'banana',
    47: 'maçã',
    48: 'sanduíche',
    49: 'laranja',
    50: 'brócolis',
    51: 'cenoura',
    52: 'cachorro-quente',
    53: 'pizza',
    54: 'rosquinha',
    55: 'bolo',

    // FURNITURE
    56: 'cadeira',
    57: 'sofá',
    58: 'planta',
    59: 'cama',
    60: 'mesa de jantar',
    61: 'vaso sanitário',

    // ELECTRONICS
    62: 'tv',
    63: 'laptop',
    64: 'mouse',
    65: 'controle remoto',
    66: 'teclado',
    67: 'celular',

    // APPLIANCES
    68: 'micro-ondas',
    69: 'forno',
    70: 'torradeira',
    71: 'pia',
    72: 'geladeira',

    // INDOOR
    73: 'livro',
    74: 'relógio',
    75: 'vaso',
    76: 'tesoura',
    77: 'ursinho de pelúcia',
    78: 'secador',
    79: 'escova de dentes',
};

// ============================================================================
// EMOJIS POR CLASSE (Visual)
// ============================================================================

export const CLASS_EMOJIS: Record<number, string> = {
    0: '👤',   // pessoa
    1: '🚲',   // bicicleta
    2: '🚗',   // carro
    3: '🏍️',   // moto
    5: '🚌',   // ônibus
    7: '🚛',   // caminhão
    15: '🐱',  // gato
    16: '🐕',  // cachorro
    41: '☕',  // xícara
    42: '🍴',  // garfo
    43: '🔪',  // faca
    44: '🥄',  // colher
    46: '🍌',  // banana
    47: '🍎',  // maçã
    53: '🍕',  // pizza
    56: '🪑',  // cadeira
    57: '🛋️',  // sofá
    63: '💻',  // laptop
    67: '📱',  // celular
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Obtém nome da classe em PT-BR
 * @param classId - ID da classe COCO (0-79)
 * @returns Nome da classe ou "desconhecido"
 */
export function getClassName(classId: number): string {
    return COCO_CLASSES[classId] || `classe_${classId}`;
}

/**
 * Obtém emoji representativo da classe
 * @param classId - ID da classe COCO
 * @returns Emoji ou 📦 (default)
 */
export function getClassEmoji(classId: number): string {
    return CLASS_EMOJIS[classId] || '📦';
}

/**
 * Obtém rótulo de detecção baseado nas classes configuradas
 * @param detectionClasses - Array de IDs de classes
 * @returns Rótulo formatado (ex: "pessoa", "colher e garfo", "pessoa, colher e garfo")
 */
export function getDetectionLabel(detectionClasses?: number[]): string {
    if (!detectionClasses || detectionClasses.length === 0) {
        return 'objetos';
    }

    // Se apenas 1 classe, retorna seu nome
    if (detectionClasses.length === 1) {
        return getClassName(detectionClasses[0]);
    }

    // Se 2 classes, retorna "A e B"
    if (detectionClasses.length === 2) {
        return `${getClassName(detectionClasses[0])} e ${getClassName(detectionClasses[1])}`;
    }

    // Se 3+ classes, retorna "A, B e C"
    const names = detectionClasses.map(id => getClassName(id));
    const last = names.pop();
    return `${names.join(', ')} e ${last}`;
}

/**
 * Obtém rótulo plural/singular correto
 * @param detectionClasses - Array de IDs de classes
 * @param count - Quantidade de objetos
 * @returns Rótulo com plural correto
 */
export function getDetectionLabelWithCount(detectionClasses?: number[], count: number = 0): string {
    if (!detectionClasses || detectionClasses.length === 0) {
        return count === 1 ? 'objeto' : 'objetos';
    }

    // Se apenas 1 classe, aplica plural
    if (detectionClasses.length === 1) {
        const name = getClassName(detectionClasses[0]);

        // Regras de pluralização PT-BR (simplificadas)
        if (count === 1) {
            return name;
        }

        // Exceções
        if (name === 'pessoa') return 'pessoas';
        if (name === 'ônibus') return 'ônibus';
        if (name === 'lápis') return 'lápis';

        // Regra geral: adiciona 's'
        if (name.endsWith('ão')) {
            return name.slice(0, -2) + 'ões'; // ex: avião → aviões
        }
        if (name.endsWith('l')) {
            return name.slice(0, -1) + 'is'; // ex: animal → animais
        }

        return name + 's'; // ex: carro → carros
    }

    // Se múltiplas classes, sempre plural
    return getDetectionLabel(detectionClasses);
}

/**
 * Obtém múltiplos emojis para representar as classes
 * @param detectionClasses - Array de IDs de classes
 * @param maxEmojis - Máximo de emojis a retornar
 * @returns String com emojis concatenados
 */
export function getDetectionEmojis(detectionClasses?: number[], maxEmojis: number = 3): string {
    if (!detectionClasses || detectionClasses.length === 0) {
        return '📦';
    }

    const emojis = detectionClasses
        .slice(0, maxEmojis)
        .map(id => getClassEmoji(id));

    if (detectionClasses.length > maxEmojis) {
        emojis.push('...');
    }

    return emojis.join(' ');
}

// ============================================================================
// CATEGORY CONSTANTS (para filtros)
// ============================================================================

export const PERSON_CLASS_IDS: Set<number> = new Set([0]);
export const VEHICLE_CLASS_IDS: Set<number> = new Set([1, 2, 3, 5, 7]);
export const ANIMAL_CLASS_IDS: Set<number> = new Set([15, 16, 17]);
export const FURNITURE_CLASS_IDS: Set<number> = new Set([56, 57, 58, 59, 60]);
export const ELECTRONICS_CLASS_IDS: Set<number> = new Set([62, 63, 64, 65, 66, 67]);
export const KITCHEN_CLASS_IDS: Set<number> = new Set([41, 42, 43, 44, 45]);
