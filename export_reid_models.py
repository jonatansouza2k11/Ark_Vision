"""
export_reid_models.py
Baixa modelos OSNet via Torchreid e exporta para arquivos .pt (TorchScript)

Perfis gerados:
  - EDGE    -> models/reid/osnet_x0_25_edge.pt
  - DEFAULT -> models/reid/osnet_x0_5_default.pt
  - HIGH    -> models/reid/osnet_x0_75_high.pt
"""

import os
from pathlib import Path

import torch
import torchreid


# ========================================================================
# CONFIGURAÇÃO
# ========================================================================

OUT_DIR = Path("reid_models")

# Perfis de ReID que vamos gerar
PROFILES = {
    "edge": {
        "model_name": "osnet_x0_25",          # leve, ideal para edge
        "feat_dim": 512,
        "filename": "osnet_x0_25_edge.pt",
    },
    "default": {
        "model_name": "osnet_x0_5",           # equilíbrio
        "feat_dim": 512,
        "filename": "osnet_x0_5_default.pt",
    },
    "high": {
        "model_name": "osnet_x0_75",          # mais pesado, melhor qualidade
        "feat_dim": 512,
        "filename": "osnet_x0_75_high.pt",
    },
}

# Tamanho típico de input em person ReID (H, W)
IMG_HEIGHT = 256
IMG_WIDTH = 128

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"


# ========================================================================
# FUNÇÕES AUXILIARES
# ========================================================================

def build_backbone(name: str):
    """
    Cria modelo OSNet pré-treinado só como extrator de features (sem classifier).
    A dimensão do embedding é a padrão do modelo (ex: 512 para OSNet).
    """
    model = torchreid.models.build_model(
        name=name,
        num_classes=0,    # 0 -> só backbone, sem cabeça de classificação
        pretrained=True,
    )
    model.eval()
    model.to(DEVICE)
    return model


def export_profile(profile_name: str, cfg: dict) -> None:
    model_name = cfg["model_name"]
    feat_dim = cfg["feat_dim"]
    filename = cfg["filename"]
    out_path = OUT_DIR / filename

    print("-" * 70)
    print(f"🎯 Exportando perfil: {profile_name.upper()}")
    print(f"   Modelo base: {model_name}")
    print(f"   Dim. embedding (doc): {feat_dim}")
    print(f"   Saída: {out_path}")
    print("-" * 70)

    # Cria pasta de saída
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Constrói modelo (dimensão de embedding é a padrão do OSNet)
    model = build_backbone(model_name)

    # Dummy input para traçar o grafo
    dummy = torch.randn(1, 3, IMG_HEIGHT, IMG_WIDTH, device=DEVICE)

    # Exporta como TorchScript (trace)
    scripted = torch.jit.trace(model, dummy)
    torch.jit.save(scripted, str(out_path))

    print(f"✅ Perfil {profile_name.upper()} salvo em: {out_path}\n")


# ========================================================================
# MAIN
# ========================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🧬 Exportando modelos de ReID (OSNet) para TorchScript .pt")
    print("=" * 70)
    print(f"📁 Pasta de saída: {OUT_DIR}")
    print(f"🖼️  Tamanho de input: {IMG_HEIGHT}x{IMG_WIDTH}")
    print(f"🔧 Device: {DEVICE}")
    if torch.cuda.is_available():
        print(f"✅ GPU detectada: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ CUDA não disponível, exportando em CPU (ok, só fica mais lento).")
    print("=" * 70)
    print()

    for profile_name, cfg in PROFILES.items():
        export_profile(profile_name, cfg)

    print("=" * 70)
    print("🏁 Exportação de todos os perfis concluída!")
    print("=" * 70)
    print("📌 Próximos passos sugeridos:")
    print("  1. Ajustar seu .env com os caminhos gerados, por exemplo:")
    print("     REID_MODEL_PATH_EDGE=models/reid/osnet_x0_25_edge.pt")
    print("     REID_MODEL_PATH_DEFAULT=models/reid/osnet_x0_5_default.pt")
    print("     REID_MODEL_PATH_HIGH=models/reid/osnet_x0_75_high.pt")
    print("  2. Definir REID_PROFILE_DEFAULT=default (ou edge/high).")
    print("  3. Subir o backend e testar uma câmera com default_tracker=yolo_strongsort.")
    print("=" * 70)
