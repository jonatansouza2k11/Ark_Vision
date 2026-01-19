"""
============================================================================
coco_classes.py v2.0 - COCO Dataset Classes (Ultralytics Compliant)
============================================================================
80 Classes do COCO Dataset (MS COCO 2017)
Compatível com YOLOv8, YOLOv9, YOLOv10, YOLOv11

Documentação Oficial:
- https://docs.ultralytics.com/datasets/detect/coco/
- https://cocodataset.org/#home

Performance:
- Dict lookup: O(1)
- Frozen sets para constantes: O(1) membership test
- Type hints para melhor IDE support

Escalabilidade:
- Suporta filtragem por categoria
- Cache de funções custosas com @lru_cache
- Lazy evaluation onde possível
============================================================================
"""

from typing import List, Dict, Set, Optional, FrozenSet
from functools import lru_cache
from enum import IntEnum

# ============================================================================
# COCO DATASET - 80 CLASSES COMPLETAS (Ultralytics Official Order)
# ============================================================================

COCO_CLASSES: Dict[int, str] = {
    # ✅ PERSON
    0: "person",
    
    # ✅ VEHICLES (Mais usados)
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "airplane",
    5: "bus",
    6: "train",
    7: "truck",
    8: "boat",
    
    # TRAFFIC
    9: "traffic light",
    10: "fire hydrant",
    11: "stop sign",
    12: "parking meter",
    13: "bench",
    
    # ✅ ANIMALS (Mais usados)
    14: "bird",
    15: "cat",
    16: "dog",
    17: "horse",
    18: "sheep",
    19: "cow",
    20: "elephant",
    21: "bear",
    22: "zebra",
    23: "giraffe",
    
    # ACCESSORIES
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    27: "tie",
    28: "suitcase",
    
    # ✅ SPORTS (Mais usados)
    29: "frisbee",
    30: "skis",
    31: "snowboard",
    32: "sports ball",
    33: "kite",
    34: "baseball bat",
    35: "baseball glove",
    36: "skateboard",
    37: "surfboard",
    38: "tennis racket",
    
    # ✅ KITCHEN (Mais usados)
    39: "bottle",
    40: "wine glass",
    41: "cup",
    42: "fork",
    43: "knife",
    44: "spoon",
    45: "bowl",
    
    # FOOD
    46: "banana",
    47: "apple",
    48: "sandwich",
    49: "orange",
    50: "broccoli",
    51: "carrot",
    52: "hot dog",
    53: "pizza",
    54: "donut",
    55: "cake",
    
    # ✅ FURNITURE (Mais usados)
    56: "chair",
    57: "couch",
    58: "potted plant",
    59: "bed",
    60: "dining table",
    61: "toilet",
    
    # ✅ ELECTRONICS (Mais usados)
    62: "tv",
    63: "laptop",
    64: "mouse",
    65: "remote",
    66: "keyboard",
    67: "cell phone",
    
    # APPLIANCES
    68: "microwave",
    69: "oven",
    70: "toaster",
    71: "sink",
    72: "refrigerator",
    
    # INDOOR
    73: "book",
    74: "clock",
    75: "vase",
    76: "scissors",
    77: "teddy bear",
    78: "hair drier",
    79: "toothbrush"
}

# ============================================================================
# CLASS IDs POR CATEGORIA (Frozen Sets para Performance)
# ============================================================================

# ✅ Pessoas (Mais usado)
PERSON_CLASS_ID: int = 0
PERSON_CLASS_IDS: FrozenSet[int] = frozenset({0})

# ✅ Veículos (Mais usados)
VEHICLE_CLASS_IDS: FrozenSet[int] = frozenset({1, 2, 3, 5, 7})  # bicycle, car, motorcycle, bus, truck

# ✅ Animais (Mais usados)
ANIMAL_CLASS_IDS: FrozenSet[int] = frozenset({14, 15, 16, 17, 18, 19})  # bird, cat, dog, horse, sheep, cow

# ✅ Móveis (Mais usados)
FURNITURE_CLASS_IDS: FrozenSet[int] = frozenset({13, 56, 57, 58, 59, 60, 61})  # bench, chair, couch, potted plant, bed, dining table, toilet

# ✅ Eletrônicos (Mais usados)
ELECTRONICS_CLASS_IDS: FrozenSet[int] = frozenset({62, 63, 64, 65, 66, 67})  # tv, laptop, mouse, remote, keyboard, cell phone

# Outras categorias (Todas as classes restantes comentadas para reference)
# TRAFFIC_CLASS_IDS = frozenset({9, 10, 11, 12})  # traffic light, fire hydrant, stop sign, parking meter
# ACCESSORIES_CLASS_IDS = frozenset({24, 25, 26, 27, 28})  # backpack, umbrella, handbag, tie, suitcase
# SPORTS_CLASS_IDS = frozenset({29, 30, 31, 32, 33, 34, 35, 36, 37, 38})  # frisbee, skis, etc
# KITCHEN_CLASS_IDS = frozenset({39, 40, 41, 42, 43, 44, 45})  # bottle, wine glass, cup, fork, knife, spoon, bowl
# FOOD_CLASS_IDS = frozenset({46, 47, 48, 49, 50, 51, 52, 53, 54, 55})  # banana, apple, sandwich, etc
# APPLIANCES_CLASS_IDS = frozenset({68, 69, 70, 71, 72})  # microwave, oven, toaster, sink, refrigerator
# INDOOR_CLASS_IDS = frozenset({73, 74, 75, 76, 77, 78, 79})  # book, clock, vase, scissors, etc

# ✅ Classes mais relevantes (DEFAULT - apenas pessoa)
DEFAULT_RELEVANT_CLASS_IDS: FrozenSet[int] = PERSON_CLASS_IDS

# Todas as classes (para reference)
ALL_CLASS_IDS: FrozenSet[int] = frozenset(COCO_CLASSES.keys())

# ============================================================================
# ENUM PARA TYPE SAFETY (Optional - Python 3.11+)
# ============================================================================

class CocoClassId(IntEnum):
    """Type-safe COCO class IDs"""
    PERSON = 0
    BICYCLE = 1
    CAR = 2
    MOTORCYCLE = 3
    AIRPLANE = 4
    BUS = 5
    TRAIN = 6
    TRUCK = 7
    BOAT = 8
    # ... (adicionar todos se necessário para type checking)

# ============================================================================
# FUNÇÕES OTIMIZADAS (Com Cache)
# ============================================================================

@lru_cache(maxsize=128)
def get_class_name(class_id: int) -> str:
    """
    Retorna o nome da classe COCO dado seu ID.
    
    Args:
        class_id: ID da classe COCO (0-79)
        
    Returns:
        Nome da classe ou "unknown"
        
    Performance:
        - O(1) dict lookup
        - Cached para chamadas repetidas
    """
    return COCO_CLASSES.get(class_id, "unknown")


def is_relevant_class(class_id: int, relevant_ids: Optional[FrozenSet[int]] = None) -> bool:
    """
    Verifica se a classe é relevante para análise.
    
    Args:
        class_id: ID da classe COCO
        relevant_ids: Set de IDs relevantes (default: apenas person)
        
    Returns:
        True se a classe for relevante
        
    Performance:
        - O(1) set membership test
    """
    if relevant_ids is None:
        relevant_ids = DEFAULT_RELEVANT_CLASS_IDS
    return class_id in relevant_ids


@lru_cache(maxsize=32)
def get_classes_by_ids(class_ids: FrozenSet[int]) -> List[str]:
    """
    Retorna nomes de classes dado um set de IDs.
    
    Args:
        class_ids: FrozenSet de IDs de classes
        
    Returns:
        Lista de nomes de classes
        
    Performance:
        - Cached para sets comuns
        - O(n) onde n = len(class_ids)
    """
    return [COCO_CLASSES[cid] for cid in sorted(class_ids) if cid in COCO_CLASSES]


def get_person_class() -> str:
    """Retorna a classe de pessoa"""
    return COCO_CLASSES[PERSON_CLASS_ID]


def get_vehicle_classes() -> List[str]:
    """Retorna lista de classes de veículos"""
    return get_classes_by_ids(VEHICLE_CLASS_IDS)


def get_animal_classes() -> List[str]:
    """Retorna lista de classes de animais"""
    return get_classes_by_ids(ANIMAL_CLASS_IDS)


def get_furniture_classes() -> List[str]:
    """Retorna lista de classes de móveis"""
    return get_classes_by_ids(FURNITURE_CLASS_IDS)


def get_electronics_classes() -> List[str]:
    """Retorna lista de classes de eletrônicos"""
    return get_classes_by_ids(ELECTRONICS_CLASS_IDS)


@lru_cache(maxsize=1)
def get_all_classes() -> List[str]:
    """
    Retorna lista de todas as 80 classes COCO.
    
    Returns:
        Lista ordenada por ID de classe
        
    Performance:
        - Cached (chamada única)
    """
    return [COCO_CLASSES[i] for i in range(80)]


@lru_cache(maxsize=1)
def get_all_classes_dict() -> Dict[int, str]:
    """
    Retorna dicionário completo de classes.
    
    Returns:
        Dict[class_id, class_name]
    """
    return COCO_CLASSES.copy()


def filter_detections_by_class(
    detections: List[Dict],
    allowed_class_ids: FrozenSet[int]
) -> List[Dict]:
    """
    Filtra detecções por classes permitidas.
    
    Args:
        detections: Lista de detecções do YOLO
        allowed_class_ids: Set de IDs de classes permitidas
        
    Returns:
        Lista filtrada de detecções
        
    Performance:
        - O(n) onde n = len(detections)
        - Set membership test é O(1)
    """
    return [
        det for det in detections
        if det.get('class_id') in allowed_class_ids
    ]


# ============================================================================
# UTILITY: Conversão de Nomes para IDs
# ============================================================================

# Mapa reverso (nome -> ID) - gerado uma vez
_NAME_TO_ID_MAP: Dict[str, int] = {name: cid for cid, name in COCO_CLASSES.items()}


@lru_cache(maxsize=128)
def get_class_id_by_name(class_name: str) -> Optional[int]:
    """
    Retorna ID da classe dado seu nome.
    
    Args:
        class_name: Nome da classe (case-insensitive)
        
    Returns:
        ID da classe ou None se não encontrada
        
    Performance:
        - O(1) dict lookup
        - Case-insensitive
    """
    return _NAME_TO_ID_MAP.get(class_name.lower())


# ============================================================================
# VALIDAÇÃO
# ============================================================================

def validate_class_ids(class_ids: List[int]) -> tuple[bool, List[str]]:
    """
    Valida lista de IDs de classes.
    
    Args:
        class_ids: Lista de IDs para validar
        
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    if not class_ids:
        errors.append("Lista de classes vazia")
        return False, errors
    
    for cid in class_ids:
        if not isinstance(cid, int):
            errors.append(f"ID inválido: {cid} (deve ser inteiro)")
        elif cid not in ALL_CLASS_IDS:
            errors.append(f"ID fora do range COCO: {cid} (deve ser 0-79)")
    
    return len(errors) == 0, errors


# ============================================================================
# TESTE
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("COCO Classes v2.0 - Ultralytics Compliant")
    print("=" * 80)
    print(f"Total classes: {len(COCO_CLASSES)}")
    print(f"Person class: {get_person_class()}")
    print(f"Vehicle classes: {get_vehicle_classes()}")
    print(f"Animal classes: {get_animal_classes()}")
    print(f"Furniture classes: {get_furniture_classes()}")
    print(f"Electronics classes: {get_electronics_classes()}")
    print("=" * 80)
    
    # Teste de performance
    import timeit
    
    # Lookup de classe
    time_lookup = timeit.timeit(
        lambda: get_class_name(0),
        number=100000
    )
    print(f"get_class_name (100k calls): {time_lookup:.4f}s")
    
    # Membership test
    time_membership = timeit.timeit(
        lambda: is_relevant_class(0),
        number=100000
    )
    print(f"is_relevant_class (100k calls): {time_membership:.4f}s")
    
    print("=" * 80)
