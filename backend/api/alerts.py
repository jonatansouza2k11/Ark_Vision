"""
============================================================================
ALERTS API - FastAPI Router
============================================================================
Endpoints CRUD para gerenciamento de alertas do sistema.

Endpoints:
- POST   /alerts/          - Criar novo alerta
- GET    /alerts/          - Listar alertas (com filtros e paginação)
- GET    /alerts/{id}      - Buscar alerta por ID
- PUT    /alerts/{id}      - Atualizar alerta
- DELETE /alerts/{id}      - Deletar alerta
- GET    /alerts/stats/summary - Estatísticas de alertas

Autenticação: JWT Bearer Token (todos os endpoints)
Rate Limit: 100 requests/minute

✅ v2.2: Corrigido para usar resolved_at ao invés de resolved
============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from psycopg_pool import AsyncConnectionPool
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import json

# Imports locais
from database import get_db_pool
from models.alerts import AlertCreate, AlertUpdate, AlertResponse
from dependencies import get_current_user, limiter
from fastapi import Request

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)

# ============================================================================
# HELPERS
# ============================================================================

def _row_to_alert_response(row: Dict[str, Any]) -> AlertResponse:
    """
    Converte row do banco para AlertResponse.
    Trata campos JSONB e timestamps.
    
    ✅ v2.2: Calcula 'resolved' baseado em resolved_at
    """
    return AlertResponse(
        id=row['id'],
        person_id=row['person_id'],
        track_id=row.get('track_id'),
        out_time=row['out_time'],
        zone_id=row.get('zone_id'),
        zone_index=row.get('zone_index'),
        zone_name=row.get('zone_name'),
        alert_type=row['alert_type'],
        severity=row['severity'],
        description=row.get('description'),
        snapshot_path=row.get('snapshot_path'),
        video_path=row.get('video_path'),
        email_sent=row.get('email_sent', False),
        resolved=row.get('resolved_at') is not None,  # ✅ CORRIGIDO
        resolved_at=row.get('resolved_at'),
        resolved_by=row.get('resolved_by'),
        metadata=row.get('metadata') if isinstance(row.get('metadata'), dict) 
                 else json.loads(row.get('metadata', '{}')),
        created_at=row['created_at'],
        updated_at=row.get('updated_at')
    )

# ============================================================================
# CREATE ALERT
# ============================================================================

@router.post(
    "/",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo alerta",
    description="""
    Cria um novo alerta no sistema.
    
    **Campos obrigatórios:**
    - person_id: ID da pessoa detectada
    - out_time: Tempo fora da zona (segundos)
    
    **Campos opcionais:**
    - track_id, zone_id, zone_name, alert_type, severity, description,
      snapshot_path, video_path, email_sent, metadata
    
    **Returns:** Alerta criado com ID gerado
    """
)
@limiter.limit("100/minute")
async def create_alert(
    request: Request,
    alert: AlertCreate,
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """Cria novo alerta"""
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Converte Enum para string se necessário
                alert_type_str = alert.alert_type.value if hasattr(alert.alert_type, 'value') else str(alert.alert_type)
                severity_str = alert.severity.value if hasattr(alert.severity, 'value') else str(alert.severity)
                
                await cur.execute(
                    """
                    INSERT INTO alerts (
                        person_id, track_id, out_time, zone_id, zone_index, zone_name,
                        alert_type, severity, description, snapshot_path, video_path,
                        email_sent, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        alert.person_id,
                        alert.track_id,
                        alert.out_time,
                        alert.zone_id,
                        alert.zone_index,
                        alert.zone_name,
                        alert_type_str,
                        severity_str,
                        alert.description,
                        alert.snapshot_path,
                        alert.video_path,
                        alert.email_sent,
                        json.dumps(alert.metadata or {})
                    )
                )
                row = await cur.fetchone()
                await conn.commit()
                
                logger.info(
                    f"✅ Alert created: ID={row['id']}, "
                    f"person_id={alert.person_id}, "
                    f"severity={severity_str}, "
                    f"by={current_user.get('username')}"
                )
                
                return _row_to_alert_response(row)
                
    except Exception as e:
        logger.error(f"❌ Error creating alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar alerta: {str(e)}"
        )

# ============================================================================
# LIST ALERTS (com filtros e paginação)
# ============================================================================

@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="Listar alertas",
    description="""
    Lista alertas com suporte a filtros e paginação.
    
    **Filtros disponíveis:**
    - severity: Filtra por severidade (LOW, MEDIUM, HIGH, CRITICAL)
    - alert_type: Filtra por tipo (zone_violation, zone_empty, etc.)
    - zone_id: Filtra por zona específica
    - resolved: Filtra por status de resolução
    - start_date: Data inicial (YYYY-MM-DD)
    - end_date: Data final (YYYY-MM-DD)
    
    **Paginação:**
    - skip: Número de registros para pular (default: 0)
    - limit: Número máximo de resultados (default: 50, max: 200)
    
    **Returns:** Lista de alertas + metadados (total, filtros aplicados)
    """
)
@limiter.limit("100/minute")
async def list_alerts(
    request: Request,
    skip: int = Query(default=0, ge=0, description="Número de registros para pular"),
    limit: int = Query(default=50, ge=1, le=200, description="Limite de resultados"),
    severity: Optional[str] = Query(None, description="Filtrar por severidade"),
    alert_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    zone_id: Optional[int] = Query(None, ge=1, description="Filtrar por zona"),
    resolved: Optional[bool] = Query(None, description="Filtrar por status de resolução"),
    start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """Lista alertas com filtros"""
    try:
        # Monta query dinamicamente
        where_clauses = []
        params = []
        
        if severity:
            where_clauses.append("severity = %s")
            params.append(severity.upper())
        
        if alert_type:
            where_clauses.append("alert_type = %s")
            params.append(alert_type.lower())
        
        if zone_id:
            where_clauses.append("zone_id = %s")
            params.append(zone_id)
        
        # ✅ CORRIGIDO: Usa resolved_at ao invés de resolved
        if resolved is not None:
            if resolved:
                where_clauses.append("resolved_at IS NOT NULL")
            else:
                where_clauses.append("resolved_at IS NULL")
        
        if start_date:
            where_clauses.append("created_at >= %s")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("created_at < %s + INTERVAL '1 day'")
            params.append(end_date)
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Query de contagem total
                count_query = f"SELECT COUNT(*) as total FROM alerts {where_sql}"
                await cur.execute(count_query, params)
                total = (await cur.fetchone())['total']
                
                # Query principal com paginação
                query = f"""
                    SELECT * FROM alerts
                    {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                await cur.execute(query, params + [limit, skip])
                rows = await cur.fetchall()
                
                alerts = [_row_to_alert_response(row) for row in rows]
                
                return {
                    "alerts": alerts,
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                    "filters": {
                        "severity": severity,
                        "alert_type": alert_type,
                        "zone_id": zone_id,
                        "resolved": resolved,
                        "start_date": start_date,
                        "end_date": end_date
                    }
                }
                
    except Exception as e:
        logger.error(f"❌ Error listing alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar alertas: {str(e)}"
        )

# ============================================================================
# GET ALERT BY ID
# ============================================================================

@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Buscar alerta por ID",
    description="Retorna detalhes completos de um alerta específico."
)
@limiter.limit("100/minute")
async def get_alert(
    request: Request,
    alert_id: int,
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """Busca alerta por ID"""
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM alerts WHERE id = %s",
                    (alert_id,)
                )
                row = await cur.fetchone()
                
                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Alerta {alert_id} não encontrado"
                    )
                
                return _row_to_alert_response(row)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar alerta: {str(e)}"
        )

# ============================================================================
# UPDATE ALERT
# ============================================================================

@router.put(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Atualizar alerta",
    description="""
    Atualiza campos de um alerta existente.
    
    **Campos atualizáveis:**
    - severity, description, email_sent, resolved, resolved_by, metadata
    
    **Auto-preenchido:**
    - resolved_at: Preenchido automaticamente quando resolved=True
    """
)
@limiter.limit("100/minute")
async def update_alert(
    request: Request,
    alert_id: int,
    alert: AlertUpdate,
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """Atualiza alerta existente"""
    try:
        async with pool.connection() as conn:
            # Verifica se alerta existe
            async with conn.cursor() as cur:
                await cur.execute("SELECT id FROM alerts WHERE id = %s", (alert_id,))
                if not await cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Alerta {alert_id} não encontrado"
                    )
            
            # Monta UPDATE dinamicamente
            update_fields = []
            params = []
            
            update_dict = alert.model_dump(exclude_none=True)
            
            # ✅ CORRIGIDO: Trata campo 'resolved'
            if 'resolved' in update_dict:
                resolved_value = update_dict.pop('resolved')
                if resolved_value:
                    # Se resolved=True, preenche resolved_at
                    if 'resolved_at' not in update_dict:
                        update_dict['resolved_at'] = datetime.now()
                    if 'resolved_by' not in update_dict:
                        update_dict['resolved_by'] = current_user.get('username')
                else:
                    # Se resolved=False, limpa resolved_at e resolved_by
                    update_dict['resolved_at'] = None
                    update_dict['resolved_by'] = None
            
            for key, value in update_dict.items():
                # Converte Enum para string
                if hasattr(value, 'value'):
                    value = value.value
                
                # Serializa metadata para JSON
                if key == 'metadata' and isinstance(value, dict):
                    value = json.dumps(value)
                
                update_fields.append(f"{key} = %s")
                params.append(value)
            
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nenhum campo para atualizar"
                )
            
            # Adiciona updated_at
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            
            params.append(alert_id)
            
            query = f"""
                UPDATE alerts
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING *
            """
            
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                row = await cur.fetchone()
                await conn.commit()
                
                logger.info(
                    f"✅ Alert updated: ID={alert_id}, "
                    f"by={current_user.get('username')}"
                )
                
                return _row_to_alert_response(row)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar alerta: {str(e)}"
        )

# ============================================================================
# DELETE ALERT
# ============================================================================

@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar alerta",
    description="Remove permanentemente um alerta do sistema."
)
@limiter.limit("100/minute")
async def delete_alert(
    request: Request,
    alert_id: int,
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """Deleta alerta"""
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM alerts WHERE id = %s RETURNING id",
                    (alert_id,)
                )
                deleted = await cur.fetchone()
                
                if not deleted:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Alerta {alert_id} não encontrado"
                    )
                
                await conn.commit()
                
                logger.info(
                    f"✅ Alert deleted: ID={alert_id}, "
                    f"by={current_user.get('username')}"
                )
                
                return None  # 204 No Content
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar alerta: {str(e)}"
        )

# ============================================================================
# ALERT STATISTICS
# ✅ v2.2: Corrigido para usar resolved_at
# ============================================================================

@router.get(
    "/stats/summary",
    response_model=Dict[str, Any],
    summary="Estatísticas de alertas",
    description="""
    Retorna estatísticas agregadas dos alertas.
    
    **Inclui:**
    - Total de alertas
    - Alertas por severidade
    - Alertas por tipo
    - Alertas resolvidos vs não resolvidos
    - Alertas das últimas 24h
    - Média de tempo de resolução
    """
)
@limiter.limit("100/minute")
async def get_alert_stats(
    request: Request,
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """Retorna estatísticas de alertas"""
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Total de alertas
                await cur.execute("SELECT COUNT(*) as total FROM alerts")
                total = (await cur.fetchone())['total']
                
                # Por severidade
                await cur.execute("""
                    SELECT severity, COUNT(*) as count
                    FROM alerts
                    GROUP BY severity
                    ORDER BY 
                        CASE severity
                            WHEN 'CRITICAL' THEN 1
                            WHEN 'HIGH' THEN 2
                            WHEN 'MEDIUM' THEN 3
                            WHEN 'LOW' THEN 4
                        END
                """)
                by_severity = {row['severity']: row['count'] for row in await cur.fetchall()}
                
                # Por tipo
                await cur.execute("""
                    SELECT alert_type, COUNT(*) as count
                    FROM alerts
                    GROUP BY alert_type
                    ORDER BY count DESC
                """)
                by_type = {row['alert_type']: row['count'] for row in await cur.fetchall()}
                
                # ✅ CORRIGIDO: Resolvidos vs não resolvidos usando resolved_at
                await cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE resolved_at IS NOT NULL) as resolved,
                        COUNT(*) FILTER (WHERE resolved_at IS NULL) as unresolved
                    FROM alerts
                """)
                resolution_stats = await cur.fetchone()
                
                # Últimas 24h
                await cur.execute("""
                    SELECT COUNT(*) as count
                    FROM alerts
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                """)
                last_24h = (await cur.fetchone())['count']
                
                # Tempo médio de resolução (em horas)
                await cur.execute("""
                    SELECT 
                        AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/3600) as avg_hours
                    FROM alerts
                    WHERE resolved_at IS NOT NULL
                """)
                avg_resolution_time = (await cur.fetchone())['avg_hours']
                
                return {
                    "total_alerts": total,
                    "by_severity": by_severity,
                    "by_type": by_type,
                    "resolved": resolution_stats['resolved'],
                    "unresolved": resolution_stats['unresolved'],
                    "last_24h": last_24h,
                    "avg_resolution_hours": round(avg_resolution_time, 2) if avg_resolution_time else None,
                    "generated_at": datetime.now().isoformat()
                }
                
    except Exception as e:
        logger.error(f"❌ Error generating alert stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar estatísticas: {str(e)}"
        )

# ============================================================================
# TESTE
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("📋 Alerts API Router v2.2")
    print("=" * 70)
    print("✅ Endpoints:")
    print("   POST   /alerts/          - Criar alerta")
    print("   GET    /alerts/          - Listar alertas (filtros + paginação)")
    print("   GET    /alerts/{id}      - Buscar alerta por ID")
    print("   PUT    /alerts/{id}      - Atualizar alerta")
    print("   DELETE /alerts/{id}      - Deletar alerta")
    print("   GET    /alerts/stats/summary - Estatísticas")
    print("=" * 70)
    print("🔐 Autenticação: JWT Bearer Token (obrigatório)")
    print("⏱️  Rate Limit: 100 requests/minute")
    print("✅ v2.2: Corrigido para usar resolved_at")
    print("=" * 70)
