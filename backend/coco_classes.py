# coco_classes.py

# Mapa de classes COCO relevantes
COCO_CLASSES = {
    0:  "person",
    1:  "bicycle",
    2:  "car",
    3:  "motorbike",
    5:  "bus",
    7:  "truck",
    15: "bench",
    16: "bird",
    17: "cat",
    18: "dog",
    24: "backpack",
    25: "umbrella",
    39: "bottle",
    56: "chair",
    57: "sofa",
    58: "pottedplant",
    59: "bed",
    61: "diningtable",
    62: "toilet",
    63: "tvmonitor",
    67: "diningtable_var",  # variação de mapeamento
    73: "laptop",
}

# Constantes úteis
PERSON_CLASS_ID = 0
VEHICLE_CLASS_IDS = {1, 2, 3, 5, 7}  # bicycle, car, motorbike, bus, truck
ANIMAL_CLASS_IDS = {16, 17, 18}      # bird, cat, dog
FURNITURE_CLASS_IDS = {15, 56, 57, 58, 59, 61, 62, 63, 67, 73}  # bench, chair, sofa, pottedplant, bed, diningtable, toilet, tvmonitor, diningtable_var, laptop
ALL_RELEVANT_CLASS_IDS = {PERSON_CLASS_ID} | VEHICLE_CLASS_IDS | ANIMAL_CLASS_IDS | FURNITURE_CLASS_IDS

def get_class_name(class_id):
    """
    Retorna o nome da classe COCO dado seu ID.
    """
    return COCO_CLASSES.get(class_id, "unknown")

def is_relevant_class(class_id):
    """
    Verifica se a classe é relevante para análise.
    """
    return class_id in ALL_RELEVANT_CLASS_IDS

def get_relevant_classes():
    """
    Retorna uma lista de todas as classes relevantes.
    """
    return [COCO_CLASSES[cid] for cid in ALL_RELEVANT_CLASS_IDS]

def get_vehicle_classes():
    """
    Retorna uma lista de classes de veículos.
    """
    return [COCO_CLASSES[cid] for cid in VEHICLE_CLASS_IDS]

def get_animal_classes():
    """
    Retorna uma lista de classes de animais.
    """
    return [COCO_CLASSES[cid] for cid in ANIMAL_CLASS_IDS]

def get_furniture_classes():
    """ 
    Retorna uma lista de classes de móveis.
    """
    return [COCO_CLASSES[cid] for cid in FURNITURE_CLASS_IDS]

def get_person_class():
    """
    Retorna a classe de pessoa.
    """
    return COCO_CLASSES[PERSON_CLASS_ID]

def get_all_classes():
    """
    Retorna uma lista de todas as classes COCO.
    """
    return list(COCO_CLASSES.values())
