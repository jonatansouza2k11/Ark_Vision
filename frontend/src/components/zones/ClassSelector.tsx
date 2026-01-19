/**
 * ============================================================================
 * ClassSelector.tsx - Reusable COCO Class Selector Component
 * ============================================================================
 * Seletor multi-select de classes COCO para zonas inteligentes
 * 
 * Features:
 * - Multi-select com checkboxes
 * - Agrupamento por categorias
 * - Pesquisa/filtro
 * - Visual compacto e responsivo
 * - Type-safe com TypeScript
 * 
 * Uso:
 * <ClassSelector
 *   selectedClasses={formData.metadata?.detection_classes || [0]}
 *   onChange={(classes) => handleMetadataChange('detection_classes', classes)}
 *   disabled={mode === 'view'}
 * />
 * ============================================================================
 */

import { useState, useMemo } from 'react';
import { Search, ChevronDown, ChevronRight, Users, Car, PawPrint, Armchair, Monitor } from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

export interface ClassSelectorProps {
    selectedClasses: number[];
    onChange: (classes: number[]) => void;
    disabled?: boolean;
    showSearch?: boolean;
    maxHeight?: string;
}

interface CocoClass {
    id: number;
    name: string;
    nameEn: string;  
    namePtBr: string;  
    category: string;
}

// ============================================================================
// TRADUÇÕES PT-BR (80 classes completas)
// ============================================================================

const COCO_TRANSLATIONS: Record<string, string> = {
    // PERSON
    "person": "Pessoa",

    // VEHICLES
    "bicycle": "Bicicleta",
    "car": "Carro",
    "motorcycle": "Motocicleta",
    "airplane": "Avião",
    "bus": "Ônibus",
    "train": "Trem",
    "truck": "Caminhão",
    "boat": "Barco",

    // TRAFFIC
    "traffic light": "Semáforo",
    "fire hydrant": "Hidrante",
    "stop sign": "Placa de Pare",
    "parking meter": "Parquímetro",
    "bench": "Banco",

    // ANIMALS
    "bird": "Pássaro",
    "cat": "Gato",
    "dog": "Cachorro",
    "horse": "Cavalo",
    "sheep": "Ovelha",
    "cow": "Vaca",
    "elephant": "Elefante",
    "bear": "Urso",
    "zebra": "Zebra",
    "giraffe": "Girafa",

    // ACCESSORIES
    "backpack": "Mochila",
    "umbrella": "Guarda-chuva",
    "handbag": "Bolsa",
    "tie": "Gravata",
    "suitcase": "Mala",

    // SPORTS
    "frisbee": "Frisbee",
    "skis": "Esquis",
    "snowboard": "Snowboard",
    "sports ball": "Bola Esportiva",
    "kite": "Pipa",
    "baseball bat": "Taco de Beisebol",
    "baseball glove": "Luva de Beisebol",
    "skateboard": "Skate",
    "surfboard": "Prancha de Surf",
    "tennis racket": "Raquete de Tênis",

    // KITCHEN
    "bottle": "Garrafa",
    "wine glass": "Taça de Vinho",
    "cup": "Xícara",
    "fork": "Garfo",
    "knife": "Faca",
    "spoon": "Colher",
    "bowl": "Tigela",

    // FOOD
    "banana": "Banana",
    "apple": "Maçã",
    "sandwich": "Sanduíche",
    "orange": "Laranja",
    "broccoli": "Brócolis",
    "carrot": "Cenoura",
    "hot dog": "Cachorro-quente",
    "pizza": "Pizza",
    "donut": "Rosquinha",
    "cake": "Bolo",

    // FURNITURE
    "chair": "Cadeira",
    "couch": "Sofá",
    "potted plant": "Planta em Vaso",
    "bed": "Cama",
    "dining table": "Mesa de Jantar",
    "toilet": "Vaso Sanitário",

    // ELECTRONICS
    "tv": "TV",
    "laptop": "Notebook",
    "mouse": "Mouse",
    "remote": "Controle Remoto",
    "keyboard": "Teclado",
    "cell phone": "Celular",

    // APPLIANCES
    "microwave": "Micro-ondas",
    "oven": "Forno",
    "toaster": "Torradeira",
    "sink": "Pia",
    "refrigerator": "Geladeira",

    // INDOOR
    "book": "Livro",
    "clock": "Relógio",
    "vase": "Vaso",
    "scissors": "Tesoura",
    "teddy bear": "Ursinho de Pelúcia",
    "hair drier": "Secador de Cabelo",
    "toothbrush": "Escova de Dentes"
};

// ============================================================================
// COCO CLASSES DATA (80 classes completas em PT-BR)
// ============================================================================

const COCO_CLASSES: CocoClass[] = [
    // ✅ PERSON (Padrão ativo)
    { id: 0, name: "person", nameEn: "person", namePtBr: "Pessoa", category: "person" },

    // ✅ VEHICLES (Mais usados - comentados)
    // { id: 1, name: "bicycle", nameEn: "bicycle", namePtBr: "Bicicleta", category: "vehicle" },
    // { id: 2, name: "car", nameEn: "car", namePtBr: "Carro", category: "vehicle" },
    // { id: 3, name: "motorcycle", nameEn: "motorcycle", namePtBr: "Motocicleta", category: "vehicle" },
    // { id: 4, name: "airplane", nameEn: "airplane", namePtBr: "Avião", category: "vehicle" },
    // { id: 5, name: "bus", nameEn: "bus", namePtBr: "Ônibus", category: "vehicle" },
    // { id: 6, name: "train", nameEn: "train", namePtBr: "Trem", category: "vehicle" },
    // { id: 7, name: "truck", nameEn: "truck", namePtBr: "Caminhão", category: "vehicle" },
    // { id: 8, name: "boat", nameEn: "boat", namePtBr: "Barco", category: "vehicle" },

    // TRAFFIC (comentados)
    // { id: 9, name: "traffic light", nameEn: "traffic light", namePtBr: "Semáforo", category: "traffic" },
    // { id: 10, name: "fire hydrant", nameEn: "fire hydrant", namePtBr: "Hidrante", category: "traffic" },
    // { id: 11, name: "stop sign", nameEn: "stop sign", namePtBr: "Placa de Pare", category: "traffic" },
    // { id: 12, name: "parking meter", nameEn: "parking meter", namePtBr: "Parquímetro", category: "traffic" },
    // { id: 13, name: "bench", nameEn: "bench", namePtBr: "Banco", category: "furniture" },

    // ✅ ANIMALS (Mais usados - comentados)
    // { id: 14, name: "bird", nameEn: "bird", namePtBr: "Pássaro", category: "animal" },
    // { id: 15, name: "cat", nameEn: "cat", namePtBr: "Gato", category: "animal" },
    // { id: 16, name: "dog", nameEn: "dog", namePtBr: "Cachorro", category: "animal" },
    // { id: 17, name: "horse", nameEn: "horse", namePtBr: "Cavalo", category: "animal" },
    // { id: 18, name: "sheep", nameEn: "sheep", namePtBr: "Ovelha", category: "animal" },
    // { id: 19, name: "cow", nameEn: "cow", namePtBr: "Vaca", category: "animal" },
    // { id: 20, name: "elephant", nameEn: "elephant", namePtBr: "Elefante", category: "animal" },
    // { id: 21, name: "bear", nameEn: "bear", namePtBr: "Urso", category: "animal" },
    // { id: 22, name: "zebra", nameEn: "zebra", namePtBr: "Zebra", category: "animal" },
    // { id: 23, name: "giraffe", nameEn: "giraffe", namePtBr: "Girafa", category: "animal" },

    // ACCESSORIES (comentados)
    // { id: 24, name: "backpack", nameEn: "backpack", namePtBr: "Mochila", category: "accessory" },
    // { id: 25, name: "umbrella", nameEn: "umbrella", namePtBr: "Guarda-chuva", category: "accessory" },
    // { id: 26, name: "handbag", nameEn: "handbag", namePtBr: "Bolsa", category: "accessory" },
    // { id: 27, name: "tie", nameEn: "tie", namePtBr: "Gravata", category: "accessory" },
    // { id: 28, name: "suitcase", nameEn: "suitcase", namePtBr: "Mala", category: "accessory" },

    // SPORTS (comentados)
    // { id: 29, name: "frisbee", nameEn: "frisbee", namePtBr: "Frisbee", category: "sports" },
    // { id: 30, name: "skis", nameEn: "skis", namePtBr: "Esquis", category: "sports" },
    // { id: 31, name: "snowboard", nameEn: "snowboard", namePtBr: "Snowboard", category: "sports" },
    // { id: 32, name: "sports ball", nameEn: "sports ball", namePtBr: "Bola Esportiva", category: "sports" },
    // { id: 33, name: "kite", nameEn: "kite", namePtBr: "Pipa", category: "sports" },
    // { id: 34, name: "baseball bat", nameEn: "baseball bat", namePtBr: "Taco de Beisebol", category: "sports" },
    // { id: 35, name: "baseball glove", nameEn: "baseball glove", namePtBr: "Luva de Beisebol", category: "sports" },
    // { id: 36, name: "skateboard", nameEn: "skateboard", namePtBr: "Skate", category: "sports" },
    // { id: 37, name: "surfboard", nameEn: "surfboard", namePtBr: "Prancha de Surf", category: "sports" },
    // { id: 38, name: "tennis racket", nameEn: "tennis racket", namePtBr: "Raquete de Tênis", category: "sports" },

    // ✅ KITCHEN (Mais usados - comentados)
     { id: 39, name: "bottle", nameEn: "bottle", namePtBr: "Garrafa", category: "kitchen" },
     { id: 40, name: "wine glass", nameEn: "wine glass", namePtBr: "Taça de Vinho", category: "kitchen" },
     { id: 41, name: "cup", nameEn: "cup", namePtBr: "Xícara", category: "kitchen" },
     { id: 42, name: "fork", nameEn: "fork", namePtBr: "Garfo", category: "kitchen" },
     { id: 43, name: "knife", nameEn: "knife", namePtBr: "Faca", category: "kitchen" },
     { id: 44, name: "spoon", nameEn: "spoon", namePtBr: "Colher", category: "kitchen" },
     { id: 45, name: "bowl", nameEn: "bowl", namePtBr: "Tigela", category: "kitchen" },

    // FOOD (comentados)
    // { id: 46, name: "banana", nameEn: "banana", namePtBr: "Banana", category: "food" },
    // { id: 47, name: "apple", nameEn: "apple", namePtBr: "Maçã", category: "food" },
    // { id: 48, name: "sandwich", nameEn: "sandwich", namePtBr: "Sanduíche", category: "food" },
    // { id: 49, name: "orange", nameEn: "orange", namePtBr: "Laranja", category: "food" },
    // { id: 50, name: "broccoli", nameEn: "broccoli", namePtBr: "Brócolis", category: "food" },
    // { id: 51, name: "carrot", nameEn: "carrot", namePtBr: "Cenoura", category: "food" },
    // { id: 52, name: "hot dog", nameEn: "hot dog", namePtBr: "Cachorro-quente", category: "food" },
    // { id: 53, name: "pizza", nameEn: "pizza", namePtBr: "Pizza", category: "food" },
    // { id: 54, name: "donut", nameEn: "donut", namePtBr: "Rosquinha", category: "food" },
    // { id: 55, name: "cake", nameEn: "cake", namePtBr: "Bolo", category: "food" },

    // ✅ FURNITURE (Mais usados - comentados)
    // { id: 56, name: "chair", nameEn: "chair", namePtBr: "Cadeira", category: "furniture" },
    // { id: 57, name: "couch", nameEn: "couch", namePtBr: "Sofá", category: "furniture" },
    // { id: 58, name: "potted plant", nameEn: "potted plant", namePtBr: "Planta em Vaso", category: "furniture" },
    // { id: 59, name: "bed", nameEn: "bed", namePtBr: "Cama", category: "furniture" },
    // { id: 60, name: "dining table", nameEn: "dining table", namePtBr: "Mesa de Jantar", category: "furniture" },
    // { id: 61, name: "toilet", nameEn: "toilet", namePtBr: "Vaso Sanitário", category: "furniture" },

    // ✅ ELECTRONICS (Mais usados - comentados)
    // { id: 62, name: "tv", nameEn: "tv", namePtBr: "TV", category: "electronics" },
    // { id: 63, name: "laptop", nameEn: "laptop", namePtBr: "Notebook", category: "electronics" },
    // { id: 64, name: "mouse", nameEn: "mouse", namePtBr: "Mouse", category: "electronics" },
    // { id: 65, name: "remote", nameEn: "remote", namePtBr: "Controle Remoto", category: "electronics" },
    // { id: 66, name: "keyboard", nameEn: "keyboard", namePtBr: "Teclado", category: "electronics" },
    // { id: 67, name: "cell phone", nameEn: "cell phone", namePtBr: "Celular", category: "electronics" },

    // APPLIANCES (comentados)
    // { id: 68, name: "microwave", nameEn: "microwave", namePtBr: "Micro-ondas", category: "appliance" },
    // { id: 69, name: "oven", nameEn: "oven", namePtBr: "Forno", category: "appliance" },
    // { id: 70, name: "toaster", nameEn: "toaster", namePtBr: "Torradeira", category: "appliance" },
    // { id: 71, name: "sink", nameEn: "sink", namePtBr: "Pia", category: "appliance" },
    // { id: 72, name: "refrigerator", nameEn: "refrigerator", namePtBr: "Geladeira", category: "appliance" },

    // INDOOR (comentados)
    // { id: 73, name: "book", nameEn: "book", namePtBr: "Livro", category: "indoor" },
    // { id: 74, name: "clock", nameEn: "clock", namePtBr: "Relógio", category: "indoor" },
    // { id: 75, name: "vase", nameEn: "vase", namePtBr: "Vaso", category: "indoor" },
    // { id: 76, name: "scissors", nameEn: "scissors", namePtBr: "Tesoura", category: "indoor" },
    // { id: 77, name: "teddy bear", nameEn: "teddy bear", namePtBr: "Ursinho de Pelúcia", category: "indoor" },
    // { id: 78, name: "hair drier", nameEn: "hair drier", namePtBr: "Secador de Cabelo", category: "indoor" },
    // { id: 79, name: "toothbrush", nameEn: "toothbrush", namePtBr: "Escova de Dentes", category: "indoor" },
];

// ============================================================================
// CATEGORY CONFIG (PT-BR)
// ============================================================================

const CATEGORY_CONFIG = {
    person: {
        label: "Pessoas",
        icon: Users,
        color: "text-blue-600"
    },
    vehicle: {
        label: "Veículos",
        icon: Car,
        color: "text-green-600"
    },
    animal: {
        label: "Animais",
        icon: PawPrint,
        color: "text-amber-600"
    },
    furniture: {
        label: "Móveis",
        icon: Armchair,
        color: "text-purple-600"
    },
    electronics: {
        label: "Eletrônicos",
        icon: Monitor,
        color: "text-cyan-600"
    },
    traffic: {
        label: "Trânsito",
        icon: Car,
        color: "text-red-600"
    },
    accessory: {
        label: "Acessórios",
        icon: Users,
        color: "text-pink-600"
    },
    sports: {
        label: "Esportes",
        icon: Users,
        color: "text-orange-600"
    },
    kitchen: {
        label: "Cozinha",
        icon: Users,
        color: "text-yellow-600"
    },
    food: {
        label: "Alimentos",
        icon: Users,
        color: "text-lime-600"
    },
    appliance: {
        label: "Eletrodomésticos",
        icon: Monitor,
        color: "text-indigo-600"
    },
    indoor: {
        label: "Interiores",
        icon: Armchair,
        color: "text-gray-600"
    }
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function ClassSelector({
    selectedClasses,
    onChange,
    disabled = false,
    showSearch = true,
    maxHeight = "300px"
}: ClassSelectorProps) {
    const [searchTerm, setSearchTerm] = useState("");
    const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
        new Set(["person"]) // Person expandido por padrão
    );

    // Filtra e agrupa classes (busca em PT-BR e EN)
    const groupedClasses = useMemo(() => {
        const searchLower = searchTerm.toLowerCase();
        const filtered = COCO_CLASSES.filter(cls =>
            cls.namePtBr.toLowerCase().includes(searchLower) ||
            cls.nameEn.toLowerCase().includes(searchLower)
        );

        const grouped: Record<string, CocoClass[]> = {};
        filtered.forEach(cls => {
            if (!grouped[cls.category]) {
                grouped[cls.category] = [];
            }
            grouped[cls.category].push(cls);
        });

        return grouped;
    }, [searchTerm]);

    // Handlers
    const toggleClass = (classId: number) => {
        if (disabled) return;

        const newClasses = selectedClasses.includes(classId)
            ? selectedClasses.filter(id => id !== classId)
            : [...selectedClasses, classId];

        onChange(newClasses);
    };

    const toggleCategory = (category: string) => {
        const newExpanded = new Set(expandedCategories);
        if (newExpanded.has(category)) {
            newExpanded.delete(category);
        } else {
            newExpanded.add(category);
        }
        setExpandedCategories(newExpanded);
    };

    const selectAllInCategory = (category: string) => {
        if (disabled) return;

        const categoryClasses = groupedClasses[category]?.map(cls => cls.id) || [];
        const newClasses = [...new Set([...selectedClasses, ...categoryClasses])];
        onChange(newClasses);
    };

    const deselectAllInCategory = (category: string) => {
        if (disabled) return;

        const categoryClassIds = groupedClasses[category]?.map(cls => cls.id) || [];
        const newClasses = selectedClasses.filter(id => !categoryClassIds.includes(id));
        onChange(newClasses);
    };

    return (
        <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <label className="block text-sm font-medium text-gray-700">
                    🎯 Classes de Detecção
                </label>
                <span className="text-xs text-gray-500">
                    {selectedClasses.length} selecionada{selectedClasses.length !== 1 ? 's' : ''}
                </span>
            </div>

            {/* Search */}
            {showSearch && (
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        placeholder="Buscar classe..."
                        className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        disabled={disabled}
                    />
                </div>
            )}

            {/* Classes List */}
            <div
                className="border border-gray-300 rounded-lg overflow-hidden"
                style={{ maxHeight }}
            >
                <div className="overflow-y-auto h-full">
                    {Object.entries(groupedClasses).map(([category, classes]) => {
                        const config = CATEGORY_CONFIG[category as keyof typeof CATEGORY_CONFIG];
                        const Icon = config?.icon || Users;
                        const isExpanded = expandedCategories.has(category);
                        const allSelected = classes.every(cls => selectedClasses.includes(cls.id));

                        return (
                            <div key={category} className="border-b border-gray-200 last:border-b-0">
                                {/* Category Header */}
                                <div className="bg-gray-50 px-3 py-2 flex items-center justify-between hover:bg-gray-100 transition-colors">
                                    <button
                                        onClick={() => toggleCategory(category)}
                                        className="flex items-center gap-2 flex-1 text-left"
                                        disabled={disabled}
                                    >
                                        {isExpanded ? (
                                            <ChevronDown className="w-4 h-4 text-gray-600" />
                                        ) : (
                                            <ChevronRight className="w-4 h-4 text-gray-600" />
                                        )}
                                        <Icon className={`w-4 h-4 ${config?.color || 'text-gray-600'}`} />
                                        <span className="text-sm font-medium text-gray-700">
                                            {config?.label || category}
                                        </span>
                                        <span className="text-xs text-gray-500">
                                            ({classes.length})
                                        </span>
                                    </button>

                                    {/* Quick Actions */}
                                    <div className="flex items-center gap-1">
                                        <button
                                            onClick={() => allSelected
                                                ? deselectAllInCategory(category)
                                                : selectAllInCategory(category)
                                            }
                                            className="text-xs text-blue-600 hover:text-blue-700 px-2 py-1 rounded hover:bg-blue-50 transition-colors"
                                            disabled={disabled}
                                        >
                                            {allSelected ? 'Deselecionar' : 'Selecionar'} todos
                                        </button>
                                    </div>
                                </div>

                                {/* Category Classes */}
                                {isExpanded && (
                                    <div className="bg-white">
                                        {classes.map(cls => (
                                            <label
                                                key={cls.id}
                                                className={`
                                                    flex items-center gap-2 px-4 py-2 hover:bg-gray-50 cursor-pointer transition-colors
                                                    ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                                                `}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selectedClasses.includes(cls.id)}
                                                    onChange={() => toggleClass(cls.id)}
                                                    disabled={disabled}
                                                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                                />
                                                <span className="text-sm text-gray-700 flex-1">
                                                    {cls.namePtBr}                                        
                                                </span>
                                                <span className="text-xs text-gray-400">
                                                    ID: {cls.id}
                                                </span>
                                            </label>
                                        ))}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Info */}
            <p className="text-xs text-gray-500">
                💡 Apenas objetos das classes selecionadas serão detectados nesta zona
            </p>
        </div>
    );
}