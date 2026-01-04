"""
Alerts endpoints
CRUD operations for alerts
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.models.user import User
from fastapi_app.models.alert import Alert
from fastapi_app.schemas.alert import AlertCreate, AlertResponse, AlertList


router = APIRouter()


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Criar novo alerta
    
    - **person_id**: ID da pessoa detectada
    - **out_time**: Tempo fora da zona (segundos)
    - **snapshot_path**: Caminho do snapshot (opcional)
    - **email_sent**: Email foi enviado? (padrão: false)
    
    Requer: Token JWT válido
    """
    new_alert = Alert(
        person_id=alert_data.person_id,
        out_time=alert_data.out_time,
        snapshot_path=alert_data.snapshot_path,
        email_sent=alert_data.email_sent
    )
    
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    
    return new_alert


@router.get("/", response_model=AlertList)
def list_alerts(
    page: int = Query(1, ge=1, description="Página (inicia em 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    person_id: Optional[int] = Query(None, description="Filtrar por person_id"),
    email_sent: Optional[bool] = Query(None, description="Filtrar por email_sent"),
    start_date: Optional[datetime] = Query(None, description="Data inicial (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Data final (ISO 8601)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar alertas com paginação e filtros
    
    **Filtros disponíveis:**
    - **page**: Número da página (padrão: 1)
    - **per_page**: Itens por página (padrão: 20, máx: 100)
    - **person_id**: Filtrar por ID da pessoa
    - **email_sent**: Filtrar por status de email (true/false)
    - **start_date**: Data inicial (ex: 2025-12-30T00:00:00)
    - **end_date**: Data final (ex: 2025-12-30T23:59:59)
    
    Requer: Token JWT válido
    """
    # Query base
    query = db.query(Alert)
    
    # Aplicar filtros
    if person_id is not None:
        query = query.filter(Alert.person_id == person_id)
    
    if email_sent is not None:
        query = query.filter(Alert.email_sent == email_sent)
    
    if start_date is not None:
        query = query.filter(Alert.timestamp >= start_date)
    
    if end_date is not None:
        query = query.filter(Alert.timestamp <= end_date)
    
    # Total de registros (antes da paginação)
    total = query.count()
    
    # Ordenar por mais recente
    query = query.order_by(desc(Alert.timestamp))
    
    # Paginação
    offset = (page - 1) * per_page
    alerts = query.offset(offset).limit(per_page).all()
    
    return AlertList(
        total=total,
        page=page,
        per_page=per_page,
        alerts=alerts
    )


@router.get("/stats")
def get_alert_stats(
    days: int = Query(7, ge=1, le=365, description="Últimos N dias"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Estatísticas de alertas
    
    - **days**: Últimos N dias para análise (padrão: 7)
    
    Retorna estatísticas agregadas dos alertas
    
    Requer: Token JWT válido
    """
    # Data de corte
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Total de alertas
    total_alerts = db.query(func.count(Alert.id)).filter(
        Alert.timestamp >= cutoff_date
    ).scalar()
    
    # Alertas com email enviado
    emails_sent = db.query(func.count(Alert.id)).filter(
        Alert.timestamp >= cutoff_date,
        Alert.email_sent == True
    ).scalar()
    
    # Média de out_time
    avg_out_time = db.query(func.avg(Alert.out_time)).filter(
        Alert.timestamp >= cutoff_date
    ).scalar()
    
    # Pessoas únicas detectadas
    unique_persons = db.query(func.count(func.distinct(Alert.person_id))).filter(
        Alert.timestamp >= cutoff_date
    ).scalar()
    
    # Top 5 pessoas com mais alertas
    top_persons = db.query(
        Alert.person_id,
        func.count(Alert.id).label('count')
    ).filter(
        Alert.timestamp >= cutoff_date
    ).group_by(Alert.person_id).order_by(desc('count')).limit(5).all()
    
    return {
        "period_days": days,
        "start_date": cutoff_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "total_alerts": total_alerts or 0,
        "emails_sent": emails_sent or 0,
        "avg_out_time": round(float(avg_out_time or 0), 2),
        "unique_persons": unique_persons or 0,
        "top_persons": [
            {"person_id": p.person_id, "alert_count": p.count}
            for p in top_persons
        ]
    }


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obter alerta por ID
    
    Requer: Token JWT válido
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerta {alert_id} não encontrado"
        )
    
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletar alerta por ID
    
    Requer: Token JWT válido
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerta {alert_id} não encontrado"
        )
    
    db.delete(alert)
    db.commit()
    
    return None


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_old_alerts(
    days: int = Query(..., ge=1, description="Deletar alertas com mais de N dias"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletar alertas antigos (limpeza)
    
    - **days**: Deletar alertas com mais de N dias
    
    Exemplo: days=30 deleta alertas com mais de 30 dias
    
    Requer: Token JWT válido
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    deleted = db.query(Alert).filter(Alert.timestamp < cutoff_date).delete()
    db.commit()
    
    return {"deleted": deleted, "cutoff_date": cutoff_date.isoformat()}
