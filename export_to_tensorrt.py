"""
export_to_tensorrt.py
Converte modelo YOLO .pt para TensorRT .engine
"""
from ultralytics import YOLO
import torch

# Configuração
MODEL_PT = "yolo_models/yolo26x.pt"             # Modelo PyTorch original
MODEL_ENGINE = "yolo_models/yolo26x.engine"     # Saída TensorRT

IMGSZ = 640  # Tamanho de entrada (deve bater com inferência)
DEVICE = 0  # GPU ID (0 para primeira GPU)

print("=" * 70)
print("🚀 Exportando YOLO para TensorRT Engine")
print("=" * 70)
print(f"📦 Modelo origem: {MODEL_PT}")
print(f"🎯 Destino: {MODEL_ENGINE}")
print(f"🖼️  Tamanho imagem: {IMGSZ}x{IMGSZ}")
print(f"🔧 Device: cuda:{DEVICE}")
print("=" * 70)

# Verificar CUDA
if not torch.cuda.is_available():
    print("❌ CUDA não disponível! TensorRT requer GPU NVIDIA.")
    exit(1)

print(f"✅ GPU detectada: {torch.cuda.get_device_name(DEVICE)}")
print("⏳ Iniciando exportação (pode levar 2-5 minutos)...\n")

# Carregar modelo
model = YOLO(MODEL_PT)

# Exportar para TensorRT
# half=True usa FP16 (mais rápido, recomendado para inferência)
# dynamic=False fixa o tamanho de entrada (mais otimizado)
model.export(
    format="engine",
    imgsz=IMGSZ,
    half=True,      # FP16 precision (2x mais rápido)
    device=DEVICE,
    dynamic=False,  # Fixed input size (melhor performance)
    simplify=True,
    workspace=4,    # GB de workspace (ajuste conforme sua GPU)
)

print("\n" + "=" * 70)
print("✅ Exportação concluída!")
print("=" * 70)
print(f"📁 Arquivo gerado: {MODEL_ENGINE}")
print("\n🎯 Próximos passos:")
print("   1. Atualizar YOLO_MODEL_PATH no .env")
print("   2. Reiniciar o servidor")
print("   3. Testar FPS no dashboard")
print("=" * 70)
