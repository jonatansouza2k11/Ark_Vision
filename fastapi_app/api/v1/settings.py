"""
Settings endpoints
CRUD operations for system settings
"""

from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user, get_current_admin
from fastapi_app.models.user import User
from fastapi_app.models.setting import Setting
from fastapi_app.schemas.setting import SettingResponse, SettingUpdate, SettingBulkUpdate


router = APIRouter()


@router.get("/", response_model=List[SettingResponse])
def list_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar todas as configurações
    
    Retorna lista de todas as configurações do sistema
    
    Requer: Token JWT válido
    """
    settings = db.query(Setting).all()
    return settings


@router.get("/dict", response_model=Dict[str, str])
def get_settings_dict(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obter configurações como dicionário
    
    Retorna todas as configurações em formato {key: value}
    
    Útil para carregar todas as configurações de uma vez
    
    Requer: Token JWT válido
    """
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}


@router.get("/{key}", response_model=SettingResponse)
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obter configuração específica por key
    
    Requer: Token JWT válido
    """
    setting = db.query(Setting).filter(Setting.key == key).first()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuração '{key}' não encontrada"
        )
    
    return setting


@router.put("/{key}", response_model=SettingResponse)
def update_setting(
    key: str,
    value: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)  # Apenas admin
):
    """
    Atualizar configuração específica
    
    - **key**: Chave da configuração
    - **value**: Novo valor
    
    Se a configuração não existir, será criada
    
    Requer: Token JWT de admin
    """
    setting = db.query(Setting).filter(Setting.key == key).first()
    
    if setting:
        # Atualizar existente
        setting.value = value
    else:
        # Criar nova
        setting = Setting(key=key, value=value)
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    
    return setting


@router.put("/", response_model=Dict[str, str])
def bulk_update_settings(
    settings_data: SettingBulkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)  # Apenas admin
):
    """
    Atualizar múltiplas configurações de uma vez
    
    Envia um dicionário {key: value} para atualizar várias configurações
    
    Exemplo:
    ```
    {
        "settings": {
            "max_out_time": "30.0",
            "email_cooldown": "600.0",
            "conf_thresh": "0.90"
        }
    }
    ```
    
    Requer: Token JWT de admin
    """
    updated = {}
    
    for key, value in settings_data.settings.items():
        setting = db.query(Setting).filter(Setting.key == key).first()
        
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            db.add(setting)
        
        updated[key] = value
    
    db.commit()
    
    return updated


@router.post("/", response_model=SettingResponse, status_code=status.HTTP_201_CREATED)
def create_setting(
    setting_data: SettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)  # Apenas admin
):
    """
    Criar nova configuração
    
    - **key**: Chave da configuração (única)
    - **value**: Valor da configuração
    
    Requer: Token JWT de admin
    """
    # Verificar se já existe
    existing = db.query(Setting).filter(Setting.key == setting_data.key).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuração '{setting_data.key}' já existe. Use PUT para atualizar."
        )
    
    new_setting = Setting(
        key=setting_data.key,
        value=setting_data.value
    )
    
    db.add(new_setting)
    db.commit()
    db.refresh(new_setting)
    
    return new_setting


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)  # Apenas admin
):
    """
    Deletar configuração
    
    ⚠️ CUIDADO: Deletar configurações pode afetar o funcionamento do sistema
    
    Requer: Token JWT de admin
    """
    setting = db.query(Setting).filter(Setting.key == key).first()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuração '{key}' não encontrada"
        )
    
    db.delete(setting)
    db.commit()
    
    return None
